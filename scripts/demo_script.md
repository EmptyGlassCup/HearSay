# Demo script - database exfiltration: overseas attacker vs compromised insider

A 2.1 GB exfiltration from db-prod-01. The evidence has been partly analysed into two
competing lines of reasoning. The external-attacker line rests (transitively) on a single
GeoIP lookup. When that lookup turns out to be stale, the entire external theory collapses in
a cascade, and - supplying the one missing internal link - the system concludes the real
cause: a compromised internal account. Both conclusions are drawn live by the LLM; the board
structure gates which one is reachable at each stage. Under 3 minutes.

## One-time setup (before recording)
1. Start Ergo.
2. `$env:HEARSAY_LLM_API_KEY = "sk-..."`   (thinking disabled by default so the agent shows
   its conclusion as a node).
3. `python scripts/run_kernel.py`
4. Open http://127.0.0.1:8000
5. IRC client -> 127.0.0.1:6667, join #evidence, #hypotheses, #control.
6. REHEARSE. The structure guarantees the agent can only reach EXTERNAL at Beat 4 and only
   INSIDER at Beat 7. The remaining risk is the agent HEDGING (no conclusion) - if it does,
   tell Kiro and we nudge the prompt.

## The recorded run

### Beat 1 - the incident, partly analysed
```
powershell -ExecutionPolicy Bypass -File scripts/inject_geoip.ps1
```
Seeds the evidence and both lines of intermediate reasoning (but neither conclusion, and two
linking steps are deliberately left out). Narrate: "A 2.1 GB exfiltration. The team has
already worked the evidence into two partial theories - an overseas attacker, and a
compromised internal account."

### Beat 2 - set the goal
```
!goal Who performed the 2.1 GB outbound transfer from db-prod-01, and from where did they connect?
```

### Beat 3 - you supply the external theory's final link
```
!claim hypothesis 0.84 premises=h_outsidenet,h_scripted a party outside the organisation operated session 88213
```
Narrate: "The source IP geolocates overseas and the session looks scripted - so a party
outside the org drove it. That completes the external picture."
(This is the ONLY conclusion now reachable - the internal theory is still missing a link.)

### Beat 4 - first analysis: EXTERNAL
Press Run analysis. The agent concludes an external attacker used mchen's credentials from
outside the network. Point at the external conclusion and the tower beneath it.

### Beat 5 - the twist (retract the stale GeoIP)
```
!retract e_geo
```
Narrate: "But that GeoIP snapshot is from 2024. Change ticket CHG-4471 shows that prefix was
reassigned to OUR egress pool in October 2026. The 'overseas' reading is stale - retract it."
Watch the whole external tower - overseas, new-location, outside-network, your outside-party
hypothesis, and the external conclusion - ghost in a cascade.

### Beat 6 - you supply the internal theory's missing link
```
!claim hypothesis 0.5 premises=h_wscomp,h_insidenet,h_scripted account mchen was taken over via WS-114 and used from inside the network
```
Narrate: "With the source now inside our egress range, and that unreviewed EDR alert on her
workstation - this looks like her account was hijacked via WS-114 and used from inside."

### Beat 7 - re-analysis: INSIDER
Press Run analysis. The agent concludes mchen's account was compromised through WS-114 and
used from inside the network to exfiltrate the data. Point at the new conclusion standing on
the surviving evidence.
Narrate: "One stale fact, retracted, collapsed the entire external theory - and the system
reassembled the real one. Every step traces back to evidence, and nothing had to be
re-checked by hand."

## Reset between takes
Restart run_kernel.py (board state is in memory).
