# Phase 7 — Evaluation

Goal: evidence for HearSay's thesis vs a traditional (non-blackboard) LLM architecture.

## Claims under test

1. CORRECTNESS: after a fact is retracted, a baseline LLM orphans beliefs (still asserts
   conclusions with no valid support) and/or over-retracts (drops still-supported ones).
   Error grows with dependency depth. HearSay is correct by construction (error = 0).
2. COST (the unconditional win): propagating a retraction costs HearSay ZERO tokens (pure
   JTMS recomputation, no model call). The baseline must re-reason -> tokens per retraction.
   True even if the baseline is perfectly accurate.

## Method

Synthetic symbolic layered-inference problems (eval/problem_generator.py), parameterised by
DEPTH. Ground truth = HearSay's own JTMS (build, retract, in_set()). The generator tunes the
retraction to remove a partial fraction (~50-78%) with alternate-path survivors, so a solver
must distinguish survivors from casualties (not just "retract everything downstream").

Systems compared:
  - C (HearSay): facts/rules -> claims/justifications; retract -> in_set(). Exact, 0 tokens.
  - B (baseline LLM): same structure rendered as text; "fact X is false, list what holds";
    parse answer, compare to ground truth. Record tokens.
  (A single-LLM variant can be added; B is the serious competitor.)

Metrics after retraction, vs depth:
  - unsupported-claim rate: asserted but NOT in ground truth (orphaned). HearSay 0.
  - missing-claim rate: in ground truth but dropped (over-retracted). HearSay 0.
  - tokens spent propagating the retraction. HearSay 0.

Depth sweep: [2, 5, 10, 20, 40] (extend if the model handles it). The CURVE shape is the
evidence. Note honestly where prompt-size/context (not tracking) becomes the limiter.

## Fairness commitments
- Baseline B gets a strong, good-faith prompt (clear rules, structured output, explicit
  instruction to trace dependencies). No straw man.
- Same source structure rendered to B and C; neither gets an easier version.
- Report honestly even if the correctness win is narrow; the cost win stands regardless.

## Status
- [x] problem_generator.py — layered symbolic problems, JTMS ground truth, partial cascade.
- [x] OpenAICompatClient.complete_with_usage — surfaces token counts for the harness.
- [ ] harness: render problem to text, query baseline, parse, score vs ground truth, sweep.
- [ ] results output (CSV/JSON in eval/results/) + a summary.
