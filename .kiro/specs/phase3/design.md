# Phase 3 — Design notes and decisions

Phase 3 builds the blackboard: event log, board fold, knowledge-source interface,
and scheduler. In-process only — no IRC, no LLMs.

## Decisions made

### Events are mutable dataclasses, not frozen
Chosen for simplicity over language-enforced immutability. The one mutation that would
corrupt the log (re-stamping `sequence`) is guarded by an assert in `EventLog.append`.
Discipline: only `EventLog.append` ever sets `sequence`; nothing else mutates an event.

### Sequence numbers are assigned by the event log, not the creator
A KS/human creates an event with `sequence=None`; `EventLog.append` stamps it with the
next index. Single source of ordering.

### Retraction split into two event types
`RetractClaimEvent` and `RetractJustifyEvent` instead of one `retract` with a bare ref.
The event declares its target kind so the board never infers it. See protocol.md note.

### Board is the sole writer to its own state
KSs only read the board and return events. `action(activation, board) -> list[Event]`
returns events; it never calls `board.apply`. The scheduler applies the returned events.
Every board mutation flows through `board.apply`, which also appends to the log.

### Activation scoring carries determinism, not KS list order
The KS list is a plain list (insertion order). Determinism comes from sorting activations
by a total, stable key `(score, ks_name, trigger_claims)` before picking. Two activations
can never truly tie, so the choice is reproducible regardless of gathering order.

## Deferred / TODO (revisit later)

### [TODO] Budget is a flat per-activation count
First build decrements the budget by 1 per activation run. This ignores that different
activations cost different amounts (an LLM call vs a cheap pattern match). Later: give each
activation/KS a `cost` and decrement by that instead. Tracked here so we don't forget.

### [TODO] Scoring is credibility-only
First build scores an activation by the credibility of its trigger claims. The full design
(steering/tech.md, section 6.2) also weighs novelty, expected utility, and cost. Add those
once the loop runs end to end on the toy problem.

### [TODO] ActivateEvent / ResultEvent not yet defined
The two scheduler-bookkeeping events in protocol/events.py are stubbed with `pass`.
Define their fields once the scheduler logs its activity to #control (Phase 4).

### [TODO] Board fold has no isolated tests
`board.apply` is only exercised indirectly via test_scheduler. Two tests still owed:
  1. Replay determinism (property 8): folding the same event list into two fresh boards
     yields identical in_set() and identical claim dicts.
  2. Per-event-type fold: ClaimEvent adds a claim; RetractClaimEvent ghosts dependents;
     ChallengeEvent records to `challenges` without changing the IN set.

### [TODO] Scheduler _pick is a placeholder
Returns activations[0]. No scoring, no deterministic tie-break yet. Property 9
(scheduler safety / identical boards -> identical choices) is untested.
