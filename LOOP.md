# LOOP.md

This file describes the loops that maintain this repository.

## Active Loops

### 1. Daily Triage (report-only)
- **Schedule**: weekdays 08:00 UTC
- **Pattern**: [patterns/daily-triage.md](patterns/daily-triage.md)
- **Starter**: [starters/minimal-loop/](starters/minimal-loop/)
- **Action**: reads open issues + recent commits, updates STATE.md
- **Auto-fix**: disabled (L1 mode)

### 2. Pattern Validator
- **Schedule**: on every push/PR
- **Action**: checks that all patterns listed in patterns/registry.yaml have a matching .md file and starter directory
- **CI**: [.github/workflows/validate-patterns.yml](.github/workflows/validate-patterns.yml)

## Loop Levels

| Level | Description | Auto-fix |
|---|---|---|
| L1 | Report only — loop surfaces findings, human acts | No |
| L2 | Assisted — loop drafts fixes, human approves | PR only |
| L3 | Unattended — loop merges on passing CI + allowlist | Yes |

This repo runs **L1** on its own triage loop. Patterns documented here may describe L2 or L3 — those are for your repo, not this one.

## Human Gates

The following always require human review regardless of loop level:

- Security, auth, payments, infrastructure changes
- Multi-file refactors
- Anything the loop has surfaced 3+ days without resolution
- Items flagged ambiguous by the triage skill
