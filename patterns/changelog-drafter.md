# Changelog Drafter Loop

**Goal**: On a schedule (or tag event), read git commits since the last release
and draft a clean, human-readable CHANGELOG entry. Human edits and approves.

## When to use this pattern

- Writing CHANGELOGs by hand from git log is tedious
- You want a consistent format without manual effort
- Low-risk first loop — output is always a draft for human review

## Scheduling

- Daily at end of day, or
- Triggered on tag push (`v*`)

**Token cost**: Low. Recommended first loop for teams new to loop engineering.

## Required Skills

- `changelog-agent` (defined in AGENTS.md) — groups commits into Added/Changed/Fixed/Removed

## State Shape

Minimal — just a draft file:

```
CHANGELOG_DRAFT.md   ← loop writes here each run
CHANGELOG.md         ← human edits and merges approved draft
```

## How the Loop Runs

1. Scheduler fires or tag is pushed.
2. Loop runs `git log <last-tag>..HEAD --oneline`.
3. changelog-agent groups commits and drafts CHANGELOG entry.
4. Draft written to `CHANGELOG_DRAFT.md`.
5. Human reviews, edits, and appends to `CHANGELOG.md`.

## Running It

```bash
python starters/changelog-drafter/run.py
```

## Human Handoff Points

Everything — the loop only drafts. Human reviews 100% of output before it ships.

## Failure Modes

| Failure | Mitigation |
|---|---|
| Commits are too cryptic to summarise | Improve commit message conventions (separate concern) |
| Draft misses important changes | Add "Important changes" section for human to fill in |
