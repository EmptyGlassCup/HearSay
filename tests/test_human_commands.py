"""
Tests for decode_human_command: parsing human-typed !commands from IRC into events.

Untrusted human input -> malformed commands return [] (never crash). Grounded claims
(hypothesis/conclusion) produce a ClaimEvent + JustifyEvent and require existing premises;
evidence is a raw premise and takes no premises.
"""
from hearsay.irc.parser import IRCMessage
from hearsay.protocol.codec import decode_human_command
from hearsay.protocol.events import ClaimEvent, JustifyEvent, RetractClaimEvent, ChallengeEvent


def _msg(text, nick="alice"):
    return IRCMessage(command="PRIVMSG", prefix=f"{nick}!u@h", params=["#evidence", text])


def _allocator():
    counter = {"n": 0}
    def allocate():
        counter["n"] += 1
        return f"h{counter['n']}"
    return allocate


class FakeBoard:
    """Minimal board: claim_events maps id -> an object with a .level, for premise checks."""
    def __init__(self, levels):
        class _C:
            def __init__(self, level): self.level = level
        self.claim_events = {cid: _C(lv) for cid, lv in levels.items()}


def _board():
    # a couple of existing evidence claims (level 0) to justify hypotheses against
    return FakeBoard({"e1": 0, "e2": 0})


def test_claim_evidence_no_premises():
    evs = decode_human_command(_msg("!claim evidence 0.9 CPU spiked at 03:14"), _allocator(), _board())
    assert len(evs) == 1
    ev = evs[0]
    assert isinstance(ev, ClaimEvent) and ev.kind == "evidence" and ev.level == 0
    assert ev.credibility == 0.9 and ev.text == "CPU spiked at 03:14"
    assert ev.claim_id == "h1" and ev.author == "alice"


def test_claim_evidence_rejects_premises():
    # evidence is foundational -> premises not allowed
    assert decode_human_command(_msg("!claim evidence 0.9 premises=e1 text"), _allocator(), _board()) == []


def test_grounded_hypothesis_makes_claim_and_justification():
    evs = decode_human_command(
        _msg("!claim hypothesis 0.6 premises=e1,e2 the deploy caused it"), _allocator(), _board())
    assert len(evs) == 2
    claim, justify = evs
    assert isinstance(claim, ClaimEvent) and claim.kind == "hypothesis"
    assert claim.level == 1                       # one above the level-0 premises
    assert isinstance(justify, JustifyEvent)
    assert justify.conclusion == claim.claim_id
    assert justify.premises == ("e1", "e2")


def test_hypothesis_without_premises_rejected():
    # the key rule: a hypothesis MUST be grounded
    assert decode_human_command(_msg("!claim hypothesis 0.6 the deploy caused it"), _allocator(), _board()) == []


def test_hypothesis_with_dangling_premise_rejected():
    assert decode_human_command(
        _msg("!claim hypothesis 0.6 premises=nonexistent text"), _allocator(), _board()) == []


def test_conclusion_requires_premises_too():
    evs = decode_human_command(
        _msg("!claim conclusion 0.8 premises=e1 final answer"), _allocator(), _board())
    assert len(evs) == 2 and evs[0].kind == "conclusion"
    assert decode_human_command(_msg("!claim conclusion 0.8 no premises here"), _allocator(), _board()) == []


def test_retract():
    evs = decode_human_command(_msg("!retract c3"), _allocator(), _board())
    assert len(evs) == 1 and isinstance(evs[0], RetractClaimEvent)
    assert evs[0].retract_claim_id == "c3"


def test_challenge():
    evs = decode_human_command(_msg("!challenge h2"), _allocator(), _board())
    assert len(evs) == 1 and isinstance(evs[0], ChallengeEvent)
    assert evs[0].challenge_id == "h2"


def test_ordinary_chatter_ignored():
    assert decode_human_command(_msg("I think the server crashed"), _allocator(), _board()) == []


def test_unknown_command_ignored():
    assert decode_human_command(_msg("!frobnicate xyz"), _allocator(), _board()) == []


def test_bad_kind_ignored():
    assert decode_human_command(_msg("!claim banana 0.9 text"), _allocator(), _board()) == []


def test_bad_credibility_ignored():
    assert decode_human_command(_msg("!claim evidence notanumber text"), _allocator(), _board()) == []
    assert decode_human_command(_msg("!claim evidence 1.5 out of range"), _allocator(), _board()) == []


def test_missing_text_ignored():
    assert decode_human_command(_msg("!claim evidence 0.9"), _allocator(), _board()) == []


def test_truncated_commands_dont_crash():
    for text in ["!claim", "!claim evidence", "!retract", "!challenge", "!"]:
        assert decode_human_command(_msg(text), _allocator(), _board()) == []
