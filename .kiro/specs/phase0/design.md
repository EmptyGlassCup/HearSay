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

## Fallback detection

At kernel startup, attempt to register `message-tags` with the server. If the server does not confirm it, switch the codec to the text-suffix fallback. This decision is made once and stored in the kernel's config state.
