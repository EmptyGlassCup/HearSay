"""
MetricThresholdKS — a classical (deterministic) knowledge source.

It encodes operator domain knowledge as explicit rules: "if evidence claim X is IN,
conclude interpreted claim Y, justified by X." It reasons over evidence already on the
board (seeded by the scenario loader or ingestion adapters); it does NOT ingest external
data. Each rule, when it fires, emits:
  - a ClaimEvent for the interpreted conclusion (a higher-level claim), and
  - a JustifyEvent linking that conclusion to the triggering evidence claim(s).

This gives a traceable justification chain: retracting the underlying evidence ghosts the
interpreted claim automatically via the JTMS.

Rules are data, not code — a list of ThresholdRule. Adding domain knowledge = adding a rule,
not editing logic. This keeps the KS deterministic and inspectable.
"""
from dataclasses import dataclass

from hearsay.control.ks import KnowledgeSource, Activation
from hearsay.protocol.events import ClaimEvent, JustifyEvent


@dataclass(frozen=True)
class ThresholdRule:
    """One piece of operator knowledge.

    trigger_evidence_id : the evidence claim this rule reacts to (must be IN to fire)
    conclusion_id       : id of the interpreted claim this rule emits
    conclusion_text     : human-readable text of the interpreted claim
    justification_id    : id of the justification linking conclusion <- [trigger]
    credibility         : confidence in the interpreted claim
    level               : abstraction level of the interpreted claim (above the evidence)
    """
    trigger_evidence_id: str
    conclusion_id: str
    conclusion_text: str
    justification_id: str
    credibility: float
    level: int = 1


# Domain knowledge for the latency_spike scenario. In a broader system this table would be
# larger, or loaded per-domain; kept inline here for the single demo scenario.
DEFAULT_RULES: tuple[ThresholdRule, ...] = (
    ThresholdRule(
        trigger_evidence_id="e_mem",
        conclusion_id="h_mempressure",
        conclusion_text="Memory is under pressure (usage high)",
        justification_id="j_mempressure",
        credibility=0.7,
    ),
    ThresholdRule(
        trigger_evidence_id="e_wait",
        conclusion_id="h_dbcontention",
        conclusion_text="Database connection pool is saturated (long waits)",
        justification_id="j_dbcontention",
        credibility=0.8,
    ),
)


class MetricThresholdKS(KnowledgeSource):
    name = "metric_threshold"

    def __init__(self, rules: tuple[ThresholdRule, ...] = DEFAULT_RULES):
        self.rules = rules

    def condition(self, board) -> list[Activation]:
        in_set = board.jtms.in_set()
        activations: list[Activation] = []

        for rule in self.rules:
            # Fire only when the trigger evidence is believed...
            if rule.trigger_evidence_id not in in_set:
                continue
            # ...and we have not already produced this interpreted claim.
            if rule.conclusion_id in board.claim_events:
                continue

            activations.append(
                Activation(
                    ks=self,
                    trigger_claims=(rule.trigger_evidence_id,),
                    payload={"rule": rule},
                )
            )

        return activations

    def action(self, activation, board) -> list:
        rule: ThresholdRule = activation.payload["rule"]

        claim = ClaimEvent(
            author=self.name,
            claim_id=rule.conclusion_id,
            text=rule.conclusion_text,
            kind="hypothesis",
            level=rule.level,
            credibility=rule.credibility,
        )
        justify = JustifyEvent(
            author=self.name,
            justification_id=rule.justification_id,
            conclusion=rule.conclusion_id,
            premises=(rule.trigger_evidence_id,),
        )
        return [claim, justify]
