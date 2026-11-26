"""
Scenario loader.
Written by KIRO

Reads a scenario JSON file and turns its evidence items into ClaimEvents ready to be
applied to a Board. A scenario is input data (the state of the world before reasoning
begins), not a knowledge source — so this is a plain function, not a KS.

Scenario JSON shape:
    {
      "id": str,
      "title": str,
      "question": str,
      "ground_truth": str,
      "evidence": [
        {"id","text","kind","level","credibility","misleading"}, ...
      ]
    }
"""
import json
from dataclasses import dataclass
from pathlib import Path

from hearsay.protocol.events import ClaimEvent

SCENARIO_AUTHOR = "scenario"


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    question: str
    ground_truth: str
    evidence_events: tuple[ClaimEvent, ...]
    misleading_ids: frozenset[str]


def load_scenario(path: str | Path) -> Scenario:
    """Load a scenario file and build its initial evidence ClaimEvents."""
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))

    events = []
    misleading = set()
    for item in data["evidence"]:
        events.append(
            ClaimEvent(
                author=SCENARIO_AUTHOR,
                claim_id=item["id"],
                text=item["text"],
                kind=item["kind"],
                level=item["level"],
                credibility=item["credibility"],
            )
        )
        if item.get("misleading", False):
            misleading.add(item["id"])

    return Scenario(
        id=data["id"],
        title=data["title"],
        question=data["question"],
        ground_truth=data["ground_truth"],
        evidence_events=tuple(events),
        misleading_ids=frozenset(misleading),
    )


def seed_board(board, scenario: Scenario) -> None:
    """Apply a scenario's evidence events to a board, in order."""
    for event in scenario.evidence_events:
        board.apply(event)
