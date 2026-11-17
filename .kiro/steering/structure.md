# Structure

## Repository layout

```
.kiro/
  steering/        product.md, tech.md, structure.md, protocol.md
  specs/           phase0/, phase1/, ... (requirements.md, design.md, tasks.md each)
  hooks/

src/hearsay/
  irc/             client.py, parser.py          [HUMAN]
  protocol/        events.py, codec.py           [HUMAN]
  tms/             jtms.py                       [HUMAN]
  board/           board.py, eventlog.py         [HUMAN]
  control/         scheduler.py, ks.py           [HUMAN]
  experts/         (LLM and classical KSs)       [KIRO]
  ui/              server.py, web/               [KIRO]

tests/             property + unit tests
eval/
  scenarios/       seeded tasks with ground truth
  results/         ablation outputs (gitignored)

LICENSE            MIT
README.md
pyproject.toml
```

## Architecture overview

```
 Humans (any IRC client)         Web UI (graph + ghosts)
        |                                  ^
        v                                  | WebSocket
 +----------------+      events      +-----+------------------+
 |  IRC server    | <--------------> |   KERNEL (bot client)  |
 | (single node)  |    tagged msgs   |  - protocol codec      |
 +----------------+                  |  - event log (append)  |
        ^                            |  - board + JTMS        |
        | tagged msgs                |  - scheduler           |
 +------+---------+                  +-----+------------------+
 | Knowledge      |                        |
 | sources (KS):  | <----------------------+ activations
 | LLM + classic  |
 +----------------+
```

## Component responsibilities

**IRC server**: transport, human visibility, message ordering. Single node only.

**Kernel**: single source of truth.
- Parses tagged IRC messages into events
- Appends events to a durable log
- Folds the log into board state
- Runs the JTMS labeling
- Schedules knowledge source activations

**Knowledge sources**: independent experts. They read the board and post events. They never call each other.

**Web UI**: read-mostly view of the hypothesis graph with IN/OUT/ghost states, updated via WebSocket.

## Data model

**Claim**: `id`, `text`, `kind` (evidence | hypothesis | conclusion | goal), `level` (abstraction level), `credibility` ∈ [0,1], `author`, `created_seq`

**Justification**: `id`, `conclusion` (claim id), `premises` (list of claim ids), `author`. Positive-only (no negated premises).

**Labels**: A claim is IN if it is an unretracted premise, or has at least one justification whose premises are all IN. Otherwise OUT (ghost).

**Events** (append-only): `CLAIM`, `JUSTIFY`, `RETRACT`, `CHALLENGE`, `ACTIVATE`, `RESULT`
