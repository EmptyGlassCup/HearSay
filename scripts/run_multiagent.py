"""
Multi-agent run: two LLM agents (DeepSeek + local bonsai) competing on the same board.

Each agent is an LLMHypothesisKS with its own backend, name, and id prefix. They see each
other's hypotheses on the board (via the prompt) and are asked for NEW ones, so they build
on or differ from each other. The scheduler ranks their proposals.

Secrets: the DeepSeek key is read from the DEEPSEEK_API_KEY environment variable. It is
NEVER hard-coded or committed. Set it in your shell before running:
    $env:DEEPSEEK_API_KEY = "sk-..."     (PowerShell)

Prereqs:
  - Ergo on 127.0.0.1:6667
  - LM Studio server on http://localhost:1234 with bonsai loaded (for the local agent)
  - DEEPSEEK_API_KEY set (for the remote agent); if unset, runs with the local agent only

Run:  python scripts/run_multiagent.py
Then: open http://127.0.0.1:8000 ; inject with scripts/inject_checkout.ps1
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hearsay.control.kernel import Kernel
from hearsay.experts.llm_client import OpenAICompatClient
from hearsay.experts.llm_hypothesis import LLMHypothesisKS
from eval.loader import load_scenario

HOST = "127.0.0.1"
PORT = 6667
NICKNAME = "hearsay"
BUDGET = 12
GOAL_THRESHOLD = 0.0

SCENARIO = Path(__file__).resolve().parents[1] / "eval" / "scenarios" / "checkout_timeout_amplification.json"
QUESTION = load_scenario(SCENARIO).question


def build_agents():
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise SystemExit(
            "DEEPSEEK_API_KEY is not set. Set it first:\n"
            '  $env:DEEPSEEK_API_KEY = "sk-..."   (PowerShell)'
        )

    agent = LLMHypothesisKS(
        llm=OpenAICompatClient(
            base_url="https://api.deepseek.com/v1",
            model="deepseek-chat",
            api_key=key,
        ),
        name="deepseek",
        id_prefix="ds",
        question=QUESTION,
        max_hypotheses=5,
    )
    print("Running with the DeepSeek agent.")
    agents = [agent]

    return agents


async def main():
    kernel = Kernel(
        knowledge_sources=build_agents(),
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
