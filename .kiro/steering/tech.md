# Tech

## Stack
- **Language**: Python 3.12
- **Concurrency**: asyncio throughout
- **Testing**: pytest + Hypothesis (property-based)
- **API / WebSocket**: FastAPI
- **Graph UI**: Cytoscape.js (or D3 — decide in Phase 6)
- **IRC server**: Ergo (IRCv3-focused) — confirm tag support in Phase 0

## Key design principles

### Event sourcing
Board state is always a deterministic fold over an append-only event log. IRC messages are ephemeral; the kernel's log is the record. Replaying the same log must reproduce identical state every time.

### Separation of concerns
- **Credibility** (float in [0,1]) is soft — used only for scheduling and display.
- **Justifications** are hard — they determine what is believed. Never conflate the two.

### Knowledge source interface
Pure-ish functions over a read-only board snapshot:
- `condition(board) -> list[Activation]`
- `action(activation, board) -> list[Event]`
LLM-backed and classical knowledge sources share this exact interface.

### No cross-KS calls
Knowledge sources never call each other. They only read the board and post events.

## Property-based testing (Hypothesis)
All JTMS and kernel properties in `steering/protocol.md` must have Hypothesis tests. Run them on every save of `tms/` and `protocol/` (see hooks).

## Module ownership

| Path | Owner | Rule |
|---|---|---|
| `src/hearsay/irc/` | Human | Kiro explains, reviews, tests, suggests — does not author |
| `src/hearsay/protocol/` | Human | Same |
| `src/hearsay/tms/` | Human | Same |
| `src/hearsay/board/` | Human | Same |
| `src/hearsay/control/` | Human | Same |
| `src/hearsay/experts/` | Kiro | Generated and iterated freely |
| `src/hearsay/ui/` | Kiro | Generated and iterated freely |

## Dependency management
Use a `pyproject.toml` (PEP 517). No `requirements.txt` as the primary source of truth.
