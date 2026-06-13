"""
tools/loop_audit.py — Loop Readiness Score CLI.

Scores your project directory on 0-100 and suggests what to add.

Usage:
  python tools/loop_audit.py .
  python tools/loop_audit.py /path/to/project --suggest
"""

import argparse
from pathlib import Path


CHECKS = [
    # (id, description, points, how_to_check)
    ("state_file",    "STATE.md exists",                     10, lambda p: (p / "STATE.md").exists()),
    ("loop_file",     "LOOP.md exists",                      10, lambda p: (p / "LOOP.md").exists()),
    ("agents_file",   "AGENTS.md exists",                     5, lambda p: (p / "AGENTS.md").exists()),
    ("engine",        "loop_engine.py present",              10, lambda p: (p / "loop_engine.py").exists()),
    ("run_script",    "A run.py or loop_run.py exists",       10,
     lambda p: any(p.glob("**/run.py")) or any(p.glob("**/loop_run.py"))),
    ("skills_dir",    ".skills/ directory exists",           10, lambda p: (p / ".skills").is_dir()),
    ("has_skills",    "At least one SKILL.md found",         10,
     lambda p: bool(list(p.glob(".skills/**/SKILL.md")))),
    ("git_repo",      "Is a git repository",                  5, lambda p: (p / ".git").is_dir()),
    ("gitignore",     ".gitignore present",                   5, lambda p: (p / ".gitignore").exists()),
    ("tests",         "tests/ directory exists",              5,
     lambda p: (p / "tests").is_dir() or (p / "test").is_dir()),
    ("requirements",  "requirements.txt or pyproject.toml",   5,
     lambda p: (p / "requirements.txt").exists() or (p / "pyproject.toml").exists()),
    ("ci_config",     "CI config present (.github/workflows or .gitlab-ci.yml)", 5,
     lambda p: (p / ".github" / "workflows").is_dir() or (p / ".gitlab-ci.yml").exists()),
    ("readme",        "README.md exists",                     5, lambda p: (p / "README.md").exists()),
    ("security",      "SECURITY.md exists",                   5, lambda p: (p / "SECURITY.md").exists()),
]

SUGGESTIONS = {
    "state_file":    "Create STATE.md — the memory spine of your loop. See templates/STATE.md.template",
    "loop_file":     "Create LOOP.md — describe which loops run on this repo and at what level (L1/L2/L3).",
    "agents_file":   "Create AGENTS.md — define maker, checker, triage agent system prompts.",
    "engine":        "Copy loop_engine.py from this repo into your project.",
    "run_script":    "Create a run.py starter. Use: python tools/loop_init.py . --pattern daily-triage",
    "skills_dir":    "Create .skills/ and add at least a loop-triage SKILL.md.",
    "has_skills":    "Add a SKILL.md to at least one .skills/<name>/ directory.",
    "git_repo":      "Initialise git: git init",
    "gitignore":     "Add a .gitignore. At minimum exclude __pycache__, .env, .ci_last_run.txt",
    "tests":         "Add a tests/ directory. Loops that fix code need tests to verify against.",
    "requirements":  "Add requirements.txt or pyproject.toml so the loop knows what's installed.",
    "ci_config":     "Add a GitHub Actions workflow. See examples/github-actions/daily-triage.yml",
    "readme":        "Add a README.md.",
    "security":      "Add SECURITY.md — describe what the loop is allowed to auto-merge vs escalate.",
}

LEVELS = {
    range(0,  40): ("Not ready", "L0", "No loop should run yet."),
    range(40, 60): ("Basic",     "L1", "Safe to run report-only (triage, changelog-drafter)."),
    range(60, 80): ("Good",      "L1-L2", "Ready for assisted loops with human PR approval."),
    range(80, 101):("Strong",    "L2-L3", "Ready for unattended loops on allowlisted paths."),
}


def score(project: Path) -> tuple[int, list[str], list[str]]:
    passed, failed = [], []
    total = 0
    for check_id, desc, points, check_fn in CHECKS:
        try:
            ok = check_fn(project)
        except Exception:
            ok = False
        if ok:
            passed.append((check_id, desc, points))
            total += points
        else:
            failed.append((check_id, desc, points))
    return total, passed, failed


def level_for(score: int) -> tuple[str, str, str]:
    for r, info in LEVELS.items():
        if score in r:
            return info
    return LEVELS[range(80, 101)]


def main():
    parser = argparse.ArgumentParser(description="Loop Readiness Audit")
    parser.add_argument("project", help="Project directory to audit")
    parser.add_argument("--suggest", action="store_true", help="Show improvement suggestions")
    args = parser.parse_args()

    project = Path(args.project).resolve()
    total, passed, failed = score(project)
    label, loop_level, note = level_for(total)

    print(f"\n── Loop Readiness Audit: {project.name} ──")
    print(f"   Score : {total}/100")
    print(f"   Level : {label} ({loop_level})")
    print(f"   Note  : {note}\n")

    print("✓ Passed:")
    for _, desc, pts in passed:
        print(f"  +{pts:>2}  {desc}")

    if failed:
        print("\n✗ Missing:")
        for _, desc, pts in failed:
            print(f"   {pts:>2}  {desc}")

    if args.suggest and failed:
        print("\n── Suggestions ──")
        for check_id, desc, _ in failed:
            suggestion = SUGGESTIONS.get(check_id, "")
            if suggestion:
                print(f"\n  {desc}:")
                print(f"    → {suggestion}")

    print()


if __name__ == "__main__":
    main()
