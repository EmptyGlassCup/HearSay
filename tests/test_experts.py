"""
Tests for the domain experts: a classical threshold KS and the LLM hypothesis KS.

Self-contained: they seed a small board inline rather than loading a scenario file, so they
test the KS mechanics generically (not against any particular demo scenario).
"""
from hearsay.board.board import Board
from hearsay.control.scheduler import Scheduler
from hearsay.experts.metric_threshold import MetricThresholdKS, ThresholdRule
from hearsay.experts.llm_client import LLMClient, LLMError
from hearsay.experts.llm_hypothesis import LLMHypothesisKS
from hearsay.protocol.events import ClaimEvent, RetractClaimEvent


def _board(evidence):
    """Board seeded with evidence claims. `evidence` is {id: (text, credibility)}."""
    board = Board()
    for cid, (text, cred) in evidence.items():
        board.apply(ClaimEvent(author="t", claim_id=cid, text=text,
                               kind="evidence", level=0, credibility=cred))
    return board


# ---- classical threshold KS -------------------------------------------------

RULES = (
    ThresholdRule(trigger_evidence_id="e_mem", conclusion_id="h_mem",
                  conclusion_text="memory under pressure", justification_id="j_mem",
                  credibility=0.7),
    ThresholdRule(trigger_evidence_id="e_wait", conclusion_id="h_db",
                  conclusion_text="db pool saturated", justification_id="j_db",
                  credibility=0.8),
)


async def test_metric_threshold_produces_interpreted_claims():
    board = _board({"e_mem": ("mem 95%", 0.9), "e_wait": ("db wait 3800ms", 0.9)})
    await Scheduler([MetricThresholdKS(rules=RULES)], board, budget=10).run()

    in_set = board.jtms.in_set()
    assert "h_mem" in in_set and "h_db" in in_set
    assert board.justify_events["j_mem"].premises == ("e_mem",)
    assert board.justify_events["j_db"].premises == ("e_wait",)


async def test_interpreted_claim_ghosts_when_evidence_retracted():
    board = _board({"e_mem": ("mem 95%", 0.9), "e_wait": ("db wait 3800ms", 0.9)})
    await Scheduler([MetricThresholdKS(rules=RULES)], board, budget=10).run()
    assert "h_mem" in board.jtms.in_set()

    board.apply(RetractClaimEvent(author="op", retract_claim_id="e_mem"))
    in_set = board.jtms.in_set()
    assert "e_mem" not in in_set
    assert "h_mem" not in in_set       # ghosted via its justification
    assert "h_db" in in_set            # unaffected (different evidence)


# ---- LLM hypothesis KS (fake client, no real model needed) ------------------

class FakeLLM(LLMClient):
    def __init__(self, response: str, raise_error: bool = False):
        self.response = response
        self.raise_error = raise_error

    def complete(self, prompt: str) -> str:
        if self.raise_error:
            raise LLMError("simulated failure")
        return self.response


def _llm_board():
    return _board({"e_cfg": ("config change", 0.95), "e_lat": ("latency rose", 0.99)})


async def test_llm_hypothesis_valid_json_produces_claim():
    board = _llm_board()
    fake = FakeLLM('{"conclusion_text": "Config change caused the latency", '
                   '"premise_ids": ["e_cfg", "e_lat"], "credibility": 0.8}')
    ks = LLMHypothesisKS(llm=fake)
    events = await ks.action(ks.condition(board)[0], board)
    assert len(events) == 2
    claim, justify = events
    assert claim.text == "Config change caused the latency"
    assert justify.premises == ("e_cfg", "e_lat")
    assert claim.credibility == 0.8
    assert claim.level == 1            # one above the level-0 premises


async def test_llm_hypothesis_rejects_dangling_premise():
    board = _llm_board()
    fake = FakeLLM('{"conclusion_text": "bogus", "premise_ids": ["nonexistent"], "credibility": 0.5}')
    assert await LLMHypothesisKS(llm=fake).action(
        LLMHypothesisKS(llm=fake).condition(board)[0], board) == []


async def test_llm_hypothesis_rejects_malformed_json():
    board = _llm_board()
    ks = LLMHypothesisKS(llm=FakeLLM("sorry, I can't help"))
    assert await ks.action(ks.condition(board)[0], board) == []


async def test_llm_hypothesis_survives_llm_failure():
    board = _llm_board()
    ks = LLMHypothesisKS(llm=FakeLLM("", raise_error=True))
    assert await ks.action(ks.condition(board)[0], board) == []


async def test_llm_hypothesis_clamps_credibility():
    board = _llm_board()
    ks = LLMHypothesisKS(llm=FakeLLM(
        '{"conclusion_text": "x", "premise_ids": ["e_cfg"], "credibility": 5.0}'))
    events = await ks.action(ks.condition(board)[0], board)
    assert events[0].credibility == 1.0


async def test_llm_hypothesis_reengages_after_retraction():
    board = _llm_board()
    ks = LLMHypothesisKS(llm=FakeLLM('{"done": true}'))
    await ks.action(ks.condition(board)[0], board)
    assert ks.condition(board) == []                   # quiet on a stable board
    board.apply(RetractClaimEvent(author="op", retract_claim_id="e_cfg"))
    assert ks.condition(board) != []                   # re-engaged after the retraction


async def test_llm_hypothesis_can_rebuild_ghosted_claim_with_fresh_id():
    board = _llm_board()
    text = '{"conclusion_text": "The config change is the cause", ' \
           '"premise_ids": ["e_cfg"], "credibility": 0.8}'
    ks = LLMHypothesisKS(llm=FakeLLM(text))

    first = await ks.action(ks.condition(board)[0], board)
    assert len(first) == 2
    first_id = first[0].claim_id
    for e in first:
        board.apply(e)
    assert first_id in board.jtms.in_set()

    board.apply(RetractClaimEvent(author="op", retract_claim_id="e_cfg"))
    assert first_id not in board.jtms.in_set()

    board.apply(ClaimEvent(author="t", claim_id="e_cfg2", text="re-confirmed",
                           kind="evidence", level=0, credibility=0.9))
    ks.llm = FakeLLM('{"conclusion_text": "The config change is the cause", '
                     '"premise_ids": ["e_cfg2"], "credibility": 0.8}')
    acts = ks.condition(board)
    assert acts != []
    second = await ks.action(acts[0], board)
    assert len(second) == 2 and second[0].claim_id != first_id
    for e in second:
        board.apply(e)                                 # must not raise on duplicate id
