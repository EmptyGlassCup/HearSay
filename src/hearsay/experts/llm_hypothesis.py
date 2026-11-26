"""
LLMHypothesisKS — generates explanatory hypotheses from the believed claims on the board.

The hard part is turning free LLM text into structured events the JTMS can use. The KS:
  1. renders the current IN claims (id + text) into a prompt,
  2. asks the LLM for a hypothesis as JSON: {conclusion_text, premise_ids, credibility},
  3. validates the JSON (shape, types, and — critically — that every premise_id is a real
     claim on the board), rejecting anything malformed or dangling,
  4. emits a ClaimEvent + JustifyEvent only if validation passes.

Trust boundary: the LLM output is untrusted. Any failure (bad JSON, missing fields, bad
types, premises that don't exist) results in NO events, never a crash. This mirrors the
codec's decode discipline.
"""
import json

from hearsay.control.ks import KnowledgeSource, Activation
from hearsay.protocol.events import ClaimEvent, JustifyEvent
from hearsay.experts.llm_client import LLMClient, LLMError

PROMPT_TEMPLATE = """You are an incident root-cause analyst. Below are the currently
believed facts and hypotheses, each with an id and description.

{claims_block}

Propose ONE new hypothesis that explains the incident, building only on the claims above.
Respond with ONLY a JSON object, no prose, in exactly this shape:
{{"conclusion_text": "<a short hypothesis>", "premise_ids": ["<id>", ...], "credibility": <0..1>}}

The premise_ids MUST be ids drawn from the list above. Do not invent ids.
"""


class LLMHypothesisKS(KnowledgeSource):
    name = "llm_hypothesis"

    def __init__(self, llm: LLMClient, max_hypotheses: int = 3):
        self.llm = llm
        self.max_hypotheses = max_hypotheses
        self._produced = 0  # how many hypotheses this KS has emitted (budget guard)

    def condition(self, board) -> list[Activation]:
        # Fire while there are believed claims to reason over and we have not hit our cap.
        in_set = board.jtms.in_set()
        if not in_set:
            return []
        if self._produced >= self.max_hypotheses:
            return []
        return [Activation(ks=self, trigger_claims=tuple(sorted(in_set)))]

    def action(self, activation, board) -> list:
        in_ids = sorted(board.jtms.in_set())
        claims_block = "\n".join(
            f"- {cid}: {board.claim_events[cid].text}" for cid in in_ids
        )
        prompt = PROMPT_TEMPLATE.format(claims_block=claims_block)

        try:
            raw = self.llm.complete(prompt)
        except LLMError:
            return []  # LLM unreachable/failed -> produce nothing

        parsed = self._parse(raw)
        if parsed is None:
            return []

        conclusion_text, premise_ids, credibility = parsed

        # Validation: every premise must be a real claim currently on the board.
        if not premise_ids:
            return []
        if any(pid not in board.claim_events for pid in premise_ids):
            return []

        # Level is DERIVED from the premises, not chosen by the LLM: a hypothesis sits one
        # abstraction level above the highest-level claim it is built on. This keeps level
        # semantically consistent with the justification structure.
        level = max(board.claim_events[pid].level for pid in premise_ids) + 1

        self._produced += 1
        claim_id = f"llm_h{self._produced}"
        just_id = f"llm_j{self._produced}"

        claim = ClaimEvent(
            author=self.name,
            claim_id=claim_id,
            text=conclusion_text,
            kind="hypothesis",
            level=level,
            credibility=credibility,
        )
        justify = JustifyEvent(
            author=self.name,
            justification_id=just_id,
            conclusion=claim_id,
            premises=tuple(premise_ids),
        )
        return [claim, justify]

    def _parse(self, raw: str):
        """Extract and validate the JSON hypothesis. Returns a tuple or None on any problem."""
        # The model may wrap JSON in prose or code fences; grab the first {...} block.
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end < start:
            return None
        try:
            obj = json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return None

        if not isinstance(obj, dict):
            return None

        text = obj.get("conclusion_text")
        premises = obj.get("premise_ids")
        cred = obj.get("credibility")

        if not isinstance(text, str) or not text.strip():
            return None
        if not isinstance(premises, list) or not all(isinstance(p, str) for p in premises):
            return None
        if not isinstance(cred, (int, float)):
            return None
        cred = max(0.0, min(1.0, float(cred)))  # clamp into [0, 1]

        return text.strip(), premises, cred
