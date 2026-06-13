# Post-Merge Cleanup Loop

**Goal**: After a PR merges, automatically clean up: delete merged branches,
close linked issues, remove TODO comments marked as resolved, update STATE.md.

## Scheduling

Triggered on `push` to main, or daily off-peak sweep.

**Token cost**: Low. Safe to run frequently.

## Required Skills

- `cleanup-agent` — identifies stale branches, closed issues still open, resolved TODOs

## Rules

- Only delete branches the loop itself created (`agent/*` prefix).
- Never delete branches with open PRs.
- Only close issues if PR body explicitly says "closes #N" or "fixes #N".

## Running It

```bash
python starters/minimal-loop/run.py --mode once --task cleanup
```
