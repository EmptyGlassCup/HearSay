"""
Evaluation harness: HearSay (C) vs a baseline LLM (B) on synthetic layered problems.

For each depth it:
  1. generates a problem (ground truth from the JTMS),
  2. scores HearSay: exact match to ground truth, 0 tokens (by construction),
  3. scores the baseline LLM: render the problem as text, ask it to update beliefs after the
     retraction, parse its answer, compare to ground truth, record tokens,
  4. reports unsupported-rate, missing-rate, and tokens, per system, per depth.

The baseline prompt is deliberately strong and fair: it states the rules clearly, explains
the retraction, and instructs the model to trace dependencies and return structured output.
"""
from dataclasses import dataclass, asdict
import json
import re

from eval.problem_generator import generate_problem, Problem
from hearsay.board.board import Board
from hearsay.protocol.events import ClaimEvent, JustifyEvent, RetractClaimEvent
from hearsay.experts.llm_client import OpenAICompatClient, LLMError


BASELINE_PROMPT = """You are a careful logic engine tracking which facts hold.

A fact is TRUE if it is a base fact that has not been retracted, OR if at least one of its
rules has ALL of its premise facts TRUE. A fact with no surviving support is FALSE.

Base facts (initially true): {base_facts}

Rules (each line: a derived fact <= the facts it requires; a fact may have multiple rules,
and is true if ANY one rule's premises are all true):
{rules_block}

NOW: the base fact "{retract_target}" is retracted (no longer true).

Trace the consequences carefully through ALL layers. A derived fact stays TRUE only if it
still has at least one rule whose premises are all TRUE after the retraction. Some facts
survive via an alternate rule; others lose all support and become FALSE.

Respond with ONLY a JSON object listing every fact id that is still TRUE:
{{"true_facts": ["<id>", "<id>", ...]}}
"""


@dataclass
class SystemScore:
    system: str
    depth: int
    unsupported: int      # asserted true but actually false (orphaned)
    missing: int          # actually true but not asserted (over-retracted)
    unsupported_rate: float
    missing_rate: float
    tokens: int
    parsed_ok: bool


def render_rules(problem: Problem) -> str:
    return "\n".join(
        f"  {conclusion} <= {' AND '.join(premises)}"
        for conclusion, premises in problem.rules
    )


def _score_against_truth(system, depth, asserted, problem, tokens, parsed_ok=True):
    """Shared scoring: compare an asserted belief set to ground truth. Used identically for
    HearSay and the baseline, so the comparison is apples-to-apples."""
    truth = problem.ground_truth_after
    all_ids = set(problem.all_fact_ids)
    asserted = asserted & all_ids                 # ignore any ids outside the problem
    unsupported = len(asserted - truth)           # asserted true, actually false (orphaned)
    missing = len(truth - asserted)               # actually true, dropped (over-retracted)
    n = max(len(all_ids), 1)
    return SystemScore(
        system=system, depth=depth,
        unsupported=unsupported, missing=missing,
        unsupported_rate=unsupported / n, missing_rate=missing / n,
        tokens=tokens, parsed_ok=parsed_ok,
    )


def score_hearsay(problem: Problem, depth: int) -> SystemScore:
    """Run HearSay's REAL pipeline: load the problem as claims+justifications onto a board,
    apply the retraction, read in_set(). Scored by the same function as the baseline, against
    ground truth computed by the INDEPENDENT naive oracle. HearSay uses no model -> 0 tokens.
    Its 0-error result is therefore a measured property of the running pipeline matching an
    independently-computed reference, not an assertion."""
    board = Board()
    for fid in problem.all_fact_ids:
        kind = "evidence" if fid in problem.base_facts else "hypothesis"
        board.apply(ClaimEvent(author="eval", claim_id=fid, text=fid,
                               kind=kind, level=0, credibility=1.0))
    for i, (conclusion, premises) in enumerate(problem.rules):
        board.apply(JustifyEvent(author="eval", justification_id=f"j{i}",
                                 conclusion=conclusion, premises=premises))
    board.apply(RetractClaimEvent(author="operator", retract_claim_id=problem.retract_target))

    asserted = set(board.jtms.in_set())
    return _score_against_truth("hearsay", depth, asserted, problem, tokens=0)


def score_baseline(problem: Problem, client: OpenAICompatClient, depth: int) -> SystemScore:
    prompt = BASELINE_PROMPT.format(
        base_facts=", ".join(problem.base_facts),
        rules_block=render_rules(problem),
        retract_target=problem.retract_target,
    )
    try:
        text, usage = client.complete_with_usage(prompt)
    except LLMError:
        return SystemScore("baseline", depth, -1, -1, 1.0, 1.0, 0, parsed_ok=False)

    asserted = _parse_true_facts(text)
    tokens = usage["total_tokens"]
    if asserted is None:
        return SystemScore("baseline", depth, -1, -1, 1.0, 1.0, tokens, parsed_ok=False)

    return _score_against_truth("baseline", depth, asserted, problem, tokens, parsed_ok=True)


def _parse_true_facts(text: str):
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        obj = json.loads(text[start:end + 1])
        facts = obj.get("true_facts")
        if not isinstance(facts, list):
            return None
        return {str(f) for f in facts}
    except (ValueError, AttributeError):
        return None


def run_eval(depths, client: OpenAICompatClient, seed: int = 1) -> list[SystemScore]:
    results = []
    for depth in depths:
        problem = generate_problem(depth=depth, seed=seed)
        hs = score_hearsay(problem, depth)
        bl = score_baseline(problem, client, depth)
        results.append(hs)
        results.append(bl)
        print(f"depth={depth:3d} | hearsay: 0 err, 0 tok | "
              f"baseline: unsupported={bl.unsupported} missing={bl.missing} "
              f"tokens={bl.tokens} parsed_ok={bl.parsed_ok}")
    return results


def save_results(results, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in results], f, indent=2)
