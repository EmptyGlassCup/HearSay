"""
Scenario loader.
Written by KIRO

Reads a scenario JSON file and turns its evidence items into ClaimEvents ready to be
applied to a Board. A scenario is input data (the state of the world before reasoning
begins), not a knowledge source — so this is a plain function, not a KS.

Scenario JSON shape:
    {
      "id": str, "title": str, "question": str, "ground_truth": str,
      "evidence": [ {"id","text","kind","level","credibility","misleading"}, ... ],
      "claims": [            # optional: pre-built derived claims (hypotheses/conclusions)
        {"id","text","kind","level","credibility"}, ...
      ],
      "justifications": [    # optional: links claims to their premises
        {"id","conclusion","premises":[id,...]}, ...
      ],
      "twist": {             # optional: documents the intended retraction and its cascade
        "retract", "reason", "expected_ghosts", "expected_survivors",
        "final_answer_after_retraction"
      }
    }

Pre-built claims + justifications let a scenario stage entire lines of reasoning that already
exist on the board, so a retraction visibly cascades through them. Levels are taken from the
JSON as given. The optional `twist` block is metadata (not applied automatically) describing
the demo's intended retraction and the expected ghost/survivor sets.
"""
import json
from dataclasses import dataclass
from pathlib import Path

from hearsay.protocol.events import ClaimEvent, JustifyEvent

SCENARIO_AUTHOR = "scenario"


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    question: str
    ground_truth: str
    evidence_events: tuple[ClaimEvent, ...]
    misleading_ids: frozenset[str]
    claim_events: tuple = ()        # pre-built derived ClaimEvents (hypotheses/conclusions)
    justify_events: tuple = ()      # JustifyEvents linking them to premises
    twist: dict | None = None       # metadata: intended retraction + expected cascade


def load_scenario(path: str | Path) -> Scenario:
    """Load a scenario: evidence, any pre-built claims + justifications, and twist metadata."""
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))

    evidence_events = []
    misleading = set()
    for item in data["evidence"]:
        evidence_events.append(
            ClaimEvent(author=SCENARIO_AUTHOR, claim_id=item["id"], text=item["text"],
                       kind=item["kind"], level=item["level"], credibility=item["credibility"])
        )
        if item.get("misleading", False):
            misleading.add(item["id"])

    claim_events = [
        ClaimEvent(author=SCENARIO_AUTHOR, claim_id=c["id"], text=c["text"],
                   kind=c["kind"], level=c["level"], credibility=c["credibility"])
        for c in data.get("claims", [])
    ]
    justify_events = [
        JustifyEvent(author=SCENARIO_AUTHOR, justification_id=j["id"],
                     conclusion=j["conclusion"], premises=tuple(j["premises"]))
        for j in data.get("justifications", [])
    ]

    return Scenario(
        id=data["id"],
        title=data["title"],
        question=data["question"],
        ground_truth=data["ground_truth"],
        evidence_events=tuple(evidence_events),
        misleading_ids=frozenset(misleading),
        claim_events=tuple(claim_events),
        justify_events=tuple(justify_events),
        twist=data.get("twist"),
    )


def seed_board(board, scenario: Scenario) -> None:
    """Apply evidence, then pre-built claims, then their justifications — in dependency-safe
    order (all claims exist before any justification references them)."""
    for event in scenario.evidence_events:
        board.apply(event)
    for event in scenario.claim_events:
        board.apply(event)
    for event in scenario.justify_events:
        board.apply(event)
