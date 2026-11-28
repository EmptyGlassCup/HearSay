"""
Diagnose WHERE and HOW an LLM system fails on the eval problems.

For a chosen system (llm_direct or llm_cot) and depth/seed, it runs the problem, then reports:
  - the exact facts the model got wrong: ORPHANED (said true, actually false) and MISSED
    (actually true, not said) — with each fact's justifications so you can see WHY it is a
    hard case (e.g. a survivor via a deep alternate path),
  - for parse failures: the raw model output and where JSON extraction broke,
  - token count.

This is for understanding the failure modes before/after the aggregate run — not scored.

Run:  $env:DEEPSEEK_API_KEY="sk-..." ; python scripts/diagnose_failures.py [system] [depth] [seed]
      system in {direct, cot}
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hearsay.experts.llm_config import make_client, require_api_key
from eval.problem_generator import generate_problem
from eval.harness import DIRECT_PROMPT, COT_PROMPT, render_rules, _parse_true_facts

SYSTEM = sys.argv[1] if len(sys.argv) > 1 else "cot"
DEPTH = int(sys.argv[2]) if len(sys.argv) > 2 else 40
SEED = int(sys.argv[3]) if len(sys.argv) > 3 else 1

PROMPT = COT_PROMPT if SYSTEM == "cot" else DIRECT_PROMPT


def justifications_of(problem, fid):
    return [premises for (c, premises) in problem.rules if c == fid]


def main():
    require_api_key()
    problem = generate_problem(depth=DEPTH, seed=SEED)
    # Generous output budget so we can tell a reasoning failure from a mere truncation.
    client = make_client(max_tokens=8000)

    prompt = PROMPT.format(
        base_facts=", ".join(problem.base_facts),
        rules_block=render_rules(problem),
        retract_target=problem.retract_target,
    )
    text, usage = client.complete_with_usage(prompt)
    asserted = _parse_true_facts(text)

    print(f"system={SYSTEM} depth={DEPTH} seed={SEED} | {len(problem.all_fact_ids)} facts, "
          f"{len(problem.rules)} rules | retracted {problem.retract_target}")
    print(f"tokens={usage['total_tokens']} (completion={usage['completion_tokens']}) "
          f"finish_reason={usage['finish_reason']}")
    print("=" * 70)
    print("--- FULL MODEL OUTPUT ---\n")
    print(text)
    print("\n" + "=" * 70)

    if asserted is None:
        print("PARSE FAILURE — could not extract a JSON {\"true_facts\": [...]} object.")
        if usage["finish_reason"] == "length":
            print(">> finish_reason=length: the output was TRUNCATED by the token budget, "
                  "not a clean refusal. The model ran out of room mid-answer.")
        else:
            print(">> finish_reason=stop: the model finished but never emitted the requested "
                  "JSON format — it deviated from the instructions on its own.")
        return

    asserted &= set(problem.all_fact_ids)
    truth = problem.ground_truth_after
    orphaned = sorted(asserted - truth)       # said true, actually false
    missed = sorted(truth - asserted)         # actually true, not said

    print(f"EXACT MATCH: {asserted == truth}")
    print(f"orphaned ({len(orphaned)}): said TRUE but actually FALSE")
    for fid in orphaned:
        print(f"   {fid}  justifications={justifications_of(problem, fid)}  "
              f"(all now broken -> should be FALSE)")
    print(f"missed ({len(missed)}): actually TRUE but model dropped")
    for fid in missed:
        print(f"   {fid}  justifications={justifications_of(problem, fid)}  "
              f"(at least one survives -> should be TRUE)")


if __name__ == "__main__":
    main()
