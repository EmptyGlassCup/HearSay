"""
Measure how the LLM's token cost grows with problem depth.

For a thinking model (deepseek-reasoner), the real cost is reasoning_tokens + completion_tokens
-- the internal chain-of-thought plus the visible answer. HearSay's cost is 0 regardless of
depth. This script quantifies the LLM's growth curve: mean +/- spread per depth over several
seeds, plus a linear-vs-exponential fit over the tested range.

This is a COST/SCALING measurement (not correctness). Output budget is set high so the model
finishes naturally; any finish_reason=length is recorded as "wanted more than the cap".

Run:  $env:DEEPSEEK_API_KEY="sk-..." ; python scripts/measure_token_growth.py
Output: eval/results/token_growth_<ts>.json + printed table + fit.
"""
import math
import json
import sys
import time
from pathlib import Path
from statistics import mean, pstdev

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hearsay.experts.llm_config import make_client, require_api_key
from eval.problem_generator import generate_problem
from eval.harness import COT_PROMPT, render_rules

DEPTHS = [50, 60]              # already measured 5-40 on this model; filling the deep end
SEEDS = (1, 2, 3, 4, 5, 6)
MAX_TOKENS = 64000   # model/base_url come from central config (hearsay.experts.llm_config)


def measure_one(client, depth, seed):
    problem = generate_problem(depth=depth, seed=seed)
    prompt = COT_PROMPT.format(
        base_facts=", ".join(problem.base_facts),
        rules_block=render_rules(problem),
        retract_target=problem.retract_target,
    )
    _text, usage = client.complete_with_usage(prompt)
    reasoning = usage.get("reasoning_tokens", 0)
    completion = usage.get("completion_tokens", 0)
    return {
        "depth": depth, "seed": seed,
        "n_facts": len(problem.all_fact_ids),
        "reasoning_tokens": reasoning,
        "completion_tokens": completion,
        "output_tokens": reasoning + completion,     # the cost of reasoning + answering
        "total_tokens": usage.get("total_tokens", 0),
        "truncated": usage.get("finish_reason") == "length",
    }


def fit_linear_and_exp(depths, means):
    """Return (linear R^2, exponential R^2) of output-tokens vs depth over the tested range."""
    xs = depths
    ys = means
    n = len(xs)
    if n < 3:
        return None, None

    def r2(pred):
        ybar = mean(ys)
        ss_tot = sum((y - ybar) ** 2 for y in ys)
        ss_res = sum((y - p) ** 2 for y, p in zip(ys, pred))
        return 1 - ss_res / ss_tot if ss_tot else 0.0

    # linear least squares y = a + b x
    xbar, ybar = mean(xs), mean(ys)
    b = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys)) / sum((x - xbar) ** 2 for x in xs)
    a = ybar - b * xbar
    lin_pred = [a + b * x for x in xs]

    # exponential: fit log(y) = log(A) + k x  (requires positive y)
    exp_pred = None
    if all(y > 0 for y in ys):
        ly = [math.log(y) for y in ys]
        lybar = mean(ly)
        k = sum((x - xbar) * (l - lybar) for x, l in zip(xs, ly)) / sum((x - xbar) ** 2 for x in xs)
        logA = lybar - k * xbar
        exp_pred = [math.exp(logA + k * x) for x in xs]

    return r2(lin_pred), (r2(exp_pred) if exp_pred else None)


def main():
    require_api_key()
    client = make_client(max_tokens=MAX_TOKENS, thinking=True)   # measuring reasoning tokens

    out_dir = Path(__file__).resolve().parents[1] / "eval" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    incremental_path = out_dir / f"token_growth_{int(time.time())}.jsonl"
    print(f"(saving each row to {incremental_path} as it completes)\n")

    from hearsay.experts.llm_client import LLMError
    rows = []
    for depth in DEPTHS:
        per_depth = []
        for seed in SEEDS:
            try:
                r = measure_one(client, depth, seed)
            except LLMError as exc:
                print(f"depth={depth:3d} seed={seed}  CALL FAILED after retries: {exc} (skipping)")
                continue
            rows.append(r)
            per_depth.append(r["output_tokens"])
            # Append-save immediately so a later crash never loses collected data.
            with open(incremental_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(r) + "\n")
            flag = " [TRUNCATED]" if r["truncated"] else ""
            print(f"depth={depth:3d} seed={seed} facts={r['n_facts']:3d} "
                  f"reasoning={r['reasoning_tokens']:6d} completion={r['completion_tokens']:5d} "
                  f"output={r['output_tokens']:6d}{flag}")
        if per_depth:
            print(f"  -> depth {depth}: mean output = {mean(per_depth):.0f} "
                  f"+/- {pstdev(per_depth):.0f}  (n={len(per_depth)})")

    # Only aggregate over depths that actually produced data.
    depths = [d for d in DEPTHS if any(r["depth"] == d for r in rows)]
    means = [mean([r["output_tokens"] for r in rows if r["depth"] == d]) for d in depths]
    lin_r2, exp_r2 = fit_linear_and_exp(depths, means)

    print("\nGrowth of (reasoning+completion) output tokens vs depth:")
    for d, m in zip(depths, means):
        print(f"  depth {d:3d}: {m:8.0f} tokens")
    print(f"\nlinear fit R^2 = {lin_r2}")
    print(f"exponential fit R^2 = {exp_r2}")
    print("(More points needed to claim a functional form; report as 'consistent with ...'.)")

    out_path = out_dir / f"token_growth_summary_{int(time.time())}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"rows": rows, "means": dict(zip(map(str, depths), means)),
                   "linear_r2": lin_r2, "exponential_r2": exp_r2}, f, indent=2)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
