# CI Sweeper Loop

**Goal**: Watch CI continuously. When tests go red, surface the failure immediately
and (in phase 2) draft a fix in an isolated worktree.

## When to use this pattern

- CI failures sit unnoticed for hours
- You want faster red→green cycle times
- You're comfortable with L2 (draft PRs, human approves)

## Scheduling

| Context | Schedule |
|---|---|
| Active development | every 5–15 minutes |
| Off-hours watch | every 30 minutes |
| GitHub Actions | on `workflow_run` event |

**Token cost warning**: very high if sub-agents are enabled. Start with report-only.

## Required Skills

- `ci-reader` — parses CI output, identifies failing tests and the most likely cause
- `minimal-fix` — scoped single-file fix for obvious test failures
- checker sub-agent — verifies the fix doesn't break other tests

## State Shape

```markdown
# CI Sweep State

Last sweep: 2026-06-09 14:32 UTC

## Currently Red
- `tests/test_auth.py::test_token_expiry` — failing since commit abc123
  Likely cause: expiry check off-by-one (line 42)
  Loop action: worktree open, fix drafted, PR #204 waiting review

## Watching (yellow / flaky)
- `tests/test_payments.py::test_webhook` — flaky 3/10 runs

## Green (last sweep)
- All other tests passing
```

## How the Loop Runs

1. Scheduler fires (5–15m interval or on CI event).
2. `ci-reader` skill parses the latest CI run: failed jobs, failed tests, error messages.
3. New failures added to state with timestamp + last-good commit.
4. *(Phase 2)* For single-file, obvious failures: open worktree → maker → checker → draft PR.
5. State updated with loop action taken.
6. Human reviews draft PR or picks up escalated items.

## Running It

```bash
python starters/ci-sweeper/run.py --mode schedule --interval 10
```

## Verification Strategy

Checker must confirm:
1. The targeted test now passes.
2. No other tests were broken.
3. The fix is scoped to the failure — no extra changes.

If any check fails, the draft PR is not opened; the item is escalated.

## Human Handoff Points

- Failures in auth, payments, or security modules
- Failures requiring multi-file changes
- Flaky tests (loop should watch, not fix)
- Items the loop has tried twice and still red

## Failure Modes

| Failure | Mitigation |
|---|---|
| Loop opens PRs faster than humans can review | Cap concurrent open loop PRs to 2–3 |
| Fix breaks unrelated test | Checker must run full test suite, not just the target test |
| Flaky test triggers unnecessary loop run | Add flaky-test denylist to ci-reader skill |
| Token cost spirals | Add `max_runs_per_day` guard in config |
