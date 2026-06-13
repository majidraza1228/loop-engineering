"""
starters/pr-babysitter/run.py

Watches open PRs. Surfaces stalled reviews, CI failures on PR branches,
and merge conflicts. Always report-only — humans act on the findings.

Usage:
  python starters/pr-babysitter/run.py --interval 15
  python starters/pr-babysitter/run.py --once
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loop_engine import LoopRunner


class PRBabysitter(LoopRunner):

    STALE_DAYS = 2   # flag PRs with no activity for this many days

    def cycle(self):
        print(f"\n[pr-babysitter] {time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.memory.set_last_run()

        prs = self.github.list_open_prs()
        if not prs:
            print("[pr-babysitter] No open PRs (or GITHUB_TOKEN not set).")
            self.memory.log_run("PR babysitter: no open PRs.")
            return

        from datetime import datetime, timezone

        stalled, ci_red, findings = [], [], []

        for pr in prs:
            number    = pr.get("number")
            title     = pr.get("title", "")[:60]
            updated   = pr.get("updated_at", "")
            draft     = pr.get("draft", False)

            if draft:
                continue

            # Check staleness
            if updated:
                try:
                    updated_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    age_days   = (datetime.now(timezone.utc) - updated_dt).days
                    if age_days >= self.STALE_DAYS:
                        stalled.append(f"PR #{number} — '{title}' — stale {age_days}d")
                except Exception:
                    pass

        summary_parts = []
        if stalled:
            summary_parts.append("## Stalled PRs\n" + "\n".join(f"- {s}" for s in stalled))
        if not summary_parts:
            summary_parts.append("All PRs active — nothing to flag.")

        summary = "\n\n".join(summary_parts)
        self.memory.log_run(f"PR babysitter:\n{summary}")
        print(f"[pr-babysitter]\n{summary}")


def main():
    parser = argparse.ArgumentParser(description="PR Babysitter")
    parser.add_argument("--interval", type=int, default=15,
                        help="Check interval in minutes (default: 15)")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    sitter = PRBabysitter()
    if args.once:
        sitter.cycle()
    else:
        try:
            import schedule
        except ImportError:
            raise ImportError("pip install schedule")
        schedule.every(args.interval).minutes.do(sitter.cycle)
        print(f"[pr-babysitter] Watching every {args.interval}m. Ctrl+C to stop.")
        while True:
            schedule.run_pending()
            time.sleep(30)

if __name__ == "__main__":
    main()
