from hearsay.board.eventlog import EventLog
from hearsay.protocol.events import (
    Event, ClaimEvent, JustifyEvent, RetractClaimEvent, RetractJustifyEvent, ChallengeEvent
)
from hearsay.tms.jtms import JTMS, Claim, Justification


class Board:
    def __init__(self):
        self.event_log = EventLog()
        self.jtms = JTMS()
        self.claim_events = {}
        self.challenges = set()
    
    def apply(self, event: Event):
        match event:
            case ClaimEvent():
                # Add the claim to JTMS
                claim = Claim(id=event.claim_id, text=event.text, kind=event.kind)
                self.jtms.add_claim(claim)

                # Add event to claim events
                self.claim_events[event.claim_id] = event
            case JustifyEvent():
                justification = Justification(id=event.justification_id, conclusion=event.conclusion, premises=event.premises)
                self.jtms.add_justification(justification)
            case RetractClaimEvent():
                self.jtms.retract_claim(event.retract_claim_id)
            case RetractJustifyEvent():
                self.jtms.retract_justification(event.retract_justification_id)
            case ChallengeEvent():
                # TODO: DO somethingg!!
                self.challenges.add(event.challenge_id)

        # Add event to event log
        self.event_log.append(event)

                


