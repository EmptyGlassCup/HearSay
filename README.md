# HearSay

**A Truth-Maintained Blackboard over IRC**

Submission for [Kiroween 2026](https://kiro.dev) — *Resurrection* category.

---

## What it does

Multi-agent LLM systems accumulate unsupported claims: one agent asserts something, another builds on it, and no one can say what the final answer actually rests on. HearSay resurrects three old ideas to fix that:

| Old idea | Origin | Role here |
|---|---|---|
| Internet Relay Chat | 1988 | Human-readable, observable transport and event log |
| Blackboard architecture | Hearsay-II, 1970s | Shared workspace where independent experts contribute hypotheses |
| Justification-based truth maintenance (JTMS) | Doyle, 1979 | Tracks which beliefs depend on which; retraction cascades automatically |

Every claim carries a justification. Retract a premise and every claim that depended on it becomes a **ghost** — remembered, shown dimmed, not believed. Restore support (via new evidence) and the ghost revives automatically. Humans watch and intervene using an ordinary IRC client; a live web graph shows the reasoning in real time.

---

## How it works (the short version)

```
 Humans (any IRC client)          Web graph (localhost:8000)
        |                                   ^
        v                                   | live updates
 +----------------+     tagged msgs   +-----+------------------+
 |  IRC server    | <---------------> |   KERNEL               |
 |  (Ergo)        |                   |  codec + event log     |
 +----------------+                   |  board + JTMS          |
        ^                             |  scheduler             |
        | reads board, posts events   +-----+------------------+
 +------+---------+                         |
 | Knowledge      | <-----------------------+
 | sources (LLM + classic experts)         |
 +------------------------------------------+
```

- Evidence and corrections arrive over IRC (from humans or data adapters).
- Knowledge sources (classical rules and LLM agents) read the board and propose claims, each with a justification.
- The JTMS maintains which claims are believed (IN) vs ghosted (OUT). Retracting one fact cascades automatically to everything that depended on it.
- A human presses **Run analysis** in the web UI to let the agents reason over the current board.

---

## Requirements

- **Python 3.12+**
- **[Ergo](https://github.com/ergochat/ergo)** — an IRCv3 server (any server that relays client-only message tags works; Ergo is tested).
- An **IRC client** for the human view (e.g. [HexChat](https://hexchat.github.io/)). Optional but recommended.
- For the LLM agents: an **OpenAI-compatible LLM endpoint** — either a hosted API (DeepSeek, OpenAI, …) or a local server (e.g. [LM Studio](https://lmstudio.ai/)). The system also runs with only classical experts and no LLM.

---

## Install

```bash
git clone <your-repo-url> HearSay
cd HearSay
python -m venv .venv
# Windows:  .venv\Scripts\Activate.ps1
# macOS/Linux:  source .venv/bin/activate
pip install -e ".[dev,ui]"
```

---

## Configure the LLM (one place)

All LLM settings live in `src/hearsay/experts/llm_config.py` and are overridable by environment variables — you never edit code to switch providers.

| Variable | Default | Meaning |
|---|---|---|
| `HEARSAY_LLM_BASE_URL` | `https://api.deepseek.com/v1` | OpenAI-compatible endpoint |
| `HEARSAY_LLM_MODEL` | `deepseek-flash` | model id |
| `HEARSAY_LLM_API_KEY` | — | API key (falls back to `DEEPSEEK_API_KEY`) |
| `HEARSAY_LLM_MAX_TOKENS` | server default | output cap |
| `HEARSAY_LLM_TIMEOUT` | `600` | request timeout (seconds) |

**Hosted API (PowerShell):**
```powershell
$env:HEARSAY_LLM_API_KEY = "sk-..."
```

**Local model (LM Studio), no key:**
```powershell
$env:HEARSAY_LLM_BASE_URL = "http://localhost:1234/v1"
$env:HEARSAY_LLM_MODEL    = "<your-local-model-id>"
```

---

## Run it

**1. Start the IRC server** (from your Ergo install):
```bash
ergo run        # listens on 127.0.0.1:6667
```

**2. Start the kernel + web UI:**
```powershell
python scripts/run_kernel.py
```
This connects to IRC, starts the reasoning engine, and serves the graph.

**3. Open the web graph:** <http://127.0.0.1:8000>

**4. (Optional) Open an IRC client** and join the channels to watch/participate:
`#evidence`, `#hypotheses`, `#conclusions`, `#control` on `127.0.0.1:6667`.

---

## Interacting: the command syntax

Type these in any channel from your IRC client. The kernel assigns ids and echoes them back in `#control`.

| Command | Effect |
|---|---|
| `!goal <question>` | Set the question the agents reason toward. |
| `!claim evidence <0-1> <text>` | Assert raw evidence. e.g. `!claim evidence 0.9 db wait time 3800ms` |
| `!claim hypothesis\|conclusion <0-1> premises=<id,id> <text>` | Assert a derived claim, grounded on existing claims. e.g. `!claim hypothesis 0.6 premises=e1,e2 the deploy caused it` |
| `!retract <id>` | Retract a claim; everything depending on it ghosts out automatically. |
| `!challenge <id>` | Flag a claim for scrutiny (no change to belief). |
| `!help` | Print the syntax to `#control`. |

Evidence is a raw premise (no `premises=`). A hypothesis or conclusion **must** be grounded
on existing claim ids via `premises=`, so it can never dangle. The kernel assigns each new
claim an id and echoes it back in `#control`.

Then press **Run analysis** in the web UI to let the agents reason over the board.

---

## Try it on a seeded scenario

A ready-made security-incident scenario is included (`eval/scenarios/exfil_stale_geoip.json`),
with a scripted walkthrough in `scripts/demo_script.md`. With an LLM configured:
```powershell
python scripts/run_multiagent.py
# then, in another terminal, inject the scenario evidence:
powershell -ExecutionPolicy Bypass -File scripts/inject_geoip.ps1
```
Then follow `scripts/demo_script.md`: set the goal, supply the missing reasoning step, run
analysis (the agent concludes an external attacker), retract the stale GeoIP fact and watch
the external theory cascade to ghosts, then run again to reach the real answer — a
compromised internal account.

---

## Run the tests

```bash
pytest
```

Includes property-based tests (Hypothesis) for the JTMS correctness properties and the codec round-trip.

---

## Evaluation

`scripts/run_eval.py` compares HearSay against single-LLM baselines on synthetic
layered-reasoning problems, parameterised by dependency depth. After a fact is retracted,
each system is scored against ground truth computed by an **independent** solver
(`eval/oracle.py`) — so HearSay's result is a measured match to a separate reference, not a
tautology. See `.kiro/specs/phase7/design.md` for the method. (Requires an LLM key.)

**Headline findings.** HearSay propagates a retraction structurally (JTMS recomputation) —
exact, and at **zero** token cost regardless of depth. A single LLM must re-reason, so its
cost grows and its accuracy degrades with depth:

*Token cost to propagate a retraction (DeepSeek, reasoning enabled; mean over 6 seeds):*

| dependency depth | ~facts | HearSay tokens | LLM (reason+output) tokens |
|---|---|---|---|
| 5  | 26  | 0 | ~8,200 |
| 10 | 46  | 0 | ~15,000 |
| 20 | 86  | 0 | ~27,300 |
| 40 | 166 | 0 | ~38,600 |
| 50 | 206 | 0 | ~54,000 |

LLM cost grows roughly **linearly** with depth (linear fit R² ≈ 0.96) and **without bound**,
with cost *variance* widening at depth (identical-difficulty problems ranged ~2× at depth 40+).
A single LLM also began **orphaning beliefs** — asserting conclusions with no surviving
support — from around depth 10. HearSay is correct and free at every depth by construction.
(`scripts/measure_token_growth.py` and `scripts/run_eval.py` reproduce these.)

---

## Stack

Python 3.12, asyncio, pytest + Hypothesis, FastAPI + WebSocket, Cytoscape.js. IRC server: Ergo.

---

## Kiro usage

Built spec-first with Kiro. See `.kiro/` for steering docs, per-phase specs, and design decisions. A write-up of how Kiro was used is included in the submission.
