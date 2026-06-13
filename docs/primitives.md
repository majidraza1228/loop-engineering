# Loop Engineering Primitives

The five building blocks every loop needs, plus memory.

---

## 1. Automations / Scheduling

**Job**: Kick off discovery and triage on a cadence, without a human pressing go.

**In Python**: `schedule` library, `threading.Timer`, GitHub Actions cron, or system cron.

**Key rule**: Start with a long cadence (daily). Shorten only when the output quality is consistently good.

---

## 2. Worktrees

**Job**: Give each parallel agent its own isolated directory so their edits never collide.

**In Python**: `git worktree add ../worktree-<branch> -b <branch>`  
Use the `Worktree` context manager in `loop_engine.py`.

**Key rule**: Only create worktrees on `agent/*` branches. Delete them after the PR is opened.

---

## 3. Skills

**Job**: Persistent project knowledge injected into the system prompt. Stops the agent guessing your conventions.

**Format**: `SKILL.md` file in `.skills/<name>/` with a YAML frontmatter header and free-form markdown body.

**Key rule**: Short, factual descriptions beat clever ones. The description is used for matching — boring is better.

---

## 4. Plugins & Connectors

**Job**: Reach into your real tools — GitHub, Slack, Linear, databases.

**In Python**: `GitHubConnector` and `SlackConnector` in `loop_engine.py`. MCP-compatible servers work too.

**Key rule**: The loop should act inside your real environment, not just tell you what it would do if it could.

---

## 5. Sub-agents

**Job**: Split maker from checker. The model that wrote the code is too kind grading its own work.

**Pattern**: `maker_agent` writes → `checker_agent` reviews → retry if score < 7.

**Key rule**: The checker needs different instructions — and ideally a different temperature — from the maker.

---

## + Memory / State

**Job**: Persist state between runs. The model forgets. The file doesn't.

**Format**: `STATE.md` — updated every cycle with timestamp, open tasks, completed items, run log.

**Key rule**: Never rely on conversation context for state. Write everything to disk.

---

## Loop Levels

| Level | Description | Auto-merge |
|---|---|---|
| L1 | Report only | Never |
| L2 | Draft PRs for human approval | No |
| L3 | Merge on CI pass + allowlist | Yes (narrow scope) |

Start every new loop at L1. Promote only when triage quality is consistently good.
