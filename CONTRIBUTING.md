# Contributing

Contributions welcome — especially production patterns, failure stories, and new starters.

## What to contribute

- **New patterns**: Copy `templates/pattern-template.md`, add to `patterns/registry.yaml`, add a starter in `starters/`.
- **Failure stories**: Add to `docs/failure-modes.md` in incident style.
- **New skills**: Add to `skills/` with a `SKILL.md`.
- **Bug fixes**: Open a PR with a clear description of what broke and what you changed.

## Process

1. Fork the repo.
2. Create a branch: `git checkout -b your-feature`.
3. Run `python scripts/validate_patterns.py` before pushing.
4. Run `python tools/loop_audit.py . --suggest` and address anything easy.
5. Open a PR with a description of what you added and why.

## Principles

- Patterns should be runnable, not just documented.
- Every pattern needs a starter with a `run.py`.
- Failure stories are as valuable as success stories.
- When in doubt, err toward more caution (L1 over L3).
