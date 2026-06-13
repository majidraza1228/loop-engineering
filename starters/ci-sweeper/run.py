"""
starters/ci-sweeper/run.py

Watches CI continuously. Surfaces failures and (phase 2) drafts fixes.

Usage:
  python starters/ci-sweeper/run.py --interval 10   # sweep every 10 minutes
  python starters/ci-sweeper/run.py --once           # single sweep
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loop_engine import LoopRunner


def get_recent_test_output() -> str:
    """Run pytest and capture output. Falls back to last CI log file if present."""
    # Try reading a cached CI log first
    for log_path in [Path(".ci_last_run.txt"), Path("ci_output.txt")]:
        if log_path.exists():
            return log_path.read_text()[:4000]

    # Run pytest locally
    result = subprocess.run(
        ["python", "-m", "pytest", "--tb=short", "-q"],
        capture_output=True, text=True, cwd=".",
    )
    output = result.stdout + result.stderr
    Path(".ci_last_run.txt").write_text(output)
    return output[:4000]


class CISweeper(LoopRunner):

    REPORT_ONLY = True   # set False for phase 2 (auto-fix)
    MAX_FIXES_PER_RUN = 1

    def cycle(self):
        print(f"\n[ci-sweeper] {time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.memory.set_last_run()

        # Step 1: get CI output
        ci_output = get_recent_test_output()
        if "failed" not in ci_output.lower() and "error" not in ci_output.lower():
            print("[ci-sweeper] All tests passing. Nothing to do.")
            self.memory.log_run("CI sweep: all green.")
            return

        # Step 2: ask ci-reader skill to interpret failure
        system = self.skills.inject(
            "You are a CI analysis agent. Parse the test output and identify failures.",
            "ci-reader",
        )
        analysis = self.llm.chat(
            f"Parse this CI output and identify the failures:\n\n{ci_output}",
            system=system,
        )
        print(f"[ci-sweeper] Failures detected:\n{analysis}\n")
        self.memory.log_run(f"CI sweep — failures:\n{analysis}")

        if self.REPORT_ONLY:
            print("[ci-sweeper] Report-only mode. Review STATE.md for details.")
            return

        # Step 3 (phase 2): attempt a fix
        import json, re
        try:
            data = json.loads(re.search(r'\{.*\}', analysis, re.DOTALL).group())
            likely_file  = data.get("file", "")
            likely_cause = data.get("likely_cause", "")
            confidence   = data.get("confidence", "low")
        except Exception:
            print("[ci-sweeper] Could not parse structured analysis — skipping auto-fix.")
            return

        if confidence != "high" or not likely_file:
            print(f"[ci-sweeper] Confidence={confidence} — escalating to human.")
            return

        task = f"Fix the test failure in {likely_file}. Cause: {likely_cause}"
        print(f"[ci-sweeper] Attempting fix: {task}")
        code, verdict = self.fix_task(task, open_pr=bool(self.github.token))
        print(f"[ci-sweeper] Fix score: {verdict.get('score')}/10")


def main():
    parser = argparse.ArgumentParser(description="CI Sweeper")
    parser.add_argument("--interval", type=int, default=10,
                        help="Sweep interval in minutes (default: 10)")
    parser.add_argument("--once", action="store_true", help="Single sweep")
    args = parser.parse_args()

    sweeper = CISweeper()

    if args.once:
        sweeper.cycle()
    else:
        try:
            import schedule
        except ImportError:
            raise ImportError("pip install schedule")
        schedule.every(args.interval).minutes.do(sweeper.cycle)
        print(f"[ci-sweeper] Watching CI every {args.interval}m. Ctrl+C to stop.")
        while True:
            schedule.run_pending()
            time.sleep(30)


if __name__ == "__main__":
    main()
