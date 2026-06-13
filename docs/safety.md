# Safety

Guidelines for running loops without causing damage.

---

## The Golden Rules

1. **Start L1 (report-only).** Never start a new loop in auto-fix mode.
2. **One loop per repo at first.** Multiple loops can conflict. Add the second after the first is stable.
3. **Human gate before merge.** Even at L3, security/auth/payments always require human review.
4. **Denylist first.** Define what the loop cannot touch before defining what it can.
5. **Cap concurrent PRs.** Never let the loop have more than 2–3 open PRs at once.

---

## Denylist (what loops must never touch)

Add these to your LOOP.md:

```
- src/auth/
- src/payments/
- infrastructure/
- .github/workflows/
- database/migrations/
- Any file containing secrets or credentials
```

---

## Allowlist (what loops may auto-fix at L3)

Safe to auto-merge with passing CI:

```
- tests/ (new tests only, no deletes)
- docs/ (*.md files)
- CHANGELOG.md (changelog-drafter output)
- requirements.txt (patch versions only)
- Stale branch deletion (agent/* branches only)
```

---

## MCP Connector Scopes

| Connector | Allowed | Blocked |
|---|---|---|
| GitHub | Read PRs/issues, open PRs, comment | Merge, delete main, manage secrets |
| Slack | Send to designated channel | DMs, @here, @channel |
| Linear | Read, add comment, change status | Delete, reassign to humans |

---

## Incident Response

If a loop does something unexpected:

1. Kill the scheduler immediately (`Ctrl+C` or disable the GitHub Action).
2. Close any open loop PRs (`agent/*` branches).
3. Review STATE.md for what the loop attempted.
4. Tighten the skill rules or denylist before restarting.
