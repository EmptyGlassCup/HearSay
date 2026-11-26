"""
Visual check of the web UI (no kernel, no IRC).

Builds a board, seeds the latency_spike scenario, runs the classical KS to produce
interpreted claims, starts the UI server, and broadcasts the graph. Then, after a pause,
retracts the misleading memory evidence and broadcasts again — so you can watch the
memory-pressure claim ghost out live in the browser.

Run:  python scripts/test_ui_live.py
Then open http://127.0.0.1:8000 in a browser.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hearsay.board.board import Board
from hearsay.control.scheduler import Scheduler
from hearsay.experts.metric_threshold import MetricThresholdKS
from hearsay.protocol.events import RetractClaimEvent
from hearsay.ui.server import UIServer

from eval.loader import load_scenario, seed_board

SCENARIO = Path(__file__).resolve().parents[1] / "eval" / "scenarios" / "latency_spike.json"


async def main():
    board = Board()
    seed_board(board, load_scenario(SCENARIO))

    # Produce interpreted claims so the graph has some depth.
    Scheduler(knowledge_sources=[MetricThresholdKS()], board=board, budget=10).run()

    ui = UIServer(board)
    await ui.start(host="127.0.0.1", port=8000)
    await asyncio.sleep(1)  # let uvicorn bind
    await ui.broadcast()

    print("UI running at http://127.0.0.1:8000")
    print("Open it now. In 15 seconds, e_mem will be retracted — watch it ghost out.")
    await asyncio.sleep(15)

    board.apply(RetractClaimEvent(author="operator", retract_claim_id="e_mem"))
    await ui.broadcast()
    print("Retracted e_mem. h_mempressure should now be dimmed.")

    print("Leaving the server up. Ctrl+C to stop.")
    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
