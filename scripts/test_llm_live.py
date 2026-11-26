"""
Live test of the LLM hypothesis KS against LM Studio (bonsai).

Prereqs: LM Studio running, model loaded, local server started on http://localhost:1234.
Run:  python scripts/test_llm_live.py
"""
from pathlib import Path

from hearsay.board.board import Board
from hearsay.control.scheduler import Scheduler
from hearsay.experts.metric_threshold import MetricThresholdKS
from hearsay.experts.llm_client import LocalLLMClient
from hearsay.experts.llm_hypothesis import LLMHypothesisKS

from eval.loader import load_scenario, seed_board

SCENARIO = Path(__file__).resolve().parents[1] / "eval" / "scenarios" / "latency_spike.json"


def main():
    board = Board()
    scenario = load_scenario(SCENARIO)
    seed_board(board, scenario)
    print(f"Scenario: {scenario.title}")
    print(f"Seeded evidence IN: {sorted(board.jtms.in_set())}\n")

    llm = LocalLLMClient()  # defaults to http://localhost:1234, model bonsai-27b
    scheduler = Scheduler(
        knowledge_sources=[MetricThresholdKS(), LLMHypothesisKS(llm=llm, max_hypotheses=2)],
        board=board,
        budget=10,
    )

    print("Running scheduler (LLM calls may take several seconds each)...\n")
    scheduler.run()

    print("Final claims on the board:")
    for cid in sorted(board.claim_events):
        ev = board.claim_events[cid]
        state = "IN " if cid in board.jtms.in_set() else "OUT"
        print(f"  [{state}] {cid} (L{ev.level}, conf={ev.credibility}): {ev.text}")

    print("\nJustifications:")
    for jid, ev in board.justify_events.items():
        print(f"  {jid}: {ev.conclusion} <- {list(ev.premises)}")


if __name__ == "__main__":
    main()
