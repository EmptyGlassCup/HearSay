# Phase 0 — Tasks

Target: complete by Nov 18, 2026.

## Tasks

### T0.1 Push repo to GitHub
- Create a public GitHub repository named `HearSay` (or chosen name).
- Push the current local commits.
- Set the About description and add the MIT license so it is detectable.

### T0.2 Install and run Ergo
- Download the Ergo binary for your platform.
- Copy the example config and make the minimum changes (see design.md).
- Start the server and confirm it is listening.

### T0.3 Verify tag support
- Connect two IRC clients to the local Ergo instance.
- From client A, send a raw `PRIVMSG` with client-only tags (e.g. `@+bb-kind=test :A!a@h PRIVMSG #evidence :hello`).
- Capture the raw line received by client B.
- Record: were the tags present? exact format? any truncation?
- Document findings in a note appended to `.kiro/specs/phase0/design.md` under a `## Verification results` heading.

### T0.4 Set up Python environment
- Confirm `python3.12 --version` works.
- Write `pyproject.toml` with project metadata and dev dependencies.
- Create a virtual environment and install dependencies.
- Run `pytest --collect-only` to confirm the test runner works (zero tests is fine).

### T0.5 Create package skeleton
- Add `src/hearsay/__init__.py` and one `__init__.py` per sub-package.
- Add a stub `tests/conftest.py`.
- Confirm `python -c "import hearsay"` works from the venv.

### T0.6 Record domain decision
- Evaluate the three candidate domains (incident RCA, legacy-code archaeology, black-box reverse engineering) against: realistic scenarios with ground truth, ability to plant misleading evidence, demo clarity in 3 minutes.
- Write a short decision note in `.kiro/specs/phase0/domain.md`.
- This choice is provisional and can be revised through end of Phase 3.

## Done criteria
- [ ] Repo is public on GitHub with MIT license.
- [ ] Ergo is running locally.
- [ ] Tag relay is confirmed (or fallback strategy is documented).
- [ ] `pytest` runs cleanly in the venv.
- [ ] `import hearsay` works.
- [ ] Domain decision note exists.
