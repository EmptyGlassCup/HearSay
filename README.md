# HearSay

**A Truth-Maintained Blackboard over IRC**

Submission for [Kiroween 2026](https://kiro.dev) — *Resurrection* category.

---

## What it does

Multi-agent LLM systems accumulate unsupported claims: one agent asserts something, another builds on it, and no one can say what the final answer actually rests on. HearSay resurrects three old ideas to fix that:

| Old idea | Origin | Role here |
|---|---|---|
| Internet Relay Chat | 1988 | Human-readable, observable transport and event log |
| Blackboard architecture | Hearsay-II, 1970s | Shared workspace where independent experts contribute hypotheses |
| Justification-based truth maintenance (JTMS) | Doyle, 1979 | Tracks which beliefs depend on which; retraction cascades automatically |

Every claim must carry a justification. Retract a premise and every claim that depended on it becomes a **ghost** — remembered, shown dimmed, not believed. Restore the premise and ghosts revive automatically. Humans watch and intervene using an ordinary IRC client.

---

## Running it

> Instructions will be added as phases complete. For now, see the phase task lists in `.kiro/specs/`.

---

## Development phases

| Phase | Scope | Owner |
|---|---|---|
| 0 | Repo setup, IRC server verification | Mixed |
| 1 | IRC client + message parser | Human |
| 2 | JTMS | Human |
| 3 | Board, event log, scheduler, toy blackboard | Human |
| 4 | Integration: kernel on IRC with tagged events | Mixed |
| 5 | Domain knowledge sources (incl. LLM expert) | Kiro |
| 6 | Web UI: graph view with IN/OUT/ghost states | Kiro |
| 7 | Evaluation, demo video, submission | Mixed |

---

## Stack

Python 3.12, asyncio, pytest + Hypothesis, FastAPI + WebSocket, Cytoscape.js

---

## Kiro usage

See `.kiro/` for steering docs, specs, and hooks. A write-up of how Kiro was used is included in the final submission.
