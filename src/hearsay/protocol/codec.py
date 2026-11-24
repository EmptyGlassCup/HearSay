from hearsay.irc.parser import IRCMessage
from hearsay.protocol.events import (
    Event, ClaimEvent, JustifyEvent, RetractClaimEvent, RetractJustifyEvent, ChallengeEvent
)
from hearsay.board.board import Board

def decode(msg: IRCMessage) -> Event | None:

    try:
        event_type = msg.tags['+bb-kind']
        author = msg.prefix.split('!')[0] if msg.prefix else 'unknown'
        match event_type:
            case 'claim':
                event = ClaimEvent(
                    author=author,
                    claim_id=msg.tags['+bb-id'],
                    text=msg.params[-1],
                    kind=msg.tags['+bb-claim-kind'],
                    level=int(msg.tags['+bb-level']),
                    credibility=float(msg.tags['+bb-conf']),
                )
                return event

            case 'justify':
                event = JustifyEvent(
                    author=author,
                    justification_id=msg.tags['+bb-id'],
                    conclusion=msg.tags['+bb-conclusion'],
                    premises=tuple(msg.tags['+bb-premises'].split(',')) if msg.tags['+bb-premises'] else tuple()
                )
                return event

            case 'retract-claim':
                event = RetractClaimEvent(
                    author=author,
                    retract_claim_id=msg.tags['+bb-ref']
                )
                return event

            case 'retract-justify':
                event = RetractJustifyEvent(
                    author=author,
                    retract_justification_id=msg.tags['+bb-ref']
                )
                return event

            case 'challenge':
                event = ChallengeEvent(
                    author=author,
                    challenge_id=msg.tags['+bb-ref']
                )
                return event

            case _:
                return None

    except (KeyError, ValueError, IndexError):
        # KeyError - required tag missing
        # Value error - incorrect level or credibility for type conversion
        # Index error - no parameters (message text)
        return None

def encode(event: Event, board: Board) -> IRCMessage:
    match event:
        case ClaimEvent():
            msg = IRCMessage(
                tags={
                    '+bb-kind': 'claim',
                    '+bb-id': event.claim_id,
                    '+bb-level': str(event.level),
                    '+bb-conf': str(event.credibility),
                    '+bb-claim-kind': event.kind,
                },
                command='PRIVMSG',
                params=[_channel(event, board), event.text]
                )
            return msg

        case JustifyEvent():
            msg = IRCMessage(
                tags={
                    '+bb-kind': 'justify',
                    '+bb-id': event.justification_id,
                    '+bb-conclusion': event.conclusion,
                    '+bb-premises': ','.join(event.premises)
                },
                command='PRIVMSG',
                params=[_channel(event, board), f"claim {event.conclusion} follows from {', '.join(event.premises)}"]
                )
            return msg

        case RetractClaimEvent():
            msg = IRCMessage(
                tags={
                    '+bb-kind': 'retract-claim',
                    '+bb-ref': event.retract_claim_id,
                },
                command='PRIVMSG',
                params=[_channel(event, board), f"claim {event.retract_claim_id} has been retracted"]
                )
            return msg

        case RetractJustifyEvent():
            msg = IRCMessage(
                tags={
                    '+bb-kind': 'retract-justify',
                    '+bb-ref': event.retract_justification_id,
                },
                command='PRIVMSG',
                params=[_channel(event, board), f"justification {event.retract_justification_id} has been retracted"]
                )
            return msg

        case ChallengeEvent():
            msg = IRCMessage(
                tags={
                    '+bb-kind': 'challenge',
                    '+bb-ref': event.challenge_id
                },
                command='PRIVMSG',
                params=[_channel(event, board), f"claim {event.challenge_id} has been challenged"]
                )
            return msg
        
            



def _channel(event: Event, board: Board) -> str:
    match event:
        case ClaimEvent():
            level = event.level
        case JustifyEvent():
            conclusion = board.claim_events[event.conclusion]
            level = conclusion.level
        case RetractClaimEvent():
            retracted_claim = board.claim_events[event.retract_claim_id]
            level = retracted_claim.level
        case RetractJustifyEvent():
            retracted_justification = board.justify_events[event.retract_justification_id]
            conclusion = board.claim_events[retracted_justification.conclusion]
            level = conclusion.level
        case ChallengeEvent():
            challanged_claim = board.claim_events[event.challenge_id]
            level = challanged_claim.level
        case _:
            level = 1
    

    if level == 0:
        return '#evidence'
    elif level < 3:
        return '#hypotheses'
    elif level >= 3:
        return '#conclusions'
    
    # Safeguard, should never run
    return '#hypotheses'


