"""
starters/dependency-sweeper/run.py

Checks for outdated Python/Node dependencies.
Drafts patch-only upgrade PRs. Major/minor versions always escalate.

Usage:
  python starters/dependency-sweeper/run.py
  python starters/dependency-sweeper/run.py --ecosystem python
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loop_engine import LoopRunner


def get_outdated_python() -> list[dict]:
    result = subprocess.run(
        ["pip", "list", "--outdated", "--format=json"],
        capture_output=True, text=True,
    )
    try:
        return json.loads(result.stdout)
    except Exception:
        return []


def get_outdated_node() -> str:
    result = subprocess.run(
        ["npm", "outdated", "--json"],
        capture_output=True, text=True,
    )
    return result.stdout or "{}"


def is_patch_only(current: str, latest: str) -> bool:
    """True if only the patch version changed (1.2.3 → 1.2.4)."""
    try:
        c = [int(x) for x in current.split(".")[:3]]
        l = [int(x) for x in latest.split(".")[:3]]
        return c[0] == l[0] and c[1] == l[1] and c[2] < l[2]
    except Exception:
        return False


class DependencySweeper(LoopRunner):

    def sweep_python(self):
        outdated = get_outdated_python()
        if not outdated:
            print("[dep-sweeper] All Python packages up to date.")
            return

        patch_updates = [p for p in outdated if is_patch_only(p["version"], p["latest_version"])]
        escalate      = [p for p in outdated if not is_patch_only(p["version"], p["latest_version"])]

        print(f"[dep-sweeper] {len(patch_updates)} patch updates, {len(escalate)} major/minor (escalated)")

        if escalate:
            summary = "\n".join(f"  - {p['name']} {p['version']} → {p['latest_version']}" for p in escalate)
            self.memory.add_task(f"Review major/minor dep upgrades:\n{summary}", priority="med")

        if patch_updates:
            names = " ".join(f"{p['name']}=={p['latest_version']}" for p in patch_updates)
            task  = f"Upgrade patch-version Python deps: {names}"
            print(f"[dep-sweeper] Drafting fix: {task}")
            self.fix_task(task, open_pr=bool(self.github.token))

    def sweep(self, ecosystem: str = "python"):
        self.memory.set_last_run()
        if ecosystem in ("python", "both"):
            self.sweep_python()
        if ecosystem in ("node", "both"):
            raw = get_outdated_node()
            self.memory.log_run(f"Node outdated check:\n{raw[:500]}")
            print(f"[dep-sweeper] Node outdated:\n{raw[:500]}")


def main():
    parser = argparse.ArgumentParser(description="Dependency Sweeper")
    parser.add_argument("--ecosystem", choices=["python", "node", "both"],
                        default="python")
    args = parser.parse_args()

    sweeper = DependencySweeper()
    sweeper.sweep(args.ecosystem)


if __name__ == "__main__":
    main()
