"""
Watch HearSay solve an eval problem in the web UI.

Loads a generated symbolic problem onto a board, serves the graph, waits, then applies the
same retraction the eval uses — so you can watch the cascade ripple through the dependency
layers and see the surviving-vs-ghosted split that the eval scores as 0 error.

Note: eval problems are SYMBOLIC (f0, d5, ...), so the graph is abstract — this is to see
the mechanism, not for a polished demo.

Run:  python scripts/view_eval_problem.py [depth]
Then: open http://127.0.0.1:8000
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hearsay.board.board import Board
from hearsay.protocol.events import ClaimEvent, JustifyEvent, RetractClaimEvent
from hearsay.ui.server import UIServer
from eval.problem_generator import generate_problem

DEPTH = int(sys.argv[1]) if len(sys.argv) > 1 else 5


def load_problem_onto_board(board, problem):
    # Base facts and derived facts all become claims. Base = evidence (level 0); derived get
    # a level by their longest dependency chain so the UI lays them out by layer.
    level = {fid: 0 for fid in problem.base_facts}

    # First pass: create every claim. Level for derived facts is filled in as we add rules.
    for fid in problem.all_fact_ids:
        kind = "evidence" if fid in problem.base_facts else "hypothesis"
        board.apply(ClaimEvent(author="eval", claim_id=fid, text=fid,
                               kind=kind, level=level.get(fid, 1), credibility=1.0))

    # Add justifications. (Level was approximated at creation; fine for layout.)
    for i, (conclusion, premises) in enumerate(problem.rules):
        board.apply(JustifyEvent(author="eval", justification_id=f"j{i}",
                                 conclusion=conclusion, premises=premises))


async def main():
    problem = generate_problem(depth=DEPTH, seed=1)
    board = Board()
    load_problem_onto_board(board, problem)

    ui = UIServer(board)
    await ui.start(host="127.0.0.1", port=8000)
    await asyncio.sleep(1)
    await ui.broadcast()

    print(f"Loaded depth-{DEPTH} problem: {len(problem.all_fact_ids)} facts, "
          f"{len(problem.rules)} rules. UI at http://127.0.0.1:8000")
    print(f"IN now: {len(board.jtms.in_set())} facts.")
    print(f"In 15s, retracting '{problem.retract_target}' — watch the cascade.")
    await asyncio.sleep(15)

    board.apply(RetractClaimEvent(author="operator", retract_claim_id=problem.retract_target))
    await ui.broadcast()

    after = board.jtms.in_set()
    print(f"Retracted {problem.retract_target}. IN now: {len(after)} facts "
          f"(ground truth after: {len(problem.ground_truth_after)}).")
    print(f"Match ground truth: {after == problem.ground_truth_after}")
    print("Leaving the UI up. Ctrl+C to stop.")
    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
