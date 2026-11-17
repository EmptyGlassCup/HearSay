# Phase 0 — Requirements

## Goal
Have a running IRC server with verified IRCv3 tag support, a confirmed tech stack, and all project scaffolding in place before any implementation begins.

## Requirements

### R0.1 Repository
- Public GitHub repository with MIT license detectable in the About section.
- `/.kiro` directory committed and not in `.gitignore`.
- `README.md` with project description and run instructions stub.

### R0.2 IRC server
- An IRC server is running locally (or on a reachable host) for development.
- The server supports the `message-tags` IRCv3 capability.
- The server relays client-only (`+`-prefixed) tags to other clients in the same channel.
- Tag key naming rules, value size budget, and line budget are documented.
- `msgid` capability is confirmed present or absent.
- Chat history capability is confirmed present or absent.

### R0.3 Stack confirmation
- Python 3.12 is available in the dev environment.
- `pyproject.toml` exists with project metadata and dev dependencies (pytest, hypothesis, asyncio test support).
- A virtual environment can be created and all declared dependencies installed successfully.

### R0.4 Steering docs
- `.kiro/steering/product.md`, `tech.md`, `structure.md`, `protocol.md` are committed and accurate.

### R0.5 Domain shortlist
- At least two candidate domains are evaluated against the selection criteria.
- A provisional domain choice is recorded (can be revised through end of Phase 3).
