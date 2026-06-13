"""
tools/loop_init.py — scaffold a loop starter into your project.

Usage:
  python tools/loop_init.py . --pattern daily-triage
  python tools/loop_init.py /path/to/project --pattern ci-sweeper
"""

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

PATTERNS = {
    "daily-triage":           "starters/minimal-loop",
    "ci-sweeper":             "starters/ci-sweeper",
    "pr-babysitter":          "starters/minimal-loop",   # uses minimal-loop base
    "dependency-sweeper":     "starters/dependency-sweeper",
    "changelog-drafter":      "starters/changelog-drafter",
    "post-merge-cleanup":     "starters/minimal-loop",
    "test-coverage-watcher":  "starters/test-coverage-watcher",
}

FILES_TO_COPY = [
    "loop_engine.py",
    "STATE.md",
    "LOOP.md",
    "AGENTS.md",
]


def scaffold(target: Path, pattern: str):
    target = target.resolve()
    target.mkdir(parents=True, exist_ok=True)

    starter_src = REPO_ROOT / PATTERNS.get(pattern, "starters/minimal-loop")

    # Copy core engine
    for fname in FILES_TO_COPY:
        src = REPO_ROOT / fname
        dst = target / fname
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
            print(f"  copied  {fname}")
        elif dst.exists():
            print(f"  exists  {fname} (skipped)")

    # Copy starter run.py
    run_src = starter_src / "run.py"
    run_dst = target / "loop_run.py"
    if run_src.exists() and not run_dst.exists():
        shutil.copy2(run_src, run_dst)
        print(f"  copied  loop_run.py  (from {starter_src.name})")

    # Copy skills
    skills_src = REPO_ROOT / "skills"
    skills_dst = target / ".skills"
    if skills_src.exists():
        for skill_dir in skills_src.iterdir():
            if skill_dir.is_dir():
                dst_skill = skills_dst / skill_dir.name
                if not dst_skill.exists():
                    shutil.copytree(skill_dir, dst_skill)
                    print(f"  skill   .skills/{skill_dir.name}/")

    # Copy pattern doc
    pattern_src = REPO_ROOT / "patterns" / f"{pattern}.md"
    pattern_dst = target / f"LOOP_PATTERN_{pattern.upper().replace('-','_')}.md"
    if pattern_src.exists() and not pattern_dst.exists():
        shutil.copy2(pattern_src, pattern_dst)
        print(f"  pattern {pattern_dst.name}")

    print(f"\n✓ Scaffolded '{pattern}' into {target}")
    print(f"\nNext steps:")
    print(f"  1. cd {target}")
    print(f"  2. pip install openai schedule requests")
    print(f"  3. ollama pull llama3   (or set OPENAI_API_KEY)")
    print(f"  4. python loop_run.py --mode once   # test single cycle")
    print(f"  5. python tools/loop_audit.py . --suggest")
    print(f"\nRun report-only for one week before enabling auto-fix.")


def main():
    parser = argparse.ArgumentParser(description="Loop Engineering scaffold tool")
    parser.add_argument("target", help="Target project directory")
    parser.add_argument("--pattern", choices=list(PATTERNS),
                        default="daily-triage", help="Pattern to scaffold")
    args = parser.parse_args()

    scaffold(Path(args.target), args.pattern)


if __name__ == "__main__":
    main()
