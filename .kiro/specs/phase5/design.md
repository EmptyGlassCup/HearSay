# Phase 5 — Domain experts (incident root-cause analysis)

Domain locked in: incident RCA. KSs live in src/hearsay/experts/ ([KIRO]-authored,
human-reviewed). Scenarios live in eval/scenarios/.

## The seeded scenario: "latency spike"

Incident: a web service's p99 latency spikes at 03:14. Find the root cause.

Ground truth (real cause): a config change at 03:12 cut db.pool.max 50 -> 5, so requests
queue waiting for DB connections, driving latency up.

Evidence available to the KSs:
| id  | text                                             | points to      | nature            |
|-----|--------------------------------------------------|----------------|-------------------|
| e_cfg  | 03:12 config change: db.pool.max 50->5        | real cause     | true, decisive    |
| e_lat  | 03:14 p99 latency 180ms -> 4200ms             | symptom        | true              |
| e_wait | 03:14 db connection wait time 3800ms          | real cause     | true, corroborating|
| e_dep  | 03:10 deployment of v2.4.1                     | red herring    | true but irrelevant|
| e_cpu  | 03:14 CPU 40% (normal)                         | rules out CPU  | true, exculpatory |
| e_mem  | 03:14 memory usage 95%  <-- PLANTED/MISLEADING | false lead     | retracted in demo |

Demo arc: e_mem leads a KS to hypothesise "v2.4.1 deploy -> memory leak -> latency",
which goes IN. The operator retracts e_mem (misread; real value 45%). The memory-leak
hypothesis and everything built on it ghost OUT. The config-pool hypothesis, supported by
e_cfg + e_wait, survives and becomes the winning conclusion.

Goal claim: a conclusion-kind claim naming the root cause, IN above the goal threshold.

## Knowledge sources to build (in order)

1. LogMatcherKS (classical, deterministic) - scans scenario "log" lines -> evidence claims.
2. MetricThresholdKS (classical) - reads scenario "metrics" -> evidence claims (incl e_mem).
3. LLMHypothesisKS - reads IN evidence, proposes hypotheses + justifications.
4. LLMCriticKS (optional) - challenges weakly-supported hypotheses via CHALLENGE events.

## LLM backend

LLMClient interface with one method: complete(prompt: str) -> str.
- LocalLLMClient: POSTs to LM Studio's OpenAI-compatible endpoint
  (http://localhost:1234/v1/chat/completions). Model: bonsai-27b. No key.
- APILLMClient (later/optional): same shape, base_url + api_key for DeepSeek/Claude.
KSs depend only on the interface, never on a concrete backend.

## Decision: LLM KS is synchronous (blocking)

The scheduler is sync; an LLM `action` call blocks the kernel (including IRC) for the
duration of the call (a few seconds on local bonsai). We accept this deliberately:
- Making it async forces run()/pick/kernel all async AND introduces concurrent board
  mutation — a human retraction mid-LLM-call would change the board the activation is
  reasoning about, risking hypotheses justified by just-retracted premises.
- Sequential application preserves the deterministic event ordering the whole design rests on.
- The pause is bounded and legible in a demo ("it's thinking now").
[TODO/future] If responsiveness becomes a problem, revisit with a design that snapshots the
board for the duration of an activation, or runs the HTTP call in a thread executor while
keeping activation application sequential.

## Open questions / decisions
- Scenario format: how are logs/metrics represented on disk in eval/scenarios/ (JSON?).
- How a scenario is fed in: a loader that emits the initial evidence ClaimEvents, OR a
  "source" KS that reads the scenario file. Decide before building KS 1 and 2.
- Prompt format for the LLM hypothesis KS, and how to parse its output back into
  claim + justify events deterministically (the LLM output must be coerced into structured
  events; free text alone can't drive the JTMS).
