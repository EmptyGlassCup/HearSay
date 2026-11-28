"""
LLMHypothesisKS — generates explanatory hypotheses from the believed claims on the board.

The hard part is turning free LLM text into structured events the JTMS can use. The KS:
  1. renders the current IN claims (evidence AND prior hypotheses) into a prompt,
  2. asks the LLM for a NEW hypothesis (not one already on the board) as JSON, OR a
     {"done": true} signal if nothing new is warranted,
  3. validates the JSON (shape, types, and — critically — that every premise_id is a real
     claim on the board), rejecting anything malformed or dangling,
  4. emits a ClaimEvent + JustifyEvent only if validation passes.

Multiple agents: each instance takes a distinct `name` and `id_prefix`, so two agents
(e.g. one on DeepSeek, one on a local model) never collide on claim ids and are
distinguishable as authors. They see each other's hypotheses on the board and build on or
differ from them — that is the multi-agent behaviour.

Trust boundary: the LLM output is untrusted. Any failure (bad JSON, missing fields, bad
types, premises that don't exist) results in NO events, never a crash.

Async: `action` is a coroutine. The blocking HTTP call to the model is offloaded to a worker
thread via asyncio.to_thread, so the event loop stays free to serve the web UI and incoming
IRC while a model is thinking. Only the pure network call runs off-thread; all board reads
and event construction happen on the event-loop thread, so there is no concurrent board
access.
"""
import asyncio
import json

from hearsay.control.ks import KnowledgeSource, Activation
from hearsay.protocol.events import ClaimEvent, JustifyEvent
from hearsay.experts.llm_client import LLMClient, LLMError

PROMPT_TEMPLATE = """You are an incident root-cause analyst named "{agent_name}".

YOUR GOAL: answer this question with a well-supported ROOT CAUSE.
QUESTION: {question}

Currently believed FACTS (evidence):
{evidence_block}

Hypotheses ALREADY proposed (you MAY build on these, but do NOT repeat them):
{hypotheses_block}

Reason toward the goal. Two kinds of contribution are allowed:
  - a "hypothesis": a partial explanation or intermediate step. You may build a hypothesis
    ON TOP of existing hypotheses (cite their ids as premises), not just on raw evidence.
    Prefer combining multiple facts/hypotheses over restating a single obvious one.
  - a "conclusion": a confident answer to the QUESTION, naming the root cause. Only give a
    conclusion when the supporting hypotheses/evidence make you confident.

CITE PREMISES MINIMALLY. premise_ids must contain ONLY the facts/hypotheses that DIRECTLY
support this specific claim — usually 2 to 4 ids. Do NOT list every known fact. A fact that
is merely true, or related to the incident in general, is NOT a premise unless this claim
depends on it directly. Over-citing is an error: if you retracted any cited premise, the
claim should no longer hold — if it would still hold, that premise does not belong.

Respond with ONLY a JSON object, no prose. Either:
  {{"claim_kind": "hypothesis" | "conclusion",
    "conclusion_text": "<your statement>",
    "premise_ids": ["<id>", ...],
    "credibility": <0..1>}}
or, if nothing new is warranted:
  {{"done": true}}

premise_ids MUST be ids drawn from the lists above. Do not invent ids. A conclusion should
build on the hypotheses that establish it, not jump straight from raw evidence.
"""


