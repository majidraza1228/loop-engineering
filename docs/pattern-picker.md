# Pattern Picker

Answer the questions to find your starting pattern.

---

**Q1: Have you run a loop on this repo before?**

- No → Start with **Daily Triage** (lowest risk, report-only)
- Yes, report-only → Consider **Changelog Drafter** or **Post-Merge Cleanup**
- Yes, with auto-fix → Consider **CI Sweeper** or **Dependency Sweeper**

---

**Q2: What's the most painful manual task?**

| Pain point | Pattern |
|---|---|
| "I don't know what's broken until someone tells me" | Daily Triage |
| "PRs sit open for days" | PR Babysitter |
| "CI goes red and nobody notices" | CI Sweeper |
| "Writing CHANGELOGs is tedious" | Changelog Drafter |
| "Deps are always outdated" | Dependency Sweeper |
| "Stale branches and closed issues everywhere" | Post-Merge Cleanup |

---

**Q3: How much do you trust automated fixes right now?**

- Not at all → **L1 only** (Daily Triage, Changelog Drafter)
- For small obvious fixes → **L2** (CI Sweeper, Dependency Sweeper)
- For well-tested, scoped changes → **L3** (narrow allowlist only)

---

**Recommendation for first-time loop engineers**:

1. Start with **Daily Triage** in report-only mode.
2. After one week, check: does STATE.md match what you'd have found manually?
3. If yes, add **Changelog Drafter** (zero risk — always a draft).
4. Then consider **CI Sweeper** with a strict allowlist.

Run `python tools/loop_audit.py . --suggest` before starting any loop.
