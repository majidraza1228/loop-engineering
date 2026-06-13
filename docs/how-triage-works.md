# How Triage Works

## Flow Overview

```
git repo
   │
   ▼
_gather_repo_context()   ← collects real signals from git
   │
   ▼
triage()                 ← combines STATE.md + repo context → LLM
   │
   ▼
STATE.md                 ← findings saved to Run Log
```

---

## 1. `_gather_repo_context()` — collects real signals

Runs 4 git commands against your repo:

| Command | What it captures |
|---------|-----------------|
| `git log --oneline -20` | Last 20 commits |
| `git log --since=7 days ago --name-only` | Files changed this week |
| `git grep -n TODO\|FIXME` | All TODO/FIXME lines in the codebase |
| `git log --diff-filter=A` | Files added in the last 7 days (for missing test detection) |

Without a git repo, all these return nothing and the LLM falls back to generating generic items.

---

## 2. `triage()` — sends context to the LLM

Combines two things into one prompt:

```
State: <STATE.md contents>

Repo context: <git log + TODOs + changed files>

Triage this project.
```

The LLM (OpenAI or local Ollama) uses the `loop-triage` skill from `.skills/loop-triage/SKILL.md` as its system prompt, which instructs it to return a prioritised markdown checklist of at most 8 items.

---

## 3. `STATE.md` — the memory spine

Every triage run appends its findings to the `## Run Log` section. On the next run, the LLM can see what was flagged before and avoid repeating stale items.

---

## 4. Run modes

| Mode | What happens |
|------|-------------|
| `--mode triage` | Gather context → call LLM → print findings → save to STATE.md |
| `--mode once` | Triage → pick highest-priority open task → run maker/checker agent to fix it |
| `--mode schedule` | Runs `once` every 4 hours on a loop |

`REPORT_ONLY = True` (set in `MinimalLoop`) means `once` mode triages but never auto-fixes — safe for getting started.

---

## 5. Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `USE_LOCAL` | `true` | Use local Ollama (`false` = OpenAI) |
| `OPENAI_API_KEY` | — | Required when `USE_LOCAL=false` |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI model to use |
| `LOCAL_MODEL` | `llama3` | Local Ollama model to use |
| `REPO_PATH` | `.` | Path to the git repo to triage |
| `STATE_FILE` | `STATE.md` | Path to the memory file |
