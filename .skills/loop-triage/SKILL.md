---
name: loop-triage
description: Reads repo state and produces a prioritised task list. Never writes code.
---
# Triage skill
## What to look for
1. Files with TODO/FIXME added in the last 7 days
2. Functions > 50 lines (complexity risk)
3. Missing tests for recently added files
4. CI failures (check the run log)
## Output format
Return ONLY a markdown list, max 8 items:
- [ ] {description} — priority: high/med/low
## Rules
- Skip auto-generated files (src/generated/, dist/, build/)
- Flag security issues as high regardless of size
- Do not propose architectural changes
