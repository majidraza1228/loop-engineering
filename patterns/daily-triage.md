# Daily Triage Loop

**Goal**: Start each day with a prioritised, actionable picture of what needs
attention — without manually checking CI, issues, PRs, and commits.

## When to use this pattern

- You want a low-risk first loop (L1, report-only)
- Your team wastes time figuring out "what's on fire" each morning
- You want a safe on-ramp before enabling auto-fix loops

## Scheduling

| Context | Schedule |
|---|---|
| Morning triage | daily at 08:00 |
| Active sprint | every 2 hours |
| GitHub Actions cron | `0 8 * * 1-5` (weekdays) |

Run report-only for 1–2 weeks before enabling auto-fix.

## Required Skills

- `loop-triage` — reads CI, issues, commits, prior STATE.md; produces prioritised findings
- `minimal-fix` *(phase 2, optional)* — drafts small fixes for obvious single-file failures
- checker sub-agent *(phase 2, optional)* — verifies proposed fixes

See `skills/loop-triage/SKILL.md` and `skills/minimal-fix/SKILL.md`.

## State Shape (STATE.md)

```markdown
# Loop State — Project X

Last run: 2026-06-09 08:15 UTC

## High Priority (loop acting or waiting on human)
- [ ] #1241 — flaky test in auth flow (CI red on main)
  Loop action: Opened worktree. Fix proposed. Waiting for human PR review.

## Watch List
- PR #1238 open 4 days, no activity.

## Recent Noise (ignored this run)
- Dependabot PRs (handled by separate automation)
```

Fields updated every run:
- `Last run` timestamp
- Item status + last action taken
- Human decisions that overrode the loop

## How the Loop Runs

1. Scheduler fires (morning or interval).
2. Triage skill ingests: CI failures (24h), open issues/tickets, recent commits, prior STATE.md.
3. High-priority items appended to state with suggested next action.
4. *(Phase 2)* For small, self-contained failures: open worktree → maker → checker.
5. *(Phase 3)* Connectors update PRs/tickets; ambiguous items escalated to human.
6. Prune resolved/merged items from state.

## Running It

```bash
# Local (Ollama)
python starters/minimal-loop/run.py --mode schedule

# One-shot test
python starters/minimal-loop/run.py --mode once

# GitHub Actions
# See examples/github-actions/daily-triage.yml
```

## Verification Strategy

- **Phase 1** (report-only): human reads STATE.md — no auto-action verification needed.
- **Phase 2+**: never let the maker mark work done; checker confirms fix scope and tests.
- Triage skill must not invent architectural work — signal only.

## Human Handoff Points

- Design decisions or multi-file refactors
- Security, auth, payments, infrastructure
- Items flagged "needs discussion" in triage output
- Anything the loop has surfaced 3+ days without resolution

## Failure Modes

| Failure | Mitigation |
|---|---|
| Triage creates noise | Tighten skill rules; add "Noise / Ignore" section to STATE.md |
| State file grows unbounded | Prune merged/closed items every run |
| Auto-fix on wrong priority | Start report-only; add explicit effort/risk gates |
| Missed overnight failures | Add `fireImmediately=True` or run at start of day + mid-day |

## Success Metrics

- Time from "something broke" to "human knows about it"
- % of mornings where STATE.md matched what you'd have found manually
- Reduction in ad-hoc "what's on fire?" messages

---

*Start report-only. Add action only when triage quality is consistently good.*
