from hypothesis import given, strategies as st
from hearsay.protocol.codec import encode, decode
from hearsay.board.board import Board
from hearsay.protocol.events import (
    Event, ClaimEvent, JustifyEvent, RetractClaimEvent, RetractJustifyEvent, ChallengeEvent
)
from tests.test_jtms import jtms_strategy

@st.composite
def events_strategy(draw):
    claims, justifications, retracted_claim_ids, retracted_justification_ids = draw(jtms_strategy())
    board = Board()

    claim_events = []
    for claim in claims:
        event = ClaimEvent(
            author=draw(st.text(min_size=0, max_size=10)),
            claim_id=claim.id,
            text=claim.text,
            kind=claim.kind,
            level=draw(st.integers(min_value=0, max_value=3)),
            credibility=draw(st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False))
        )

        claim_events.append(event)

    justify_events = []
    for justification in justifications:
        event = JustifyEvent(
            author=draw(st.text(min_size=0, max_size=10)),
            justification_id=justification.id,
            conclusion=justification.conclusion,
            premises=justification.premises
        )

        justify_events.append(event)

    retract_claim_events = []
    for retracted_claim_id in retracted_claim_ids:
        event = RetractClaimEvent(
            author=draw(st.text(min_size=0, max_size=10)),
            retract_claim_id=retracted_claim_id
        )

        retract_claim_events.append(event)

    retract_justify_events = []
    for retracted_justification_id in retracted_justification_ids:
        event = RetractJustifyEvent(
            author=draw(st.text(min_size=0, max_size=10)),
            retract_justification_id=retracted_justification_id
        )

        retract_justify_events.append(event)

    # Create Challange events seperately, as jtms strategy does not generate
    claim_ids = [c.id for c in claims]
    challange_events = []
    if claim_ids:
        challange_ids = draw(st.lists(st.sampled_from(claim_ids), max_size=len(claim_ids), unique=True))
        for challange_id in challange_ids:
            event = ChallengeEvent(
                author=draw(st.text(min_size=0, max_size=10)),
                challenge_id=challange_id
            )

            challange_events.append(event)

    # Apply all events to the board
    events = claim_events + justify_events + retract_claim_events + retract_justify_events + challange_events
    
    for event in events:
        board.apply(event)

    return events, board


@given(events_strategy())
def test_codec(data):
    events, board = data

    for event in events:
        original = event
        decoded = decode(encode(original, board))

        # These are expected to change
        decoded.author = original.author
        decoded.sequence = original.sequence

        decoded.sequence = original.sequence
        assert decoded == original


