"""
Launch the full HearSay kernel for interactive use: IRC + board + scheduler + LLM agent + UI.

Prereqs:
  - Ergo running on 127.0.0.1:6667
  - An LLM configured (see hearsay.experts.llm_config / the README). For a hosted API:
        $env:HEARSAY_LLM_API_KEY = "sk-..."
    For a local model:
        $env:HEARSAY_LLM_BASE_URL = "http://localhost:1234/v1"
        $env:HEARSAY_LLM_MODEL    = "<local-model-id>"

Run:  python scripts/run_kernel.py
Then: open http://127.0.0.1:8000 and connect an IRC client to 127.0.0.1:6667.
      In IRC: set the question with  !goal <text>, add evidence with !claim ...,
      then press "Run analysis" in the web UI.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hearsay.control.kernel import Kernel
from hearsay.experts.llm_config import make_client, get_api_key
from hearsay.experts.llm_hypothesis import LLMHypothesisKS

HOST = "127.0.0.1"
PORT = 6667
NICKNAME = "hearsay"
BUDGET = 10
GOAL_THRESHOLD = 0.0


async def main():
    # Don't hard-exit on a missing key: let the kernel start so the UI can show the warning.
    # (A local endpoint legitimately needs no key.)
    key_present = get_api_key() is not None
    agent = LLMHypothesisKS(
        llm=make_client(),
        name="agent",
        id_prefix="a",
        max_hypotheses=5,
    )
    kernel = Kernel(
        knowledge_sources=[agent],
        host=HOST,
        port=PORT,
        nickname=NICKNAME,
        budget=BUDGET,
        goal_threshold=GOAL_THRESHOLD,
        llm_key_present=key_present,
    )
    print("Kernel starting. UI at http://127.0.0.1:8000")
    print('In IRC: !goal <question>  then  !claim evidence 0.9 <fact>  then press Run analysis.')
    await kernel.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
