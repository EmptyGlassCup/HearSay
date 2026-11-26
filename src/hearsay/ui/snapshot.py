"""
Board -> graph snapshot.

A pure function that turns the current board state into a JSON-serialisable dict the web UI
can render. Nodes are claims (tagged IN/OUT/challenged); edges connect each justification's
premises to its conclusion. Kept separate from the server so it can be unit-tested without
any WebSocket machinery.

Shape:
    {
      "nodes": [
        {"id","text","kind","level","credibility","state","challenged"}, ...
      ],
      "edges": [
        {"id","source","target","justification"}, ...
      ]
    }
state is "in" or "out" (out = ghost). An edge goes premise -> conclusion.
"""


def board_snapshot(board) -> dict:
    in_set = board.jtms.in_set()

    nodes = []
    for claim_id, ev in board.claim_events.items():
        nodes.append({
            "id": claim_id,
            "text": ev.text,
            "kind": ev.kind,
            "level": ev.level,
            "credibility": ev.credibility,
            "state": "in" if claim_id in in_set else "out",
            "challenged": claim_id in board.challenges,
        })

    edges = []
    for just_id, ev in board.justify_events.items():
        # Only draw edges for justifications whose claims still exist as nodes.
        if ev.conclusion not in board.claim_events:
            continue
        for premise in ev.premises:
            if premise not in board.claim_events:
                continue
            edges.append({
                "id": f"{just_id}:{premise}->{ev.conclusion}",
                "source": premise,
                "target": ev.conclusion,
                "justification": just_id,
            })

    return {"nodes": nodes, "edges": edges}
