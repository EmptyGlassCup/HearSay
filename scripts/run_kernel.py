"""
Launch the full HearSay kernel: IRC + board + scheduler + experts + web UI.

Prereqs:
  - Ergo running on 127.0.0.1:6667
  - LM Studio server running on http://localhost:1234 with bonsai loaded
    (or set USE_LLM = False to run with only the classical KS)

Run:  python scripts/run_kernel.py
Then: open http://127.0.0.1:8000 (the graph)
      connect HexChat to 127.0.0.1:6667 to watch/participate
      inject evidence with scripts/inject.ps1 (or a raw IRC client)
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hearsay.control.kernel import Kernel
from hearsay.experts.metric_threshold import MetricThresholdKS
from hearsay.experts.llm_client import LocalLLMClient
from hearsay.experts.llm_hypothesis import LLMHypothesisKS

USE_LLM = True
HOST = "127.0.0.1"
PORT = 6667
NICKNAME = "hearsay"
BUDGET = 10
GOAL_THRESHOLD = 0.0


def build_knowledge_sources():
    ks = [MetricThresholdKS()]
    if USE_LLM:
        ks.append(LLMHypothesisKS(llm=LocalLLMClient(), max_hypotheses=2))
    return ks


async def main():
    kernel = Kernel(
        knowledge_sources=build_knowledge_sources(),
        host=HOST,
        port=PORT,
        nickname=NICKNAME,
        budget=BUDGET,
        goal_threshold=GOAL_THRESHOLD,
    )
    print("Kernel starting. UI at http://127.0.0.1:8000")
    await kernel.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
