"""
loop_engine.py — shared core used by all starters.

Provides:
  - LLMClient    : thin wrapper around OpenAI/Ollama
  - LoopMemory   : STATE.md read/write
  - SkillLoader  : SKILL.md injection
  - Worktree     : git worktree lifecycle
  - SubAgent     : maker + checker
  - Connectors   : GitHub PR + Slack notify
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

# ── optional deps (graceful degradation) ──────────────────────────────────────
try:
    import requests as _requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from openai import OpenAI as _OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════

class Config:
    """Central config. Override via env vars or pass kwargs to LLMClient."""

    USE_LOCAL:      bool = os.getenv("USE_LOCAL", "true").lower() != "false"
    LOCAL_BASE_URL: str  = os.getenv("LOCAL_BASE_URL", "http://localhost:11434/v1")
    LOCAL_MODEL:    str  = os.getenv("LOCAL_MODEL",    "llama3")
    OPENAI_KEY:     str  = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL:   str  = os.getenv("OPENAI_MODEL",   "gpt-4o")

    GITHUB_TOKEN:   str  = os.getenv("GITHUB_TOKEN",   "")
    GITHUB_REPO:    str  = os.getenv("GITHUB_REPO",    "owner/repo")
    SLACK_WEBHOOK:  str  = os.getenv("SLACK_WEBHOOK_URL", "")

    SKILLS_DIR:     Path = Path(os.getenv("SKILLS_DIR", ".skills"))
    STATE_FILE:     Path = Path(os.getenv("STATE_FILE", "STATE.md"))
    REPO_PATH:      Path = Path(os.getenv("REPO_PATH",  "."))


# ══════════════════════════════════════════════════════════════════════════════
# LLM CLIENT
# ══════════════════════════════════════════════════════════════════════════════

class LLMClient:
    """Thin wrapper — swap Ollama ↔ OpenAI with one flag."""

    def __init__(self, use_local: bool = Config.USE_LOCAL):
        if not HAS_OPENAI:
            raise ImportError("pip install openai")
        self.use_local = use_local
        if use_local:
            self._client = _OpenAI(base_url=Config.LOCAL_BASE_URL, api_key="ollama")
            self.model   = Config.LOCAL_MODEL
        else:
            self._client = _OpenAI(api_key=Config.OPENAI_KEY)
            self.model   = Config.OPENAI_MODEL

    def chat(self, prompt: str, system: str = "You are a helpful coding agent.",
             temperature: float = 0.2) -> str:
        resp = self._client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
        )
        return resp.choices[0].message.content.strip()


# ══════════════════════════════════════════════════════════════════════════════
# MEMORY
# ══════════════════════════════════════════════════════════════════════════════

_STATE_TEMPLATE = """\
# Loop State

Last run: —

## High Priority

## Watch List

## Open Tasks

## Completed

## Run Log

"""

class LoopMemory:
    """Read/write STATE.md — the spine of the loop."""

    def __init__(self, path: Path = Config.STATE_FILE):
        self.path = path
        if not self.path.exists():
            self.path.write_text(_STATE_TEMPLATE)

    def read(self) -> str:
        return self.path.read_text()

    def write(self, content: str):
        self.path.write_text(content)

    def _update_section(self, heading: str, new_content: str):
        text   = self.read()
        marker = f"## {heading}"
        # find the section and insert after the heading
        if marker in text:
            idx = text.index(marker) + len(marker)
            text = text[:idx] + "\n" + new_content + text[idx:]
        else:
            text += f"\n## {heading}\n{new_content}\n"
        self.write(text)

    def add_task(self, task: str, priority: str = "med"):
        line = f"- [ ] {task} — priority: {priority}\n"
        self._update_section("Open Tasks", line)

    def mark_done(self, task_fragment: str):
        text = self.read()
        lines = text.splitlines()
        updated = []
        for line in lines:
            if task_fragment in line and line.strip().startswith("- [ ]"):
                line = line.replace("- [ ]", "- [x]", 1)
            updated.append(line)
        self.write("\n".join(updated))

    def log_run(self, summary: str):
        ts    = time.strftime("%Y-%m-%d %H:%M UTC")
        entry = f"\n### {ts}\n{summary.strip()}\n"
        self._update_section("Run Log", entry)

    def set_last_run(self):
        ts   = time.strftime("%Y-%m-%d %H:%M UTC")
        text = self.read()
        text = re.sub(r"Last run:.*", f"Last run: {ts}", text, count=1)
        self.write(text)

    def get_open_tasks(self) -> list[str]:
        return [
            line.replace("- [ ] ", "").strip()
            for line in self.read().splitlines()
            if line.strip().startswith("- [ ]")
        ]


# ══════════════════════════════════════════════════════════════════════════════
# SKILLS
# ══════════════════════════════════════════════════════════════════════════════

class SkillLoader:
    """Loads SKILL.md files and injects them into prompts."""

    def __init__(self, skills_dir: Path = Config.SKILLS_DIR):
        self.dir = skills_dir

    def load(self, name: str) -> str:
        path = self.dir / name / "SKILL.md"
        return path.read_text() if path.exists() else ""

    def inject(self, system: str, skill_name: str) -> str:
        skill = self.load(skill_name)
        if skill:
            return f"{system}\n\n## Project skill: {skill_name}\n{skill}"
        return system

    def create_starter_skills(self):
        """Write example SKILL.md files if they don't exist."""
        defaults = {
            "loop-triage": _SKILL_TRIAGE,
            "minimal-fix":  _SKILL_MINIMAL_FIX,
            "ci-reader":    _SKILL_CI_READER,
            "changelog":    _SKILL_CHANGELOG,
        }
        for name, content in defaults.items():
            skill_dir  = self.dir / name
            skill_file = skill_dir / "SKILL.md"
            skill_dir.mkdir(parents=True, exist_ok=True)
            if not skill_file.exists():
                skill_file.write_text(content)


