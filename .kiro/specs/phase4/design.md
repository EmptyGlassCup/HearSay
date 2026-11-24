# Phase 4 — Integration (the kernel)

Connect the IRC side and the blackboard side. The codec translates IRCMessage <-> Event;
the kernel wires client -> codec -> board -> scheduler -> codec -> client into one system.
Architecture A: KSs are in-process; IRC is the human read/write interface, not KS transport.

## Done
- `protocol/codec.py` — decode (IRCMessage -> Event) and encode (Event -> IRCMessage, needs board).
- Codec round-trip property test (property 7) passing across all five event types.
- Board tracks claim_events, justify_events, challenges.

## Decisions
- `encode` takes a board so `_channel` can look up a referenced claim's level and place
  justify/retract/challenge messages in the same channel as the claim they concern.
- Channel mapping: level 0 -> #evidence, 1-2 -> #hypotheses, 3+ -> #conclusions.
- `author` is not carried on the wire (clients don't send prefixes). Decoded events take
  author from the IRC prefix nick, or 'unknown'. So author does not survive a round-trip.
- Retraction is permanent (see protocol.md property 5). Wire uses +bb-kind=retract-claim /
  retract-justify, both carrying +bb-ref.

## Deferred / TODO

### [TODO] Codec does not implement IRCv3 tag escaping
Tag values are written raw. If a claim id contains ; = or a space, or text contains \r\n,
the wire format corrupts. Safe in practice because KSs generate ids like c1/j1 and
controlled text. A human typing arbitrary text in HexChat could in theory break round-trip.
Fix: implement IRCv3 escaping (; -> \: , space -> \s , \r \n, \\) in the codec and parser
tag handling. Low priority unless a demo input hits it.

### [TODO] ActivateEvent / ResultEvent still stubbed
Needed to narrate scheduler activity to #control. Define fields, add codec cases, have the
scheduler emit them. Transparency feature, not blocking the core loop.

### [TODO] Kernel not yet written
Still need the top-level object that: constructs the IRC client with an on_message handler
that decodes -> board.apply; runs the scheduler; encodes produced events -> client.send.
This is the actual "integration" deliverable of Phase 4.
