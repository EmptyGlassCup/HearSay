"""
Synthetic layered-inference problem generator for the evaluation.

Produces a symbolic problem parameterised by DEPTH: base facts, and derived facts arranged
in layers, each derived from a conjunction of earlier facts. Some derived facts get a second
independent justification (so retracting one premise does NOT kill them — they survive via
the other path). This forces a correct solver to both DROP unsupported facts and KEEP
still-supported ones — testing genuine dependency tracking, not just "retract everything
downstream".

Ground truth is computed by HearSay's own JTMS: build the structure, retract the target,
read in_set(). By construction HearSay matches it; the eval measures how far a baseline LLM
diverges, and at what token cost.

The generator is seeded for reproducibility.
"""
from dataclasses import dataclass
import random

from eval.oracle import naive_in_set


@dataclass(frozen=True)
class Problem:
    base_facts: tuple[str, ...]              # f0, f1, ...
    rules: tuple[tuple[str, tuple[str, ...]], ...]  # (conclusion_id, premise_ids)
    retract_target: str                      # a base fact to retract
    all_fact_ids: tuple[str, ...]            # every fact id (base + derived)
    ground_truth_before: frozenset[str]      # IN set before the retraction
    ground_truth_after: frozenset[str]       # IN set after retracting the target


def generate_problem(depth: int, fanout: int = 4, n_base: int = 6, seed: int = 0) -> Problem:
    """Build a problem of the given dependency depth.

    depth  : number of derived layers above the base facts.
    fanout : how many derived facts per layer (breadth).
    n_base : number of base facts. A wider base means the retraction target is not a single
             chokepoint, so retraction removes a meaningful-but-partial fraction (not ~all),
             which is what forces a solver to truly distinguish survivors from casualties.
    seed   : RNG seed for reproducibility.
    """
    rng = random.Random(seed)

    base_facts = [f"f{i}" for i in range(n_base)]
    all_ids = list(base_facts)
    rules: list[tuple[str, tuple[str, ...]]] = []

    # Build `depth` layers; each derived fact draws 2-3 premises from facts already defined.
    prev_layer = list(base_facts)
    counter = 0
    for layer in range(depth):
        this_layer = []
        for _ in range(fanout):
            cid = f"d{counter}"
            counter += 1
            k = rng.choice([2, 3])
            # Premises: prefer the previous layer (keeps depth meaningful), plus occasional
            # reach-back to earlier facts for shared-premise structure.
            pool = prev_layer + rng.sample(all_ids, min(len(all_ids), 3))
            premises = tuple(sorted(set(rng.sample(pool, min(k, len(pool))))))
            rules.append((cid, premises))
            all_ids.append(cid)
            this_layer.append(cid)
        prev_layer = this_layer

    # Give ~40% of derived facts a SECOND justification from base facts that EXCLUDE the
    # eventual retraction target's typical dependants, so a healthy fraction survives via an
    # alternate path. This makes the retraction remove a partial (not overwhelming) subset,
    # which is the discriminating case for a solver.
    for cid, _premises in list(rules):
        if rng.random() < 0.4 and len(base_facts) >= 2:
            alt = tuple(sorted(rng.sample(base_facts, 2)))
            rules.append((cid, alt))

    # Retraction target: the base fact with the largest transitive downstream support, so the
    # retraction cascades meaningfully.
    retract_target = _most_depended_on(base_facts, rules, all_ids)

    before = _solve(all_ids, rules, retracted=frozenset())
    after = _solve(all_ids, rules, retracted=frozenset({retract_target}))

    return Problem(
        base_facts=tuple(base_facts),
        rules=tuple(rules),
        retract_target=retract_target,
        all_fact_ids=tuple(all_ids),
        ground_truth_before=before,
        ground_truth_after=after,
    )


def _solve(all_ids, rules, retracted) -> frozenset[str]:
    """Ground truth via the INDEPENDENT naive oracle (not the JTMS). This is what makes
    HearSay matching it a real, non-circular result: HearSay runs its own JTMS pipeline,
    and we check it against a differently-implemented reference."""
    return naive_in_set(all_ids, rules, retracted)


def _most_depended_on(base_facts, rules, all_ids) -> str:
    """Pick the base fact whose retraction removes the most facts from the IN set."""
    best, best_loss = base_facts[0], -1
    full = _solve(all_ids, rules, frozenset())
    for fid in base_facts:
        after = _solve(all_ids, rules, frozenset({fid}))
        loss = len(full) - len(after)
        if loss > best_loss:
            best, best_loss = fid, loss
    return best