_SKILL_TRIAGE = """\
---
name: loop-triage
description: Reads repo state and produces a prioritised task list. Never writes code.
---
# Triage skill
## What to look for
1. Files with TODO/FIXME added in the last 7 days
2. Functions > 50 lines (complexity risk)
3. Missing tests for recently added files
4. CI failures (check the run log)
## Output format
Return ONLY a markdown list, max 8 items:
- [ ] {description} — priority: high/med/low
## Rules
- Skip auto-generated files (src/generated/, dist/, build/)
- Flag security issues as high regardless of size
- Do not propose architectural changes
"""

_SKILL_MINIMAL_FIX = """\
---
name: minimal-fix
description: Writes a scoped, single-file fix. Output is code only.
---
# Minimal fix skill
## Rules
- Fix ONLY what the task describes. Nothing else.
- One file changed maximum.
- Add type hints and a docstring if they're missing.
- Output ONLY the complete fixed file — no explanation.
"""

_SKILL_CI_READER = """\
---
name: ci-reader
description: Parses CI output and identifies the most likely failure cause.
---
# CI reader skill
## Output format
Return JSON:
{
  "failing_tests": ["test_name"],
  "likely_cause": "one sentence",
  "file": "path/to/file.py",
  "line_hint": 42,
  "confidence": "high|medium|low"
}
"""

_SKILL_CHANGELOG = """\
---
name: changelog
description: Drafts a CHANGELOG entry from git commits.
---
# Changelog skill
## Output format
## [version] — YYYY-MM-DD
### Added
- ...
### Changed
- ...
### Fixed
- ...
### Removed
- ...
## Rules
- Plain language. No jargon.
- One line per commit (group related commits).
- Skip merge commits and automated dependency bumps.
"""


# ══════════════════════════════════════════════════════════════════════════════
# WORKTREES
# ══════════════════════════════════════════════════════════════════════════════

class Worktree:
    """Context manager for an isolated git worktree."""

    def __init__(self, branch: str, repo: Path = Config.REPO_PATH):
        self.branch = branch
        self.repo   = repo
        self.path   = repo.parent / f"worktree-{branch.replace('/', '-')}"

    def create(self) -> Path:
        result = subprocess.run(
            ["git", "worktree", "add", str(self.path), "-b", self.branch],
            capture_output=True, text=True, cwd=self.repo,
        )
        if result.returncode != 0:
            # branch may already exist — try checking out instead
            subprocess.run(
                ["git", "worktree", "add", str(self.path), self.branch],
                capture_output=True, text=True, cwd=self.repo,
            )
        return self.path

    def remove(self):
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(self.path)],
            capture_output=True, cwd=self.repo,
        )

    def __enter__(self) -> Path:
        return self.create()

    def __exit__(self, *_):
        self.remove()


def run_in_worktree(branch: str, fn, *args, **kwargs):
    """Run fn(worktree_path, *args, **kwargs) in an isolated worktree."""
    wt = Worktree(branch)
    with wt as path:
        return fn(path, *args, **kwargs)


# ══════════════════════════════════════════════════════════════════════════════
# SUB-AGENTS
# ══════════════════════════════════════════════════════════════════════════════

