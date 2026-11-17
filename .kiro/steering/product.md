# Product

## Project name
HearSay — a Truth-Maintained Blackboard over IRC

## Hackathon
Kiroween 2026, Resurrection category. Deadline: Dec 4, 2026, 2:00 PM PT. Target submission: Dec 3.

## Problem
Multi-agent LLM systems accumulate unsupported claims. One agent asserts something, another builds on it, and nobody can say what the final answer actually rests on. When a premise turns out to be wrong, nothing automatically cleans up the conclusions that depended on it.

## Solution
Every claim on the shared blackboard must carry a justification. If a premise is retracted, every dependent claim becomes a **ghost** (OUT: remembered and shown, but not believed). If support is restored, the ghost revives automatically. Control is symbolic and deterministic, not an LLM. Humans participate and observe using any ordinary IRC client.

## Three resurrected ideas

| Idea | Origin | Role |
|---|---|---|
| Internet Relay Chat | 1988 | Human-readable transport and observable event log |
| Blackboard architecture | Hearsay-II, 1970s | Shared workspace where independent experts post hypotheses |
| Justification-based truth maintenance (JTMS) | Doyle, 1979 | Tracks belief dependencies; retraction cascades automatically |

## Target users
Engineers or analysts who need auditable multi-expert reasoning.

## Core claim to demonstrate
Compared with an LLM-orchestrated baseline, this design produces fewer unsupported claims in final answers, at lower cost, with a fully auditable reasoning trail.

## Hackathon constraints
- Project must be new (started on or after Oct 30, 2026).
- Public GitHub repo with an OSI-detectable open-source license.
- `/.kiro` directory at the repo root — never add it to `.gitignore`.
- Working app URL or clear run instructions, a text description, a YouTube demo under 3 minutes.
- Write-up on how Kiro was used.
- No third-party trademarks or copyrighted music in the video.

## Demo plan (under 3 minutes)
Show an ordinary IRC client and the web graph side by side. Plant bad evidence. Retract it. Watch dependent claims turn into ghosts. Supply corrected evidence and watch them revive. Show ablation numbers.
