# Test Coverage Watcher Loop

**Goal**: Run `pytest --cov` on a schedule, compare coverage to the previous run,
and flag files where coverage dropped. At L2, draft missing tests using the
maker/checker pair and open a PR for human review.

## When to use this pattern

- You have a coverage target (e.g. 80%) and want to protect it automatically
- Coverage drops go unnoticed between PRs
- You want a safety net without enforcing hard CI gates yet

## Scheduling

| Context | Schedule |
|---|---|
| Active development | every 2–4 hours |
| CI integration | on push to main |
| Overnight watch | daily at 22:00 |

Run report-only (L1) for one week. Only enable L2 draft-fix once triage quality is consistently good.

## Required Skills

- `coverage-reader` — parses `pytest --cov` output, compares to prior run, surfaces regressions
- `test-drafter` *(phase 2)* — drafts missing tests for a single file; output is code only
- checker sub-agent *(phase 2)* — verifies drafted tests actually pass and don't duplicate existing ones

## State Shape (STATE.md)

```markdown
# Coverage Watch State

Last run: 2026-06-13 22:00 UTC
Overall coverage: 74%
Delta: -3% vs previous run

## Regressions (coverage dropped)
- [ ] src/auth/token.py  — 61% (was 79%) — priority: high
- [ ] src/payments/refund.py — 55% (was 55%) — priority: med  ← below threshold, no change

## At-Risk (below threshold, stable)
- src/utils/retry.py — 48% (threshold: 60%)

## Healthy (above threshold)
- All other modules ≥ 80%

## Run Log
### 2026-06-13 22:00 UTC
Coverage: 74%. Regressions: token.py (-18pp). Draft PR opened: #211.
```

Fields updated every run:
- Overall coverage + delta vs last run
- Per-file regressions (files that dropped since last run)
- Loop action taken (draft PR link, or "report only")

## How the Loop Runs

1. Scheduler fires.
2. `coverage-reader` skill runs `pytest --cov --cov-report=json` and parses `coverage.json`.
3. Coverage per file compared to values stored in STATE.md from previous run.
4. Files with coverage drop > threshold (default: 5pp) added to regressions list.
5. *(Phase 2)* For each regression: open worktree → maker drafts tests → checker verifies they pass → PR opened.
6. STATE.md updated with new baseline coverage values.
7. Human reviews draft PRs or escalated items.

## Running It

```bash
# One-shot test (report only)
python starters/test-coverage-watcher/run.py --mode once

# Scheduled (every 4 hours)
python starters/test-coverage-watcher/run.py --mode schedule --interval 4

# GitHub Actions
# See examples/github-actions/test-coverage-watcher.yml
```

## Verification Strategy

Checker must confirm:
1. All drafted tests pass (`pytest` exit code 0).
2. Coverage for the target file increased.
3. No existing tests were broken.
4. Drafted tests are scoped to the target file — no cross-module side effects.

If any check fails, the draft PR is not opened; item is escalated to human.

## Human Handoff Points

- Coverage drops in auth, payments, or security modules (always escalate)
- Files requiring integration tests (loop should only draft unit tests)
- Regressions caused by intentional code deletion (loop cannot know if code was removed on purpose)
- Items the loop has tried twice and coverage is still red

## Failure Modes

| Failure | Mitigation |
|---|---|
| Tests drafted but coverage still low | Checker must verify coverage increase before opening PR |
| Loop drafts tests for deleted code | Read current file before drafting; skip if file no longer exists |
| Coverage fluctuates due to flaky tests | Require 2 consecutive drops before flagging a regression |
| Token cost spirals on large repos | Limit to top-3 regressions per cycle; set `max_files_per_run` |
| Baseline drifts after intentional removal | Human can reset baseline with `--reset-baseline` flag |

## Success Metrics

- Time from "coverage dropped" to "human knows about it"
- % of coverage regressions caught before merging to main
- Reduction in "surprise coverage drop" comments on PRs

---

*Start report-only. Add draft-fix only when coverage-reader output is consistently accurate.*