class SubAgents:
    """Maker + checker sub-agent pair."""

    def __init__(self, llm: LLMClient, skills: SkillLoader):
        self.llm    = llm
        self.skills = skills

    def maker(self, task: str, skill_name: str = "minimal-fix") -> str:
        system = self.skills.inject(
            "You are a senior engineer. Write clean, working code. Output ONLY code.",
            skill_name,
        )
        return self.llm.chat(task, system=system)

    def checker(self, code: str, task: str) -> dict:
        system = (
            "You are a strict code reviewer. Be skeptical. Find bugs, security issues, "
            "and edge cases the author missed. "
            "Reply ONLY with valid JSON: "
            '{"verdict": "pass"|"fail", "score": 0-10, "issues": [...]}'
        )
        raw = self.llm.chat(
            f"Original task:\n{task}\n\nCode to review:\n```\n{code}\n```",
            system=system,
        )
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {"verdict": "fail", "score": 0, "issues": [raw[:300]]}

    def run_with_review(self, task: str, max_retries: int = 2) -> tuple[str, dict]:
        """Maker→checker loop with retry. Returns (code, verdict)."""
        current = task
        last_code, last_verdict = "", {}

        for attempt in range(max_retries + 1):
            print(f"    [maker] attempt {attempt+1}")
            code    = self.maker(current)
            verdict = self.checker(code, task)
            score   = verdict.get("score", 0)
            last_code, last_verdict = code, verdict

            if verdict.get("verdict") == "pass" or score >= 7:
                print(f"    [checker] pass (score {score}/10)")
                return code, verdict

            issues = "\n".join(f"- {i}" for i in verdict.get("issues", []))
            print(f"    [checker] fail (score {score}/10) — feeding back")
            current = f"{task}\n\nFix these issues from your previous attempt:\n{issues}"

        return last_code, last_verdict


def run_parallel(tasks: list[tuple[str, callable]], *args):
    """Run a list of (name, fn) pairs in parallel threads."""
    threads = [threading.Thread(target=fn, args=args, daemon=True) for _, fn in tasks]
    for t in threads: t.start()
    for t in threads: t.join()


# ══════════════════════════════════════════════════════════════════════════════
# CONNECTORS
# ══════════════════════════════════════════════════════════════════════════════

class GitHubConnector:

    def __init__(self, token: str = Config.GITHUB_TOKEN, repo: str = Config.GITHUB_REPO):
        self.token = token
        self.repo  = repo

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
        }

    def open_pr(self, branch: str, title: str, body: str = "", base: str = "main") -> str:
        if not self.token or not HAS_REQUESTS:
            return "(skipped — GITHUB_TOKEN not set)"
        resp = _requests.post(
            f"https://api.github.com/repos/{self.repo}/pulls",
            headers=self._headers(),
            json={"title": title, "body": body, "head": branch, "base": base},
            timeout=10,
        )
        if resp.status_code == 201:
            return resp.json()["html_url"]
        return f"(failed {resp.status_code})"

    def list_open_prs(self) -> list[dict]:
        if not self.token or not HAS_REQUESTS:
            return []
        resp = _requests.get(
            f"https://api.github.com/repos/{self.repo}/pulls",
            headers=self._headers(), timeout=10,
        )
        return resp.json() if resp.status_code == 200 else []

    def list_issues(self, state: str = "open", labels: str = "") -> list[dict]:
        if not self.token or not HAS_REQUESTS:
            return []
        params: dict = {"state": state, "per_page": 50}
        if labels:
            params["labels"] = labels
        resp = _requests.get(
            f"https://api.github.com/repos/{self.repo}/issues",
            headers=self._headers(), params=params, timeout=10,
        )
        return resp.json() if resp.status_code == 200 else []


class SlackConnector:

    def __init__(self, webhook: str = Config.SLACK_WEBHOOK):
        self.webhook = webhook

    def notify(self, message: str) -> bool:
        if not self.webhook or not HAS_REQUESTS:
            print(f"  [slack] (skipped) {message[:80]}")
            return False
        resp = _requests.post(self.webhook, json={"text": message}, timeout=10)
        return resp.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# LOOP RUNNER
# ══════════════════════════════════════════════════════════════════════════════

