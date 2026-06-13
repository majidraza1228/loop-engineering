# Security Policy

## Unattended Automation Risks

Loops run code without a human in the loop. Before enabling auto-fix (L2/L3):

1. **Define a denylist** in LOOP.md — paths the loop must never touch.
2. **Cap concurrent PRs** — never more than 2–3 open `agent/*` PRs at once.
3. **Test in a fork first** — run the loop on a fork before your production repo.
4. **Never store secrets in STATE.md or skill files** — they may be committed.

## Reporting a Vulnerability

If you find a security issue in this repo, open a GitHub issue marked `[SECURITY]`.
Do not include exploit details in the public issue — send those privately.

## What Loops Should Never Do

Regardless of level or config:

- Auto-merge changes to auth, payments, or infrastructure
- Add or rotate secrets
- Change CI/CD pipeline definitions
- Delete branches that aren't `agent/*`
- Send messages on behalf of a human
