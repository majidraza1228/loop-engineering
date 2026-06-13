# Dependency Sweeper Loop

**Goal**: Periodically check for outdated or vulnerable dependencies. Draft
patch-version upgrade PRs. Escalate major-version changes to human.

## Scheduling

Every 6–24 hours. Outside business hours is fine — low urgency.

## Required Skills

- `dep-reader` — runs `pip list --outdated` or `npm outdated`, reads output
- `dep-patcher` *(phase 2)* — drafts a requirements.txt or package.json update for patch versions only

## Rules

- **Patch versions only** for auto-draft (`1.2.3` → `1.2.4`). Minor and major always escalate.
- Never auto-merge. Always human approval.
- Security advisories → immediate escalation regardless of version bump size.

## Failure Modes

| Failure | Mitigation |
|---|---|
| Patch update breaks compatibility | Run full test suite in worktree before opening PR |
| Loop opens too many dep PRs | Group updates into one PR per language ecosystem |
