"""
Tests for the board -> graph snapshot (pure function, no server needed).
"""
from hearsay.board.board import Board
from hearsay.protocol.events import ClaimEvent, JustifyEvent, RetractClaimEvent
from hearsay.ui.snapshot import board_snapshot


def _claim(cid, kind="evidence", level=0, cred=1.0):
    return ClaimEvent(author="t", claim_id=cid, text=f"text {cid}",
                      kind=kind, level=level, credibility=cred)


def test_snapshot_nodes_and_states():
    board = Board()
    board.apply(_claim("c1"))
    board.apply(_claim("c2"))
    board.apply(_claim("c3", kind="hypothesis", level=1, cred=0.7))
    board.apply(JustifyEvent(author="t", justification_id="j1",
                             conclusion="c3", premises=("c1", "c2")))

    snap = board_snapshot(board)
    by_id = {n["id"]: n for n in snap["nodes"]}

    assert set(by_id) == {"c1", "c2", "c3"}
    assert all(n["state"] == "in" for n in snap["nodes"])
    assert by_id["c3"]["kind"] == "hypothesis"
    assert by_id["c3"]["level"] == 1
    assert by_id["c3"]["author"] == "t"

    # c3 carries its justification; c1 (raw premise) carries none
    assert by_id["c3"]["justifications"] == [
        {"id": "j1", "premises": ["c1", "c2"], "author": "t"}
    ]
    assert by_id["c1"]["justifications"] == []

    # one justification with two premises -> two edges into c3
    into_c3 = [e for e in snap["edges"] if e["target"] == "c3"]
    assert {e["source"] for e in into_c3} == {"c1", "c2"}


def test_snapshot_marks_ghosts_out():
    board = Board()
    board.apply(_claim("c1"))
    board.apply(_claim("c2"))
    board.apply(_claim("c3", kind="hypothesis", level=1, cred=0.7))
    board.apply(JustifyEvent(author="t", justification_id="j1",
                             conclusion="c3", premises=("c1", "c2")))
    board.apply(RetractClaimEvent(author="t", retract_claim_id="c2"))

    snap = board_snapshot(board)
    by_id = {n["id"]: n for n in snap["nodes"]}

    assert by_id["c1"]["state"] == "in"
    assert by_id["c2"]["state"] == "out"    # retracted
    assert by_id["c3"]["state"] == "out"    # ghosted via the cascade
