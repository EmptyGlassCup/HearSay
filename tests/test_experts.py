"""
Tests for the domain experts against the seeded latency_spike scenario.

These validate the ingestion (loader) -> board -> classical-KS -> scheduler path with no
LLM involved, so the deterministic foundation is trusted before LLM KSs are added.
"""
from pathlib import Path

from hearsay.board.board import Board
from hearsay.control.scheduler import Scheduler
from hearsay.experts.metric_threshold import MetricThresholdKS
from hearsay.protocol.events import ClaimEvent, RetractClaimEvent

from eval.loader import load_scenario, seed_board

SCENARIO = Path(__file__).resolve().parents[1] / "eval" / "scenarios" / "latency_spike.json"


def _seeded_board():
    board = Board()
    scenario = load_scenario(SCENARIO)
    seed_board(board, scenario)
    return board, scenario


def test_scenario_seeds_evidence():
    board, scenario = _seeded_board()
    in_set = board.jtms.in_set()
    # All six evidence claims are raw premises, so all IN immediately.
    assert in_set == frozenset({"e_cfg", "e_lat", "e_wait", "e_dep", "e_cpu", "e_mem"})


async def test_metric_threshold_ks_produces_interpreted_claims():
    board, _ = _seeded_board()
    scheduler = Scheduler(
        knowledge_sources=[MetricThresholdKS()],
        board=board,
        budget=10,
    )
    await scheduler.run()

    in_set = board.jtms.in_set()
    # The two rules fire off e_mem and e_wait, producing interpreted hypotheses.
    assert "h_mempressure" in in_set
    assert "h_dbcontention" in in_set

    # Each interpreted claim is justified by its triggering evidence.
    assert board.justify_events["j_mempressure"].premises == ("e_mem",)
    assert board.justify_events["j_dbcontention"].premises == ("e_wait",)


async def test_interpreted_claim_ghosts_when_evidence_retracted():
    board, _ = _seeded_board()
    scheduler = Scheduler(knowledge_sources=[MetricThresholdKS()], board=board, budget=10)
    await scheduler.run()
    assert "h_mempressure" in board.jtms.in_set()

    # Retract the misleading memory evidence — the interpreted claim must ghost out.
    board.apply(RetractClaimEvent(author="operator", retract_claim_id="e_mem"))

    in_set = board.jtms.in_set()
    assert "e_mem" not in in_set
    assert "h_mempressure" not in in_set          # ghosted via the justification chain
    assert "h_dbcontention" in in_set             # unaffected — different evidence


# --- LLM hypothesis KS (tested against a fake client, no real model needed) ---

from hearsay.experts.llm_client import LLMClient, LLMError
from hearsay.experts.llm_hypothesis import LLMHypothesisKS


class FakeLLM(LLMClient):
    """Returns a canned response, or raises, to drive the KS deterministically."""
    def __init__(self, response: str, raise_error: bool = False):
        self.response = response
        self.raise_error = raise_error

    def complete(self, prompt: str) -> str:
        if self.raise_error:
            raise LLMError("simulated failure")
        return self.response


async def test_llm_hypothesis_valid_json_produces_claim():
    board, _ = _seeded_board()
    fake = FakeLLM('{"conclusion_text": "Config change caused the latency", '
                   '"premise_ids": ["e_cfg", "e_lat"], "credibility": 0.8}')
    ks = LLMHypothesisKS(llm=fake)

    activations = ks.condition(board)
    events = await ks.action(activations[0], board)

    assert len(events) == 2                       # claim + justification
    claim, justify = events
    assert claim.text == "Config change caused the latency"
    assert justify.premises == ("e_cfg", "e_lat")
    assert claim.credibility == 0.8
    # level derived: both premises are level 0, so hypothesis is level 1
    assert claim.level == 1


async def test_llm_hypothesis_rejects_dangling_premise():
    board, _ = _seeded_board()
    # cites a premise id that does not exist on the board
    fake = FakeLLM('{"conclusion_text": "bogus", "premise_ids": ["nonexistent"], '
                   '"credibility": 0.5}')
    ks = LLMHypothesisKS(llm=fake)
    events = await ks.action(ks.condition(board)[0], board)
    assert events == []                           # rejected, no crash


async def test_llm_hypothesis_rejects_malformed_json():
    board, _ = _seeded_board()
    fake = FakeLLM("sorry, I can't help with that")
    ks = LLMHypothesisKS(llm=fake)
    assert await ks.action(ks.condition(board)[0], board) == []


async def test_llm_hypothesis_survives_llm_failure():
    board, _ = _seeded_board()
    fake = FakeLLM("", raise_error=True)
    ks = LLMHypothesisKS(llm=fake)
    assert await ks.action(ks.condition(board)[0], board) == []


async def test_llm_hypothesis_clamps_credibility():
    board, _ = _seeded_board()
    fake = FakeLLM('{"conclusion_text": "x", "premise_ids": ["e_cfg"], "credibility": 5.0}')
    ks = LLMHypothesisKS(llm=fake)
    events = await ks.action(ks.condition(board)[0], board)
    assert events[0].credibility == 1.0           # clamped from 5.0


async def test_llm_hypothesis_reengages_after_retraction():
    # A declared-done agent must re-engage when external evidence is retracted, so it can
    # rebuild toward the true cause. This is the demo-critical behaviour.
    board, _ = _seeded_board()
    fake = FakeLLM('{"done": true}')
    ks = LLMHypothesisKS(llm=fake)

    # First pass: the agent declares it has nothing to add, so it goes quiet.
    await ks.action(ks.condition(board)[0], board)
    assert ks.condition(board) == []            # quiet on the stable board

    # Retract a piece of external evidence — the board changes under the agent.
    board.apply(RetractClaimEvent(author="operator", retract_claim_id="e_mem"))

    # The agent must now re-engage (condition proposes an activation again).
    assert ks.condition(board) != []            # re-engaged after the retraction


async def test_llm_hypothesis_can_rebuild_ghosted_claim_with_fresh_id():
    # After a claim ghosts (its support retracted), the agent may legitimately re-assert the
    # same statement on surviving evidence. Dedup must NOT block it (ghost != believed), and
    # the new claim must get a fresh, non-colliding id.
    board, _ = _seeded_board()
    same_text = '{"conclusion_text": "The config change is the cause", ' \
                '"premise_ids": ["e_cfg"], "credibility": 0.8}'
    ks = LLMHypothesisKS(llm=FakeLLM(same_text))

    first = await ks.action(ks.condition(board)[0], board)
    assert len(first) == 2
    first_claim_id = first[0].claim_id
    for e in first:
        board.apply(e)
    assert first_claim_id in board.jtms.in_set()

    # Retract e_cfg -> the claim built on it ghosts.
    board.apply(RetractClaimEvent(author="operator", retract_claim_id="e_cfg"))
    assert first_claim_id not in board.jtms.in_set()

    # New surviving evidence the agent can rebuild on, with the same conclusion text.
    board.apply(ClaimEvent(author="t", claim_id="e_cfg2", text="config change, re-confirmed",
                           kind="evidence", level=0, credibility=0.9))
    ks.llm = FakeLLM('{"conclusion_text": "The config change is the cause", '
                     '"premise_ids": ["e_cfg2"], "credibility": 0.8}')

    acts = ks.condition(board)
    assert acts != []                                  # re-engaged
    second = await ks.action(acts[0], board)
    assert len(second) == 2                             # NOT blocked by dedup (old one is a ghost)
    assert second[0].claim_id != first_claim_id         # fresh, non-colliding id
    for e in second:
        board.apply(e)                                  # must not raise on duplicate id
