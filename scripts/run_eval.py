"""
Run the evaluation: HearSay vs a baseline LLM across a depth sweep.

Secrets: DeepSeek key read from DEEPSEEK_API_KEY (never committed).
Run:  $env:DEEPSEEK_API_KEY = "sk-..." ; python scripts/run_eval.py
Output: eval/results/eval_<timestamp>.json plus a printed summary.
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hearsay.experts.llm_client import OpenAICompatClient
from eval.harness import run_eval, save_results

DEPTHS = [2, 5, 10, 20, 40]


def main():
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise SystemExit('Set DEEPSEEK_API_KEY first: $env:DEEPSEEK_API_KEY = "sk-..."')

    client = OpenAICompatClient(
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        api_key=key,
        timeout=180.0,
    )

    print("Running evaluation (each depth makes one baseline LLM call)...\n")
    results = run_eval(DEPTHS, client, seed=1)

    out_dir = Path(__file__).resolve().parents[1] / "eval" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"eval_{int(time.time())}.json"
    save_results(results, out_path)

    print(f"\nSaved to {out_path}")
    print("\nSummary (baseline error grows with depth; HearSay stays at 0):")
    print(f"{'depth':>6} {'b_unsupported':>14} {'b_missing':>10} {'b_tokens':>9}")
    for r in results:
        if r.system == "baseline":
            print(f"{r.depth:>6} {r.unsupported:>14} {r.missing:>10} {r.tokens:>9}")


if __name__ == "__main__":
    main()
