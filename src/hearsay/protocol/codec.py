from hearsay.irc.parser import IRCMessage
from hearsay.irc.parser import IRCMessage
from hearsay.protocol.events import (
    Event, ClaimEvent, JustifyEvent, RetractClaimEvent, RetractJustifyEvent, ChallengeEvent
)
from hearsay.board.board import Board


# Human-facing command syntax, typed by a person in an ordinary IRC client. These carry no
# bb-tags, so the kernel tries decode() first (machine events) and falls back to this.
HELP_TEXT = (
    "HearSay commands: "
    "!claim <evidence|hypothesis|conclusion|goal> <credibility 0-1> <text>  |  "
    "!retract <id>  |  "
    "!challenge <id>  |  "
    "!help"
)

_VALID_KINDS = ("evidence", "hypothesis", "conclusion", "goal")


def decode_human_command(msg: IRCMessage, allocate_id) -> Event | None:
    """Parse a human-typed `!command` into an Event. Returns None for anything that is not a
    recognised, well-formed command (ordinary chatter is ignored — never crashes).

    allocate_id: a zero-arg callable the KERNEL provides, returning a fresh unique claim id.
                 Humans don't invent ids; the kernel assigns one for !claim and echoes it back.

    Note: `!help` is handled by the kernel (it replies with HELP_TEXT), not here, since it
    produces no board event.
    """
    text = msg.params[-1].strip() if msg.params else ""
    if not text.startswith("!"):
        return None

    author = msg.prefix.split("!")[0] if msg.prefix else "human"
    parts = text.split()
    cmd = parts[0].lower()

    try:
        if cmd == "!claim":
            # !claim <kind> <credibility> <text...>
            kind = parts[1].lower()
            if kind not in _VALID_KINDS:
                return None
            credibility = float(parts[2])
            if not (0.0 <= credibility <= 1.0):
                return None
            body = " ".join(parts[3:]).strip()
            if not body:
                return None
            level = 0 if kind == "evidence" else 1   # humans assert raw evidence or a claim
            return ClaimEvent(
                author=author,
                claim_id=allocate_id(),
                text=body,
                kind=kind,
                level=level,
                credibility=credibility,
            )

        if cmd == "!retract":
            return RetractClaimEvent(author=author, retract_claim_id=parts[1])

        if cmd == "!challenge":
            return ChallengeEvent(author=author, challenge_id=parts[1])

    except (IndexError, ValueError):
        return None   # malformed command -> ignore, never crash

    return None


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

        case _:
            return None
        
            



def _channel(event: Event, board: Board) -> str:
    match event:
        case ClaimEvent():
            level = event.level
        case JustifyEvent():
            try:
                conclusion = board.claim_events[event.conclusion]
                level = conclusion.level
            except KeyError:
                level = 1
        case RetractClaimEvent():
            try:
                retracted_claim = board.claim_events[event.retract_claim_id]
                level = retracted_claim.level
            except KeyError:
                level = 1
        case RetractJustifyEvent():
            try:
                retracted_justification = board.justify_events[event.retract_justification_id]
                conclusion = board.claim_events[retracted_justification.conclusion]
                level = conclusion.level
            except KeyError:
                level = 1
        case ChallengeEvent():
            try:
                challanged_claim = board.claim_events[event.challenge_id]
                level = challanged_claim.level
            except KeyError:
                level = 1
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


