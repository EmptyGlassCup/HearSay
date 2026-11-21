from dataclasses import dataclass

@dataclass(kw_only=True)
class Event:
    author: str
    sequence: int | None = None

@dataclass(kw_only=True)
class ClaimEvent(Event):
    claim_id: str
    text: str
    kind: str
    level: int
    credibility: float

@dataclass(kw_only=True)
class JustifyEvent(Event):
    justification_id: str
    conclusion: str
    premises: tuple[str, ...]

@dataclass(kw_only=True)
class RetractClaimEvent(Event):
    claim_id: str

@dataclass(kw_only=True)
class RetractJustifyEvent(Event):
    justification_id: str

@dataclass(kw_only=True)
class ChallengeEvent(Event):
    challenge_id: str

#TODO
@dataclass(kw_only=True)
class ActivateEvent(Event):
    pass

#TODO
@dataclass(kw_only=True)
class ResultEvent(Event):
    pass

