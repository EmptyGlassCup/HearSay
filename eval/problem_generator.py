"""
Synthetic layered-inference problem generator for the evaluation.

Produces a symbolic problem parameterised by DEPTH: base facts, and derived facts arranged
in layers, each derived from a conjunction of earlier facts. Some derived facts get a second
independent justification (so retracting one premise does NOT kill them — they survive via
the other path). This forces a correct solver to both DROP unsupported facts and KEEP
still-supported ones — testing genuine dependency tracking, not just "retract everything
downstream".

Ground truth is computed by an INDEPENDENT naive oracle (eval/oracle.py), NOT the JTMS, so
HearSay's pipeline matching it is a real (non-circular) result. The eval measures how far an
LLM diverges, and at what token cost.

Justifications per claim are skewed low (most claims have one line of support; corroboration
is common but not universal), with a ceiling that scales with graph size — see the alternate-
justification pass below for the pre-registered parameters.

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

    # Alternate justifications. Each derived fact already has ONE rule (its layered one); we
    # add EXTRA independent justifications so some facts survive a retraction via another path.
    #
    # Realism: most real claims have a single line of support; corroboration (2-3 independent
    # lines) is common but not universal; many lines is rare. So the number of extras is
    # heavily skewed low. As the graph grows there are more opportunities to re-derive a
    # claim, so the *ceiling* (how many a rare claim may reach) scales with size — the tail
    # lengthens, it does not fatten.
    #
    # FIXED, pre-registered parameters (committed before running, to avoid tuning-to-win):
    #   extras distribution: P(0)=0.45, P(1)=0.30, P(2)=0.15, P(3+)=0.10 (tail to ceiling)
    #   ceiling: min(2 + n_facts // 15, 7)
    n_facts_now = len(all_ids)
    ceiling = min(2 + n_facts_now // 15, 7)
    earlier_pool = list(all_ids)  # alternates draw from existing facts (no forward refs)

    for cid, _premises in list(rules):
        extras = _draw_extras(rng, ceiling)
        for _ in range(extras):
            # premises for an alternate rule: 2-3 earlier facts, excluding the conclusion
            # itself (no trivial self-support).
            candidates = [f for f in earlier_pool if f != cid]
            if len(candidates) < 2:
                break
            k = rng.choice([2, 3])
            alt = tuple(sorted(rng.sample(candidates, min(k, len(candidates)))))
            rules.append((cid, alt))

    # Retraction target: the base fact whose retraction removes a fraction of facts CLOSEST
    # to a target (~50%). A partial cascade (not a near-total wipeout) is the discriminating
    # case — a solver must correctly split the graph into a large survivor set AND a large
    # casualty set, rather than scoring well by guessing "almost everything died".
    retract_target = _balanced_target(base_facts, rules, all_ids, target_frac=0.5)

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


def _draw_extras(rng, ceiling) -> int:
    """Number of EXTRA justifications for one fact. Skewed low; the >=3 tail spreads over the
    size-dependent ceiling. P(0)=.45 P(1)=.30 P(2)=.15 P(3+)=.10."""
    r = rng.random()
    if r < 0.45:
        return 0
    if r < 0.75:
        return 1
    if r < 0.90:
        return 2
    # remaining 10%: 3..ceiling inclusive (if ceiling < 3, clamp to ceiling)
    if ceiling < 3:
        return ceiling
    return rng.randint(3, ceiling)


def _solve(all_ids, rules, retracted) -> frozenset[str]:
    """Ground truth via the INDEPENDENT naive oracle (not the JTMS). This is what makes
    HearSay matching it a real, non-circular result: HearSay runs its own JTMS pipeline,
    and we check it against a differently-implemented reference."""
    return naive_in_set(all_ids, rules, retracted)


def _balanced_target(base_facts, rules, all_ids, target_frac=0.5) -> str:
    """Pick the base fact whose retraction removes a fraction of facts closest to target_frac,
    so the cascade is substantial but partial (both survivor and casualty sets are large)."""
    full = _solve(all_ids, rules, frozenset())
    n = max(len(full), 1)
    best, best_gap = base_facts[0], float("inf")
    for fid in base_facts:
        after = _solve(all_ids, rules, frozenset({fid}))
        frac = (len(full) - len(after)) / n
        gap = abs(frac - target_frac)
        if gap < best_gap:
            best, best_gap = fid, gap
    return best
