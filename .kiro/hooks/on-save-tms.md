# Hook: run property tests on TMS save

**Trigger**: file save in `src/hearsay/tms/` or `src/hearsay/protocol/`

**Command**:
```
pytest tests/ -k "property" --tb=short -q
```

**Purpose**: catch JTMS and codec property violations immediately on save, before they compound.

> This is a placeholder. Wire it up in .kiro/hooks/ config once the first property tests exist (Phase 2).
