# Protocol

## IRC wire format

Each blackboard event is one IRC `PRIVMSG` with IRCv3 client-only message tags (prefix `+`).

### Tag keys

| Tag | Meaning |
|---|---|
| `+bb-kind` | Event type: `claim`, `justify`, `retract`, `challenge`, `activate`, `result` |
| `+bb-id` | Claim or justification ID |
| `+bb-level` | Abstraction level (integer) |
| `+bb-conf` | Credibility score, float in [0,1] |
| `+bb-claim-kind` | Claim kind: `evidence`, `hypothesis`, `conclusion`, `goal` |
| `+bb-conclusion` | For `justify`: the claim ID being justified |
| `+bb-premises` | For `justify`: comma-separated list of premise claim IDs |
| `+bb-ref` | For `retract`: ID of the claim or justification being retracted |

### Example messages

```
@+bb-kind=claim;+bb-id=c42;+bb-claim-kind=hypothesis;+bb-level=2;+bb-conf=0.7 :logexpert!l@h PRIVMSG #hypotheses :Deploy at 03:12 likely caused the latency spike
@+bb-kind=justify;+bb-id=j7;+bb-conclusion=c42;+bb-premises=c17,c19 :logexpert!l@h PRIVMSG #hypotheses :c42 follows from c17 and c19
@+bb-kind=retract;+bb-ref=c17 :metricexpert!m@h PRIVMSG #evidence :Retracting c17: dashboard was misread
```

### Channel mapping

| Channel | Purpose |
|---|---|
| `#evidence` | Level-0 claims: raw observations, measurements |
| `#hypotheses` | Level-1/2 claims: inferences and explanations |
| `#conclusions` | Level-3+ claims: final answers |
| `#control` | Scheduler notices, ACTIVATE and RESULT events |

## Fallback encoding

If the IRC server does not reliably relay client-only tags, append a compact machine-readable suffix to the message text:

```
Deploy at 03:12 likely caused the latency spike |||bb:claim,c42,hypothesis,2,0.7
```

The codec must support both forms and round-trip either. The kernel detects which form is in use at startup.

## Verification checklist (Phase 0) [VERIFY]

- [ ] Chosen server supports the `message-tags` capability
- [ ] Server relays client-only (`+`) tags to other clients
- [ ] Tag key naming rules (allowed characters, length)
- [ ] Tag value size budget (separate from the 512-byte line budget)
- [ ] `msgid` capability available
- [ ] Chat history / `CHATHISTORY` available
- [ ] Confirm Ergo is the server or document the alternative

## Correctness properties

These must each have a Hypothesis property-based test.

### JTMS
1. **Soundness**: every IN claim is an unretracted premise or has a justification whose premises are all IN.
2. **Completeness**: the IN set equals the least fixpoint of the labeling rule, computed by a naive from-scratch oracle.
3. **Incremental = batch**: incremental relabeling gives the same result as full recomputation on the same inputs.
4. **Order independence**: the same set of assertions and retractions yields the same labeling regardless of order.
5. **Revival**: retract then re-assert a premise restores the previous labeling exactly.
6. **No self-support**: cyclic justifications alone never make claims IN.

### Protocol and kernel
7. **Codec round-trip**: `parse(serialize(event)) == event` for all valid events; malformed input never crashes the kernel.
8. **Replay determinism**: folding the same event log always yields identical board state.
9. **Scheduler safety**: never activates a KS whose condition returns empty; identical board states give identical activation choices.
10. **No dangling references**: every justification and retraction in the log refers to a claim that exists at that point.
