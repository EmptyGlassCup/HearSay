"""
Evaluation harness: three systems on synthetic layered inference problems.

Systems:
  - hearsay   : runs the REAL board + JTMS pipeline; structural retraction, 0 tokens.
  - llm_direct: a single, carefully-prompted LLM call ("trace the consequences, list truths").
  - llm_cot   : same, but instructed to reason step by step through the layers first
                (chain-of-thought) before answering. Tests whether more reasoning closes the
                gap — and at what extra token cost.

Ground truth comes from the INDEPENDENT naive oracle (eval/oracle.py), not the JTMS, so
hearsay matching it is a real, non-circular result. All three systems are scored by the SAME
function against the SAME ground truth.

Each depth is run over several SEEDS and the per-system metrics are averaged, so the reported
numbers are means (with spread), not single noisy samples.
"""
from dataclasses import dataclass, asdict
from statistics import mean, pstdev
import json

from eval.problem_generator import generate_problem, Problem
from hearsay.board.board import Board
from hearsay.protocol.events import ClaimEvent, JustifyEvent, RetractClaimEvent
from hearsay.experts.llm_client import OpenAICompatClient, LLMError


_RULES_EXPLAINER = """A fact is TRUE if it is a base fact that has not been retracted, OR if
at least one of its rules has ALL of its premise facts TRUE. A fact with no surviving support
is FALSE.

Base facts (initially true): {base_facts}

Rules (each line: a derived fact <= the facts it requires; a fact may have multiple rules and
is true if ANY one rule's premises are all true):
{rules_block}

NOW: the base fact "{retract_target}" is retracted (no longer true). Some facts survive via
an alternate rule; others lose all support and become FALSE."""

DIRECT_PROMPT = "You are a careful logic engine.\n\n" + _RULES_EXPLAINER + """

Trace the consequences through ALL layers. Respond with ONLY a JSON object listing every
fact id that is still TRUE:
{{"true_facts": ["<id>", ...]}}
"""

COT_PROMPT = "You are a careful logic engine.\n\n" + _RULES_EXPLAINER + """

Think step by step. Go layer by layer: for each derived fact, check whether it still has a
rule whose premises are all TRUE given the retraction, and write down your reasoning. AFTER
your reasoning, end your reply with ONLY a JSON object on its own, listing every fact id that
is still TRUE:
{{"true_facts": ["<id>", ...]}}
"""


@dataclass
class SystemScore:
    system: str
    depth: int
    seed: int
    unsupported: int
    missing: int
    unsupported_rate: float
    missing_rate: float
    tokens: int
    parsed_ok: bool


def render_rules(problem: Problem) -> str:
    return "\n".join(
        f"  {conclusion} <= {' AND '.join(premises)}"
        for conclusion, premises in problem.rules
    )


def _score_against_truth(system, depth, seed, asserted, problem, tokens, parsed_ok=True):
    """Shared scoring: compare an asserted belief set to ground truth. Identical for every
    system, so the comparison is apples-to-apples."""
    truth = problem.ground_truth_after
    all_ids = set(problem.all_fact_ids)
    asserted = asserted & all_ids
    unsupported = len(asserted - truth)
    missing = len(truth - asserted)
    n = max(len(all_ids), 1)
    return SystemScore(system, depth, seed, unsupported, missing,
                       unsupported / n, missing / n, tokens, parsed_ok)


def score_hearsay(problem: Problem, depth: int, seed: int) -> SystemScore:
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
    return _score_against_truth("hearsay", depth, seed, asserted, problem, tokens=0)


def _score_llm(system, prompt_template, problem, client, depth, seed) -> SystemScore:
    prompt = prompt_template.format(
        base_facts=", ".join(problem.base_facts),
        rules_block=render_rules(problem),
        retract_target=problem.retract_target,
    )
    try:
        text, usage = client.complete_with_usage(prompt)
    except LLMError:
        return SystemScore(system, depth, seed, -1, -1, 1.0, 1.0, 0, parsed_ok=False)

    asserted = _parse_true_facts(text)
    tokens = usage["total_tokens"]
    if asserted is None:
        return SystemScore(system, depth, seed, -1, -1, 1.0, 1.0, tokens, parsed_ok=False)
    return _score_against_truth(system, depth, seed, asserted, problem, tokens, parsed_ok=True)


def score_llm_direct(problem, client, depth, seed):
    return _score_llm("llm_direct", DIRECT_PROMPT, problem, client, depth, seed)


def score_llm_cot(problem, client, depth, seed):
    return _score_llm("llm_cot", COT_PROMPT, problem, client, depth, seed)


def _parse_true_facts(text: str):
    # Grab the LAST {...} block — for CoT output the JSON comes after the reasoning.
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


def run_eval(depths, client: OpenAICompatClient, seeds=(1, 2, 3)) -> dict:
    """Run every system at every depth over several seeds. Returns both the raw per-seed
    scores and per-(system, depth) aggregates (mean error, mean tokens)."""
    raw: list[SystemScore] = []
    for depth in depths:
        for seed in seeds:
            problem = generate_problem(depth=depth, seed=seed)
            raw.append(score_hearsay(problem, depth, seed))
            raw.append(score_llm_direct(problem, client, depth, seed))
            raw.append(score_llm_cot(problem, client, depth, seed))
        _print_depth_summary(depth, raw, seeds)

    return {"raw": [asdict(r) for r in raw], "aggregates": _aggregate(raw)}


def _aggregate(raw):
    aggs = []
    systems = ["hearsay", "llm_direct", "llm_cot"]
    depths = sorted({r.depth for r in raw})
    for system in systems:
        for depth in depths:
            rows = [r for r in raw if r.system == system and r.depth == depth]
            if not rows:
                continue
            # Error/token means are over runs that actually produced a usable answer.
            # Parse failures are a DIFFERENT outcome (no answer given), counted separately —
            # never folded into the error mean (their sentinel -1s would corrupt it).
            ok = [r for r in rows if r.parsed_ok]
            errs = [r.unsupported + r.missing for r in ok]
            toks = [r.tokens for r in ok]
            aggs.append({
                "system": system, "depth": depth, "n_seeds": len(rows),
                "n_scored": len(ok),
                "mean_error": mean(errs) if ok else None,
                "std_error": pstdev(errs) if len(errs) > 1 else 0.0,
                "mean_unsupported": mean(r.unsupported for r in ok) if ok else None,
                "mean_missing": mean(r.missing for r in ok) if ok else None,
                "mean_tokens": mean(toks) if ok else None,
                "parse_failures": sum(1 for r in rows if not r.parsed_ok),
            })
    return aggs


def _print_depth_summary(depth, raw, seeds):
    for system in ["hearsay", "llm_direct", "llm_cot"]:
        rows = [r for r in raw if r.system == system and r.depth == depth]
        ok = [r for r in rows if r.parsed_ok]
        if not rows:
            continue
        fails = len(rows) - len(ok)
        if ok:
            err = mean(r.unsupported + r.missing for r in ok)
            tok = mean(r.tokens for r in ok)
            print(f"depth={depth:3d} {system:>11}: mean_error={err:5.1f}  "
                  f"mean_tokens={tok:7.0f}  parse_fail={fails}")
        else:
            print(f"depth={depth:3d} {system:>11}: all {fails} runs failed to parse")


def save_results(results: dict, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
