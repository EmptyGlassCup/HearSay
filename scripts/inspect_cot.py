"""
Inspect the chain-of-thought model's actual reasoning on one eval problem.

Runs the CoT prompt against DeepSeek for a single (depth, seed), prints the full raw reply
(the reasoning trace + final JSON), then scores it against ground truth so you can see both
WHAT it reasoned and WHETHER it got it right.

Run:  $env:DEEPSEEK_API_KEY="sk-..." ; python scripts/inspect_cot.py [depth] [seed]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hearsay.experts.llm_config import make_client, require_api_key
from eval.problem_generator import generate_problem
from eval.harness import COT_PROMPT, render_rules, _parse_true_facts

DEPTH = int(sys.argv[1]) if len(sys.argv) > 1 else 10
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 1


def main():
    require_api_key()
    problem = generate_problem(depth=DEPTH, seed=SEED)
    client = make_client()

    prompt = COT_PROMPT.format(
        base_facts=", ".join(problem.base_facts),
        rules_block=render_rules(problem),
        retract_target=problem.retract_target,
    )

    print("=" * 70)
    print(f"PROBLEM: depth={DEPTH} seed={SEED} | {len(problem.all_fact_ids)} facts, "
          f"{len(problem.rules)} rules | retracting {problem.retract_target}")
    print("=" * 70)
    print("\n--- PROMPT SENT ---\n")
    print(prompt)

    text, usage = client.complete_with_usage(prompt)

    print("\n--- MODEL REASONING (raw reply) ---\n")
    print(text)

    asserted = _parse_true_facts(text) or set()
    asserted &= set(problem.all_fact_ids)
    truth = problem.ground_truth_after

    print("\n--- SCORING ---")
    print(f"tokens: {usage['total_tokens']}")
    print(f"ground-truth TRUE facts ({len(truth)}): {sorted(truth)}")
    print(f"model said TRUE     ({len(asserted)}): {sorted(asserted)}")
    print(f"orphaned (said true, actually false): {sorted(asserted - truth)}")
    print(f"missed   (actually true, not said):  {sorted(truth - asserted)}")
    print(f"EXACT MATCH: {asserted == truth}")


if __name__ == "__main__":
    main()
