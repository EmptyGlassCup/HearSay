from hearsay.control.ks import KnowledgeSource, Activation
from hearsay.board.board import Board
import asyncio

# Default scoring weights. Tunable per-instance via the `weights` constructor argument.
DEFAULT_WEIGHTS = {
    "credibility": 1.0,   # prefer activations triggered by believable claims
    "utility": 1.0,       # prefer activations closer to a conclusion (higher-level triggers)
    "novelty": 0.5,       # mildly prefer exploring claims not already worked
    "cost": 0.3,          # mildly penalise expensive (LLM) knowledge sources
}

# Used to normalise the "utility" term (trigger level / this cap -> roughly [0, 1]).
# Levels above this are clamped; a soft cap, not a hard limit on the system.
UTILITY_LEVEL_CAP = 5


class Scheduler:
    def __init__(
        self,
        knowledge_sources: list[KnowledgeSource],
        board: Board,
        budget: float,
        goal_threshold: float = 0.0,
        weights: dict | None = None,
    ):
        self.knowledge_sources = knowledge_sources
        self.board = board
        self.budget = budget
        self.goal_threshold = goal_threshold
        self.weights = weights if weights is not None else dict(DEFAULT_WEIGHTS)
        # Novelty memory: how many times each claim id has triggered a chosen activation.
        # Reset per scheduler instance; carried across runs of the same instance.
        self._used_triggers: dict[str, int] = {}

    async def run(self):
        all_events = []
        while self.budget > 0:
            # Gather all activations every knowledge source proposes for the current board.
            activations = []
            for ks in self.knowledge_sources:
                activations.extend(ks.condition(self.board))

            if not activations:
                break

            # Pick the best activation deterministically, run it, apply its events.
            chosen_activation = self._pick(activations)
            chosen_ks = chosen_activation.ks

            events = await chosen_ks.action(chosen_activation, self.board)
            all_events = all_events + events

            for event in events:
                self.board.apply(event)

            # Stop early if a goal claim is now believed above threshold.
            if self._goal_reached():
                return all_events

            self.budget -= 1

        return all_events

    # --- goal detection -----------------------------------------------------

    def _goal_reached(self) -> bool:
        # The goal is a CRITERION, not a claim: reasoning is done when a believed
        # conclusion-kind claim exists above the threshold. A conclusion is an ordinary,
        # justified claim an agent produces — the discovered answer — so it is IN only if
        # its support holds, and it ghosts if that support is retracted, like any claim.
        in_set = self.board.jtms.in_set()
        for claim_id in in_set:
            claim_event = self.board.claim_events[claim_id]
            if claim_event.kind == "conclusion" and claim_event.credibility >= self.goal_threshold:
                return True
        return False

    # --- activation selection ----------------------------------------------

    def _pick(self, activations: list[Activation]) -> Activation:
        """Choose the highest-scoring activation, with a fully deterministic tie-break.

        The sort key is (-score, ks.name, sorted trigger ids): highest score first, then
        stable unique fields so identical boards always yield identical choices (property 9).
        """
        best = min(
            activations,
            key=lambda a: (-self._score(a), a.ks.name, tuple(sorted(a.trigger_claims))),
        )
        # Record the chosen triggers so repeats score lower on novelty next round.
        for trigger in best.trigger_claims:
            self._used_triggers[trigger] = self._used_triggers.get(trigger, 0) + 1
        return best

    def _score(self, activation: Activation) -> float:
        w = self.weights
        return (
            w["credibility"] * self._avg_credibility(activation)
            + w["utility"] * self._expected_utility(activation)
            + w["novelty"] * self._novelty(activation)
            - w["cost"] * activation.ks.cost
        )

    def _avg_credibility(self, activation: Activation) -> float:
        """Mean credibility of the triggering claims, already in [0, 1]."""
        triggers = activation.trigger_claims
        if not triggers:
            return 0.0
        total = 0.0
        for cid in triggers:
            claim_event = self.board.claim_events.get(cid)
            if claim_event is not None:
                total += claim_event.credibility
        return total / len(triggers)

    def _expected_utility(self, activation: Activation) -> float:
        """Proxy for 'closeness to a conclusion': the highest trigger level, normalised.

        Activations built on higher-level claims are further up the abstraction hierarchy,
        so running them tends to move the board toward a conclusion.
        """
        triggers = activation.trigger_claims
        levels = [
            self.board.claim_events[cid].level
            for cid in triggers
            if cid in self.board.claim_events
        ]
        if not levels:
            return 0.0
        return min(max(levels), UTILITY_LEVEL_CAP) / UTILITY_LEVEL_CAP

    def _novelty(self, activation: Activation) -> float:
        """1.0 for never-used triggers, decaying as a trigger is reused.

        Uses the most-worked trigger in the set: an activation rehashing a heavily-used
        claim is less novel than one touching fresh claims.
        """
        triggers = activation.trigger_claims
        if not triggers:
            return 1.0
        max_uses = max(self._used_triggers.get(cid, 0) for cid in triggers)
        return 1.0 / (1.0 + max_uses)