class LoopRunner:
    """
    High-level loop runner. Wires all five blocks together.
    Override `cycle()` in subclasses for custom patterns.
    """

    def __init__(self):
        self.llm      = LLMClient()
        self.memory   = LoopMemory()
        self.skills   = SkillLoader()
        self.agents   = SubAgents(self.llm, self.skills)
        self.github   = GitHubConnector()
        self.slack    = SlackConnector()

        self.skills.create_starter_skills()

    # ── building block helpers ─────────────────────────────────────────────

    def _gather_repo_context(self) -> str:
        repo = Config.REPO_PATH
        parts = []

        r = subprocess.run(["git", "log", "--oneline", "-20"],
                           capture_output=True, text=True, cwd=repo)
        if r.returncode == 0 and r.stdout.strip():
            parts.append(f"## Recent commits\n{r.stdout.strip()}")

        r = subprocess.run(
            ["git", "log", "--since=7 days ago", "--name-only", "--pretty=format:"],
            capture_output=True, text=True, cwd=repo,
        )
        if r.returncode == 0 and r.stdout.strip():
            files = sorted(set(f for f in r.stdout.splitlines() if f.strip()))[:30]
            parts.append("## Files changed in last 7 days\n" + "\n".join(files))

        r = subprocess.run(["git", "grep", "-n", "-E", "TODO|FIXME"],
                           capture_output=True, text=True, cwd=repo)
        if r.returncode == 0 and r.stdout.strip():
            lines = r.stdout.splitlines()[:30]
            parts.append("## TODO/FIXME\n" + "\n".join(lines))

        r = subprocess.run(
            ["git", "log", "--since=7 days ago", "--diff-filter=A",
             "--name-only", "--pretty=format:"],
            capture_output=True, text=True, cwd=repo,
        )
        if r.returncode == 0 and r.stdout.strip():
            new_files = [f for f in r.stdout.splitlines() if f.strip()]
            parts.append("## Files added in last 7 days\n" + "\n".join(new_files))

        return "\n\n".join(parts) if parts else "(not a git repo or no history)"

    def triage(self) -> str:
        """Block 1 + 3: Call triage skill, return findings."""
        repo_ctx = self._gather_repo_context()
        system = self.skills.inject(
            "You are a triage agent. Surface what needs attention. Never write code.",
            "loop-triage",
        )
        return self.llm.chat(
            f"State:\n{self.memory.read()}\n\nRepo context:\n{repo_ctx}\n\nTriage this project.",
            system=system,
        )

    def fix_task(self, task: str, open_pr: bool = False) -> tuple[str, dict]:
        """Block 1+2+5: Fix a task in an isolated worktree with maker/checker."""
        import re as _re
        safe   = _re.sub(r'[^a-z0-9-]', '-', task[:30].lower()).strip('-')
        branch = f"agent/{safe}-{int(time.time())}"

        wt = Worktree(branch)
        with wt as wt_path:
            code, verdict = self.agents.run_with_review(task)
            (wt_path / "AGENT_OUTPUT.md").write_text(
                f"# Task\n{task}\n\n"
                f"# Score\n{verdict.get('score')}/10\n\n"
                f"# Code\n```\n{code}\n```\n"
            )

            pr_url = ""
            if open_pr and verdict.get("score", 0) >= 6:
                pr_url = self.github.open_pr(
                    branch=branch,
                    title=f"[agent] {task[:60]}",
                    body=f"Auto-generated fix — score {verdict.get('score')}/10.\n\nPlease review before merging.",
                )
                self.slack.notify(f"🤖 Agent opened PR: {task[:50]}\n{pr_url}")

        self.memory.mark_done(task)
        self.memory.log_run(f"Fixed: {task} (score {verdict.get('score')}/10)")
        return code, verdict

    # ── main cycle ─────────────────────────────────────────────────────────

    def cycle(self):
        """One full loop cycle. Override in subclasses."""
        print(f"\n{'='*55}\nLOOP CYCLE — {time.strftime('%Y-%m-%d %H:%M:%S')}\n{'='*55}")
        self.memory.set_last_run()

        findings = self.triage()
        self.memory.log_run(f"Triage:\n{findings}")
        print(f"[triage]\n{findings}\n")

        tasks = self.memory.get_open_tasks()
        high  = [t for t in tasks if "high" in t.lower()]
        target = (high or tasks or [None])[0]

        if target:
            print(f"[fix] → {target}")
            self.fix_task(target, open_pr=bool(Config.GITHUB_TOKEN))
        else:
            print("[loop] No open tasks this cycle.")

    def run_once(self):
        self.cycle()

    def run_scheduled(self, interval_hours: float = 4.0):
        try:
            import schedule as _sched
        except ImportError:
            raise ImportError("pip install schedule")

        _sched.every(interval_hours).hours.do(self.cycle)
        _sched.every().day.at("08:00").do(self.cycle)
        print(f"Scheduled loop running. Next run: {_sched.next_run()}")
        while True:
            _sched.run_pending()
            time.sleep(30)
