# PR Babysitter Loop

**Goal**: Watch open PRs. Detect stalled reviews, failed CI on a PR branch,
and merge conflicts. Surface them before they become blockers.

## When to use this pattern

- PRs sit open for days with no movement
- CI fails on a PR branch and nobody notices
- You want merge conflicts surfaced early

## Scheduling

Every 5–15 minutes during business hours; every 30–60 minutes off-hours.

## Required Skills

- `pr-reader` — reads open PR list, CI status per PR, review activity, conflict state
- `pr-nudge` *(optional)* — drafts a Slack/comment nudge for stalled PRs

## State Shape

```markdown
# PR Watch State

Last sweep: 2026-06-09 15:00 UTC

## Stalled (>2 days, no review activity)
- PR #198 — "Add pagination" — open 4 days, 0 reviews

## CI Red on PR Branch
- PR #201 — "Fix auth" — test_token_expiry failing since 14:20

## Merge Conflicts
- PR #196 — conflicts with main (files: src/models/user.py)

## Clean (last sweep)
- PRs #200, #202, #203 — all green, reviewed
```

## Human Handoff Points

- All nudges and PR comments — loop drafts, human sends
- Any PR touching security or payments
- PRs with design disagreements in comments

## Failure Modes

| Failure | Mitigation |
|---|---|
| Loop spams PR comments | Humans send all comments; loop only drafts |
| False "stalled" on PR under active discussion | Read comment timestamps, not just review timestamps |
| High token cost | Rate-limit to 1 full sweep per 15m; lightweight ping in between |
