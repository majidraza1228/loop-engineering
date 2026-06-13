# Running the Test Coverage Watcher

Three ways to run the coverage watcher. Pick the one that fits your workflow.

---

## Prerequisites (all options)

```bash
pip install openai schedule requests pytest pytest-cov
```

Set at least one LLM backend:

```bash
# Option A — local (free)
ollama pull llama3
# USE_LOCAL defaults to true, so nothing else needed

# Option B — OpenAI
export OPENAI_API_KEY=sk-...
export USE_LOCAL=false
export OPENAI_MODEL=gpt-4o-mini   # cheaper for triage
```

---

## Option 1: Claude Code `/loop` (session-based)

**Best for**: local development, watching coverage while you're actively coding.

### How to start

In Claude Code, type:

```
/loop 4h python starters/test-coverage-watcher/run.py --mode once
```

Claude wakes up every 4 hours, runs the watcher, and prints the findings directly in the session.

### Interval examples

| Command | Cadence |
|---|---|
| `/loop 30m python starters/test-coverage-watcher/run.py --mode once` | Every 30 minutes |
| `/loop 2h python starters/test-coverage-watcher/run.py --mode once` | Every 2 hours |
| `/loop 4h python starters/test-coverage-watcher/run.py --mode once` | Every 4 hours (recommended) |
| `/loop 1d python starters/test-coverage-watcher/run.py --mode once` | Once a day |

### Enable L2 (auto-draft PRs)

Add `--fix` to have Claude open draft PRs for regressions that score ≥ 6/10:

```
/loop 4h python starters/test-coverage-watcher/run.py --mode once --fix
```

Requires `GITHUB_TOKEN` and `GITHUB_REPO` to be set.

### What you see each cycle

```
=======================================================
COVERAGE CYCLE — 2026-06-13 18:00:00
=======================================================
[coverage] running pytest --cov ...
[coverage] overall: 74.2%  delta: -3.1pp
[coverage] regressions found: 2
[triage]
- [ ] src/auth/token.py — 61% (was 79%) — priority: high
- [ ] src/utils/retry.py — 55% (was 60%) — priority: med
```

`STATE.md` is updated after every cycle with the new baseline and run log.

### How to stop

Close the Claude Code session, or type `/stop` in the session to end the loop.

### Limitations

- Stops when the session closes — not suitable for overnight or unattended runs.
- `STATE.md` baseline is written locally; no automatic git commit back to the repo.

---

## Option 2: Claude Code `/schedule` (cloud agent, unattended)

**Best for**: nightly runs, running while your machine is off, team-shared schedules.

### How to start

In Claude Code, type:

```
/schedule
```

Then tell the agent:

```
Every weekday at 22:00 UTC, run:
  python starters/test-coverage-watcher/run.py --mode once
in the directory /path/to/your/repo
```

The agent is created in the cloud. It fires on the cron even when you're offline and sends you a notification with the findings.

### To enable L2

In the schedule prompt, add `--fix`:

```
Every weekday at 22:00 UTC, run:
  python starters/test-coverage-watcher/run.py --mode once --fix
```

### Managing schedules

```
/schedule list      # see all active schedules
/schedule delete    # remove a schedule
```

### Limitations

- Billed against your Claude usage.
- The scheduled agent does not have direct `git push` access, so `STATE.md` baseline
  updates are local to that agent run and do not persist back to your repo automatically.
  Use GitHub Actions (Option 3) if you need the baseline committed to the repo.

---

## Option 3: GitHub Actions (fully automated, CI-integrated)

**Best for**: team repos, persistent STATE.md baseline in git, no local machine needed.

### Setup

1. Copy the workflow file into your repo:

```bash
cp examples/github-actions/test-coverage-watcher.yml .github/workflows/
```

2. Add secrets in your GitHub repo settings (`Settings → Secrets → Actions`):

| Secret | Value |
|---|---|
| `OPENAI_API_KEY` | Your OpenAI key |
| `GITHUB_TOKEN` | Auto-provided by GitHub — no action needed |

3. Push the workflow file. It runs automatically.

### Workflow file

```yaml
# .github/workflows/test-coverage-watcher.yml

name: Test Coverage Watcher

on:
  push:
    branches: [main]          # runs on every push to main
  schedule:
    - cron: '0 22 * * *'     # nightly at 22:00 UTC
  workflow_dispatch:           # manual trigger from GitHub UI

jobs:
  coverage-watch:
    runs-on: ubuntu-latest
    permissions:
      contents: write          # to commit STATE.md baseline
      pull-requests: write     # to open draft PRs (L2 only)

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: pip

      - name: Install dependencies
        run: pip install openai schedule requests pytest pytest-cov

      - name: Run coverage watcher (report-only, L1)
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          USE_LOCAL: "false"
          OPENAI_MODEL: "gpt-4o-mini"
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_REPO: ${{ github.repository }}
        run: |
          python starters/test-coverage-watcher/run.py --mode once
          # To enable L2 (auto-draft test PRs), add: --fix

      - name: Commit updated STATE.md
        run: |
          git config user.name  "coverage-bot"
          git config user.email "coverage-bot@users.noreply.github.com"
          git add STATE.md
          git diff --staged --quiet || git commit -m "chore: coverage watch $(date -u +%Y-%m-%d)"
          git push
```

### Trigger options

| Trigger | When it fires |
|---|---|
| `push` to main | Every merge to main |
| `schedule` cron | Nightly at 22:00 UTC |
| `workflow_dispatch` | Manually from GitHub UI → Actions tab |

### To enable L2 (auto-draft PRs)

Uncomment `--fix` in the workflow step:

```yaml
run: python starters/test-coverage-watcher/run.py --mode once --fix
```

The loop will open a draft PR for each regression that scores ≥ 6/10 from the checker agent.

### Resetting the baseline

Run this locally whenever you intentionally remove code and want to reset coverage expectations:

```bash
python starters/test-coverage-watcher/run.py --reset-baseline
git add STATE.md && git commit -m "chore: reset coverage baseline"
git push
```

---

## Comparison

| | `/loop` (Option 1) | `/schedule` (Option 2) | GitHub Actions (Option 3) |
|---|---|---|---|
| Runs unattended | No | Yes | Yes |
| Persists baseline to git | No | No | Yes |
| Costs | Claude session | Claude billing | GitHub free tier |
| Setup effort | One command | One command | YAML file + secrets |
| L2 (auto-draft PRs) | Yes (`--fix`) | Yes (`--fix`) | Yes (uncomment `--fix`) |
| Best for | Active dev sessions | Overnight / offline | Team repos / CI |

---

## Choosing the right option

- **Just starting out?** Use `/loop` — zero setup, see results immediately.
- **Want it running overnight or on a team repo?** Use GitHub Actions.
- **No GitHub repo but want unattended runs?** Use `/schedule`.

Start with L1 (report-only) for one week. Only add `--fix` once triage output is consistently accurate.
