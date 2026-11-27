"""
Independent, naive reference solver for the labeling rule.

Deliberately NOT the JTMS. It recomputes the IN set from scratch each pass, in the most
transparent way possible, so that when HearSay's JTMS pipeline agrees with it, the agreement
is a genuine (non-circular) correctness result rather than a tautology. This is the same
least-fixpoint rule the JTMS implements, written independently.

Used to compute ground truth for the evaluation.
"""


def naive_in_set(all_ids, rules, retracted=frozenset()):
    """all_ids: iterable of fact ids. rules: iterable of (conclusion_id, (premise_ids,)).
    retracted: set of retracted base-fact ids. Returns the frozenset of ids that hold."""
    active_ids = [fid for fid in all_ids if fid not in retracted]
    active_rules = [(c, p) for (c, p) in rules]

    in_set = set()
    while True:
        new_in = set()
        for fid in active_ids:
            supporting = [p for (c, p) in active_rules if c == fid]
            if not supporting:
                new_in.add(fid)                                  # base fact, not retracted
            elif any(all(prem in in_set for prem in premises) for premises in supporting):
                new_in.add(fid)                                  # some rule fully satisfied
        if new_in == in_set:
            break
        in_set = new_in
    return frozenset(in_set)
