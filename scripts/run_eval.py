"""
Run the evaluation: HearSay vs a baseline LLM across a depth sweep.

Secrets: DeepSeek key read from DEEPSEEK_API_KEY (never committed).
Run:  $env:DEEPSEEK_API_KEY = "sk-..." ; python scripts/run_eval.py
Output: eval/results/eval_<timestamp>.json plus a printed summary.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hearsay.experts.llm_config import make_client, require_api_key
from eval.harness import run_eval, save_results

# Correctness sweep is capped at depths where the model can produce a COMPLETE answer.
# Beyond ~depth 50 it hits its output-token ceiling (see the token-growth study), where
# "wrong" and "couldn't finish" blur — so we keep correctness to the feasible range.
# Correctness sweep is capped at depths where the model can produce a COMPLETE answer.
# Beyond ~depth 50 it hits its output-token ceiling (see the token-growth study).
DEPTHS = [2, 5, 10, 20, 30, 40]
SEEDS = (1, 2, 3, 4, 5)
MAX_TOKENS = 32000                # high, so complete answers don't truncate at the deep end


def main():
    require_api_key()
    # Model/base_url/timeout come from central config (env or defaults); max_tokens is an
    # experiment-specific override for this correctness sweep.
    client = make_client(max_tokens=MAX_TOKENS, thinking=True)   # consistent with prior eval runs

    n_calls = len(DEPTHS) * len(SEEDS) * 2  # two LLM systems (direct + cot) per problem
    print(f"Running evaluation: {len(DEPTHS)} depths x {len(SEEDS)} seeds, "
          f"~{n_calls} LLM calls total...\n")
    results = run_eval(DEPTHS, client, seeds=SEEDS)

    out_dir = Path(__file__).resolve().parents[1] / "eval" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"eval_{int(time.time())}.json"
    save_results(results, out_path)

    print(f"\nSaved to {out_path}")
    print("\nAggregates (mean over seeds):")
    print(f"{'system':>11} {'depth':>6} {'mean_err':>9} {'std_err':>8} {'mean_tokens':>12} {'parse_fail':>10}")
    for a in results["aggregates"]:
        err = "n/a" if a["mean_error"] is None else f"{a['mean_error']:.1f}"
        tok = "n/a" if a["mean_tokens"] is None else f"{a['mean_tokens']:.0f}"
        print(f"{a['system']:>11} {a['depth']:>6} {err:>9} "
              f"{a['std_error']:>8.1f} {tok:>12} {a['parse_failures']:>10}")


if __name__ == "__main__":
    main()
