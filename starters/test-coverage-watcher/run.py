"""
starters/test-coverage-watcher/run.py

Usage:
  python run.py --mode once              # single cycle, report only
  python run.py --mode schedule          # run every 4 hours
  python run.py --mode once --fix        # single cycle + open draft PRs (L2)
  python run.py --reset-baseline         # overwrite stored baseline with current coverage
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

# Allow running from the starter dir or from the repo root
_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_ROOT))

from loop_engine import (  # noqa: E402
    Config,
    LLMClient,
    LoopMemory,
    LoopRunner,
    SkillLoader,
    SubAgents,
    Worktree,
)

# ── constants ─────────────────────────────────────────────────────────────────

COVERAGE_THRESHOLD  = 60    # files below this % are flagged
REGRESSION_DELTA    = 5     # pp drop that counts as a regression
MAX_FILES_PER_RUN   = 3     # cap LLM calls per cycle
BASELINE_KEY        = "<!-- coverage-baseline:"


# ── helpers ───────────────────────────────────────────────────────────────────

def run_pytest_coverage(repo: Path) -> dict[str, float] | None:
    """Run pytest --cov and return {file: pct} from coverage.json. Returns None on failure."""
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "--cov", str(repo),
            "--cov-report", "json",
            "--cov-report", "term-missing",
            "-q", "--tb=no",
        ],
        capture_output=True,
        text=True,
        cwd=repo,
    )

    cov_file = repo / "coverage.json"
    if not cov_file.exists():
        print(f"  [coverage] coverage.json not found — is pytest-cov installed?")
        print(f"  [coverage] stdout: {result.stdout[-500:]}")
        return None

    data = json.loads(cov_file.read_text())
    files = data.get("files", {})
    return {
        path: info["summary"]["percent_covered"]
        for path, info in files.items()
    }


def load_baseline(memory: LoopMemory) -> dict[str, float]:
    """Extract stored baseline from STATE.md comment block."""
    text = memory.read()
    match = re.search(rf"{re.escape(BASELINE_KEY)}(.*?)-->", text, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(1).strip())
    except json.JSONDecodeError:
        return {}


def save_baseline(memory: LoopMemory, baseline: dict[str, float]):
    """Persist baseline into STATE.md as a hidden comment block."""
    text = memory.read()
    blob = json.dumps(baseline, indent=2)
    new_block = f"{BASELINE_KEY}\n{blob}\n-->"

    if BASELINE_KEY in text:
        text = re.sub(
            rf"{re.escape(BASELINE_KEY)}.*?-->",
            new_block,
            text,
            flags=re.DOTALL,
        )
    else:
        text += f"\n\n{new_block}\n"

    memory.write(text)


def find_regressions(
    current: dict[str, float],
    baseline: dict[str, float],
) -> list[tuple[str, float, float | None]]:
    """Return [(file, current_pct, prior_pct_or_None)] sorted worst-first."""
    regressions = []
    for path, pct in current.items():
        prior = baseline.get(path)
        if prior is None:
            # New file below threshold with no baseline
            if pct < COVERAGE_THRESHOLD:
                regressions.append((path, pct, None))
        elif prior - pct >= REGRESSION_DELTA:
            regressions.append((path, pct, prior))
    regressions.sort(key=lambda x: (x[2] or 100) - x[1], reverse=True)
    return regressions[:MAX_FILES_PER_RUN]


# ── loop subclass ─────────────────────────────────────────────────────────────

class CoverageWatcher(LoopRunner):

    def __init__(self, auto_fix: bool = False):
        super().__init__()
        self.auto_fix = auto_fix

    def _triage_coverage(self, regressions: list, overall: float, delta: float | None) -> str:
        """Ask the LLM to prioritise and summarise the regressions."""
        if not regressions:
            return "(no regressions — all files within threshold)"

        lines = []
        for path, pct, prior in regressions:
            if prior is not None:
                lines.append(f"- {path}: {pct:.1f}% (was {prior:.1f}%)")
            else:
                lines.append(f"- {path}: {pct:.1f}% (new file, no prior baseline)")

        prompt = (
            f"Overall coverage: {overall:.1f}%"
            + (f" (delta: {delta:+.1f}pp)" if delta is not None else "")
            + f"\n\nFiles with coverage regressions:\n" + "\n".join(lines)
            + "\n\nTriage these files. Flag auth/payments/security as high. "
            + "Return ONLY a markdown task list, max 8 items."
        )
        system = self.skills.inject(
            "You are a triage agent. Surface what needs attention. Never write code.",
            "coverage-reader",
        )
        return self.llm.chat(prompt, system=system)

    def _draft_tests(self, filepath: str, pct: float) -> tuple[str, dict]:
        """Run maker/checker to draft tests for a single file."""
        source = Path(Config.REPO_PATH) / filepath
        source_code = source.read_text() if source.exists() else "(file not found)"

        task = (
            f"File: {filepath}\n"
            f"Current coverage: {pct:.1f}%\n\n"
            f"Source:\n```python\n{source_code[:3000]}\n```\n\n"
            "Draft missing pytest unit tests to improve coverage. "
            "Output ONLY the complete test file."
        )
        return self.agents.run_with_review(task, max_retries=2)

    def cycle(self):
        print(f"\n{'='*55}\nCOVERAGE CYCLE — {time.strftime('%Y-%m-%d %H:%M:%S')}\n{'='*55}")
        self.memory.set_last_run()
        repo = Config.REPO_PATH

        # 1. Run coverage
        print("[coverage] running pytest --cov ...")
        current = run_pytest_coverage(repo)
        if current is None:
            self.memory.log_run("Coverage run failed — pytest-cov may not be installed.")
            return

        overall = sum(current.values()) / len(current) if current else 0.0

        # 2. Load prior baseline and find regressions
        baseline = load_baseline(self.memory)
        prior_overall = sum(baseline.values()) / len(baseline) if baseline else None
        delta = (overall - prior_overall) if prior_overall is not None else None

        regressions = find_regressions(current, baseline)

        print(f"[coverage] overall: {overall:.1f}%"
              + (f"  delta: {delta:+.1f}pp" if delta is not None else "  (first run)"))
        print(f"[coverage] regressions found: {len(regressions)}")

        # 3. Triage
        findings = self._triage_coverage(regressions, overall, delta)
        self.memory.log_run(
            f"Coverage: {overall:.1f}%"
            + (f" ({delta:+.1f}pp)" if delta is not None else "")
            + f". Regressions: {len(regressions)}.\n{findings}"
        )
        print(f"[triage]\n{findings}\n")

        # 4. Save updated baseline
        save_baseline(self.memory, current)

        # 5. Draft fixes (L2) if enabled
        if self.auto_fix and regressions:
            for filepath, pct, prior in regressions:
                print(f"[fix] drafting tests for {filepath} ({pct:.1f}%)")
                branch = f"agent/coverage-{Path(filepath).stem}-{int(time.time())}"
                wt = Worktree(branch)
                with wt as wt_path:
                    code, verdict = self._draft_tests(filepath, pct)
                    test_path = wt_path / f"tests/test_{Path(filepath).stem}_coverage.py"
                    test_path.parent.mkdir(parents=True, exist_ok=True)
                    test_path.write_text(code)

                    score = verdict.get("score", 0)
                    if score >= 6:
                        pr_url = self.github.open_pr(
                            branch=branch,
                            title=f"[agent] add tests for {filepath} (coverage {pct:.1f}%)",
                            body=(
                                f"Coverage dropped to {pct:.1f}%"
                                + (f" (was {prior:.1f}%)" if prior else "")
                                + f".\n\nAuto-drafted tests — score {score}/10. Please review before merging."
                            ),
                        )
                        self.slack.notify(
                            f"Coverage watcher opened PR for {filepath}: {pr_url}"
                        )
                        self.memory.log_run(f"Draft PR: {filepath} → {pr_url}")
                    else:
                        print(f"  [checker] score {score}/10 — skipping PR, needs human")
                        self.memory.add_task(
                            f"Manually add tests for {filepath} ({pct:.1f}% coverage)",
                            priority="high" if pct < 40 else "med",
                        )
        elif not self.auto_fix and regressions:
            for filepath, pct, prior in regressions:
                self.memory.add_task(
                    f"Add tests for {filepath} — coverage {pct:.1f}%"
                    + (f" (was {prior:.1f}%)" if prior else ""),
                    priority="high" if pct < 40 else "med",
                )


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Test Coverage Watcher")
    parser.add_argument("--mode", choices=["once", "schedule"], default="once")
    parser.add_argument("--interval", type=float, default=4.0,
                        help="Hours between cycles (schedule mode)")
    parser.add_argument("--fix", action="store_true",
                        help="Enable L2: draft test PRs automatically")
    parser.add_argument("--reset-baseline", action="store_true",
                        help="Overwrite stored baseline with current coverage, then exit")
    args = parser.parse_args()

    watcher = CoverageWatcher(auto_fix=args.fix)

    if args.reset_baseline:
        print("[baseline] running coverage to capture new baseline ...")
        current = run_pytest_coverage(Config.REPO_PATH)
        if current:
            save_baseline(watcher.memory, current)
            overall = sum(current.values()) / len(current)
            print(f"[baseline] saved {len(current)} files. Overall: {overall:.1f}%")
        else:
            print("[baseline] failed — check pytest-cov installation")
        return

    if args.mode == "once":
        watcher.run_once()
    else:
        try:
            import schedule as _sched
        except ImportError:
            sys.exit("pip install schedule")
        _sched.every(args.interval).hours.do(watcher.cycle)
        print(f"Scheduled every {args.interval}h. Next: {_sched.next_run()}")
        while True:
            _sched.run_pending()
            time.sleep(30)


if __name__ == "__main__":
    main()
