# Failure Modes

Incident-style catalog of common loop failures and mitigations.

---

## FM-01: State file grows unbounded

**Symptom**: STATE.md becomes hundreds of lines; triage quality degrades as context fills with old items.  
**Cause**: Loop appends but never prunes resolved items.  
**Fix**: Add a pruning step at the start of each cycle — remove items where the linked issue/PR is closed.

---

## FM-02: Triage invents architectural work

**Symptom**: Loop adds tasks like "refactor the entire auth module" to STATE.md.  
**Cause**: Triage skill too permissive; no scope boundary.  
**Fix**: Add to the triage skill: "Do not propose architectural changes. Signal only. Max 8 items."

---

## FM-03: Checker is too lenient

**Symptom**: Checker always returns `pass`; code quality doesn't improve.  
**Cause**: Checker uses the same model/temperature as maker; gets anchored on the maker's output.  
**Fix**: Use a higher temperature on the checker. Add explicit skepticism instructions: "Be critical. Assume the code has at least one bug."

---

## FM-04: Worktree collision

**Symptom**: Two agents create the same branch name; one silently fails.  
**Cause**: Branch name generation not unique enough.  
**Fix**: Append a Unix timestamp to every branch name: `agent/fix-auth-1717920000`.

---

## FM-05: Token cost spike

**Symptom**: Monthly LLM bill 10× what you expected.  
**Cause**: Sub-agents + long STATE.md + high cadence = many large prompts.  
**Fix**: Add `max_runs_per_day` guard. Prune STATE.md. Run sub-agents only for high-priority items.

---

## FM-06: Loop opens PRs faster than humans can review

**Symptom**: 10+ open `agent/*` PRs; team starts ignoring them.  
**Cause**: No concurrency limit.  
**Fix**: Before opening a new PR, check how many `agent/*` PRs are already open. Block if ≥ 3.

---

## FM-07: Comprehension debt accumulates

**Symptom**: The loop ships code you don't understand; bugs slip through review.  
**Cause**: Loop is moving faster than your reading speed.  
**Fix**: Slow the cadence. Set a personal rule: "I read every diff before it merges."

---

## FM-08: Flaky tests trigger unnecessary CI sweeper runs

**Symptom**: CI sweeper fires repeatedly on a test that fails 2/10 runs.  
**Cause**: No flaky-test denylist.  
**Fix**: Add a "Known flaky — skip" list to the ci-reader skill. Only fix tests that fail 8+/10 runs.
