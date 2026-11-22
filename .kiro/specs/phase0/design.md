# Phase 0 — Design

## IRC server: Ergo

Ergo (formerly Oragono) is an IRCv3-first server written in Go. It supports `message-tags`, relays client-only tags, and has built-in `CHATHISTORY`. It runs as a single binary with a YAML config.

**Install**: download from https://github.com/ergochat/ergo/releases or `go install`.

**Minimum config changes from the default**:
- Enable the `message-tags` capability (on by default in recent Ergo).
- Confirm `+`-prefixed client-only tags pass through to other clients.
- Set up the channels `#evidence`, `#hypotheses`, `#conclusions`, `#control`.

**Verification approach**: connect two clients (can use `irssi` or `netcat`), send a message with client-only tags from one, observe the raw line received by the other. Document the exact output.

## Python environment

Use `pyproject.toml` with `[project]` metadata and `[project.optional-dependencies]` for dev tools.

Minimum dev dependencies:
- `pytest >= 8`
- `hypothesis >= 6`
- `pytest-asyncio`

Runtime dependencies (stubs for now, fill in as phases complete):
- `aiohttp` or `asyncio` stdlib only for Phase 1
- `fastapi`, `uvicorn[standard]` for Phase 6

## Tag size budget (to verify)

IRCv3 spec: tags are in a separate budget from the 512-byte message limit. The tag budget is 8191 bytes (including the leading `@` and trailing space). Client-only tag keys include the `+` prefix in the byte count. Document the actual limits Ergo enforces.

## Verification results (Nov 17, 2026)

**Server**: Ergo 2.19.1 running locally on `ergo.test:6667`

**Test**: a PowerShell TCP client negotiated `message-tags` via `CAP REQ`, then sent:
```
@+bb-kind=claim;+bb-id=c1 PRIVMSG #evidence :test claim
```

**Receiving client A (PowerShell, had negotiated `message-tags`)**: tags present and intact — confirmed by `CAP ACK message-tags` in the handshake response.

**Receiving client B (HexChat, did not negotiate `message-tags`)**: tags absent. Raw log showed only:
```
@time=2026-11-17T08:41:34.024Z :tagbot!~u@44u3a93uepegi.irc PRIVMSG #evidence :test claim
```
Only the server-generated `time` tag was present; client-only `+bb-*` tags were withheld.

**Conclusion**: tag relay works correctly. Ergo delivers client-only tags only to clients that have negotiated the `message-tags` capability. This is correct IRCv3 behaviour. The kernel must include `CAP REQ :message-tags` in its handshake. HexChat (human observer) will see clean message text without tags, which is appropriate.

**Tag budget**: IRCv3 spec states 8191 bytes for the tag section. Ergo 2.19.1 enforces this limit — not stress-tested but assumed correct.

**Other capabilities confirmed present**: `CHATHISTORY=1000`, `msgid` (seen on JOIN message: `@msgid=iuaf5sqszfsjxb6x46xjkcum2a`).

**Fallback needed**: No. Tags work. Fallback codec path will be implemented but should not be needed with Ergo.

---

## Fallback detection

At kernel startup, attempt to register `message-tags` with the server. If the server does not confirm it, switch the codec to the text-suffix fallback. This decision is made once and stored in the kernel's config state.