class LLMHypothesisKS(KnowledgeSource):
    cost = 5.0   # an LLM call is far more expensive than a classical rule check

    def __init__(
        self,
        llm: LLMClient,
        name: str = "llm_hypothesis",
        id_prefix: str = "llm",
        question: str = "What is the root cause of the incident?",
        max_hypotheses: int = 5,
    ):
        self.llm = llm
        self.name = name
        self.id_prefix = id_prefix
        self.question = question
        self.max_hypotheses = max_hypotheses
        self._produced = 0            # contributions since the board last changed (cap counter)
        self._emitted = 0             # lifetime contributions; drives unique ids, never resets
        self._done = False            # set when the LLM signals it has nothing new
        self._last_external = None    # external (non-self) IN-set the agent last saw

    def condition(self, board) -> list[Activation]:
        in_set = board.jtms.in_set()
        if not in_set:
            return []

        # "External" view of the board: the believed claims NOT authored by this agent.
        # We re-engage when THIS changes — i.e. evidence was retracted, or another source
        # added/removed a claim — but not merely because we ourselves added a hypothesis.
        # This is what lets the agent rebuild toward the true cause after misleading
        # evidence is retracted, while still going quiet on a stable board.
        external = frozenset(
            cid for cid in in_set
            if board.claim_events[cid].author != self.name
        )
        if external != self._last_external:
            self._done = False
            self._produced = 0
            self._last_external = external

        if self._done or self._produced >= self.max_hypotheses:
            return []
        return [Activation(ks=self, trigger_claims=tuple(sorted(in_set)))]

    async def action(self, activation, board) -> list:
        # Board reads happen here on the event-loop thread (no concurrency hazard).
        in_ids = sorted(board.jtms.in_set())

        evidence_lines = []
        hypothesis_lines = []
        for cid in in_ids:
            ev = board.claim_events[cid]
            line = f"- {cid}: {ev.text}"
            (evidence_lines if ev.kind == "evidence" else hypothesis_lines).append(line)

        prompt = PROMPT_TEMPLATE.format(
            agent_name=self.name,
            question=self.question,
            evidence_block="\n".join(evidence_lines) or "(none)",
            hypotheses_block="\n".join(hypothesis_lines) or "(none yet)",
        )

        try:
            # Offload the blocking HTTP call to a worker thread so the event loop stays
            # free to serve the UI and IRC while the model is thinking.
            raw = await asyncio.to_thread(self.llm.complete, prompt)
        except LLMError:
            return []  # LLM unreachable/failed -> produce nothing this round

        parsed = self._parse(raw)
        if parsed is None:
            return []
        if parsed == "DONE":
            self._done = True   # the agent has declared it has nothing new to add
            return []

        claim_kind, conclusion_text, premise_ids, credibility = parsed

        # Validation: at least one premise, and every premise a real claim on the board.
        if not premise_ids:
            return []
        if any(pid not in board.claim_events for pid in premise_ids):
            return []

        # Light backstop against a model ignoring the "don't repeat" instruction: skip if
        # an identical hypothesis text is already BELIEVED. Only IN claims count — a ghosted
        # (OUT) claim is not "already on the board": re-asserting it with fresh, surviving
        # support is exactly the revival the system exists to allow (e.g. the same conclusion
        # rebuilt after misleading evidence is retracted).
        normalized = conclusion_text.strip().lower()
        in_set = board.jtms.in_set()
        if any(
            board.claim_events[cid].text.strip().lower() == normalized
            for cid in in_set
        ):
            return []

        # Level is DERIVED from premises: one above the highest-level claim it builds on.
        level = max(board.claim_events[pid].level for pid in premise_ids) + 1

        self._produced += 1   # counts against max_hypotheses for the current board
        self._emitted += 1    # lifetime counter -> globally unique ids across re-engagements
        claim_id = f"{self.id_prefix}_h{self._emitted}"
        just_id = f"{self.id_prefix}_j{self._emitted}"

        claim = ClaimEvent(
            author=self.name,
            claim_id=claim_id,
            text=conclusion_text,
            kind=claim_kind,   # "hypothesis" or "conclusion", as the agent chose
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
        """Return a (text, premises, cred) tuple, the string 'DONE', or None on any problem."""
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

        if obj.get("done") is True:
            return "DONE"

        claim_kind = obj.get("claim_kind", "hypothesis")
        text = obj.get("conclusion_text")
        premises = obj.get("premise_ids")
        cred = obj.get("credibility")

        if claim_kind not in ("hypothesis", "conclusion"):
            claim_kind = "hypothesis"   # default/repair a bad kind rather than reject
        if not isinstance(text, str) or not text.strip():
            return None
        if not isinstance(premises, list) or not all(isinstance(p, str) for p in premises):
            return None
        if not isinstance(cred, (int, float)):
            return None
        cred = max(0.0, min(1.0, float(cred)))

        return claim_kind, text.strip(), premises, cred
