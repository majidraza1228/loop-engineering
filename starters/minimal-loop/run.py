"""
starters/minimal-loop/run.py

The simplest possible loop: triage → pick top task → fix → log.
Good for: first loop, report-only (L1), learning the primitives.

Usage:
  python starters/minimal-loop/run.py --mode once
  python starters/minimal-loop/run.py --mode schedule
  python starters/minimal-loop/run.py --mode triage   # report only
"""

import argparse
import sys
from pathlib import Path

# allow running from the repo root or this directory
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loop_engine import Config, LoopRunner


class MinimalLoop(LoopRunner):
    """
    Minimal loop — runs triage, logs findings, optionally fixes the top task.
    Set REPORT_ONLY=True for safe week-one operation.
    """

    REPORT_ONLY = True   # flip to False when you trust the triage output

    def cycle(self):
        import time
        print(f"\n[minimal-loop] {time.strftime('%Y-%m-%d %H:%M:%S')}")

        self.memory.set_last_run()
        findings = self.triage()
        self.memory.log_run(f"Triage:\n{findings}")
        print(f"\nFindings:\n{findings}\n")

        # seed Open Tasks from triage output (skip duplicates)
        existing = {t[:50] for t in self.memory.get_open_tasks()}
        for line in findings.splitlines():
            line = line.strip()
            if line.startswith("- [ ]"):
                task = line[5:].strip()
                if not any(task[:50] in e for e in existing):
                    self.memory.add_task(task)
                    existing.add(task[:50])

        if self.REPORT_ONLY:
            print("[minimal-loop] Report-only mode — no auto-fix. Review STATE.md.")
            return

        tasks = self.memory.get_open_tasks()
        if tasks:
            target = next((t for t in tasks if "high" in t.lower()), tasks[0])
            print(f"[minimal-loop] Fixing: {target}")
            self.fix_task(target, open_pr=bool(Config.GITHUB_TOKEN))
            print("[minimal-loop] STATE.md updated.")
            print(f"  [slack] (skipped) Agent completed: {target[:60]}")
        else:
            print("[minimal-loop] No open tasks.")


def main():
    parser = argparse.ArgumentParser(description="Minimal loop starter")
    parser.add_argument("--mode", choices=["once", "schedule", "triage"],
                        default="once", help="Run mode")
    parser.add_argument("--report-only", action="store_true",
                        help="Triage only — no auto-fix")
    args = parser.parse_args()

    loop = MinimalLoop()
    loop.REPORT_ONLY = args.report_only

    if args.mode == "triage":
        print(f"[debug] use_local={loop.llm.use_local}  model={loop.llm.model}")
        repo_ctx = loop._gather_repo_context()
        print(f"[debug] repo_context preview:\n{repo_ctx[:300]}\n---")
        loop.memory.set_last_run()
        findings = loop.triage()
        loop.memory.log_run(f"Triage:\n{findings}")
        print(findings)
    elif args.mode == "once":
        loop.run_once()
    elif args.mode == "schedule":
        loop.run_scheduled(interval_hours=4)


if __name__ == "__main__":
    main()
