---
name: coverage-reader
description: Parses pytest --cov output, compares to prior run, surfaces files where coverage dropped.
---
# Coverage reader skill
## What to look for
1. Files where coverage dropped more than 5 percentage points vs the prior run
2. Files below the project threshold (default: 60%) that weren't there before
3. New files added in the last 7 days with no test file counterpart
## Output format
Return ONLY a markdown list, max 8 items:
- [ ] {file_path} — {current}% (was {prior}%) — priority: high/med/low
## Rules
- Skip auto-generated files (migrations/, dist/, build/, *_pb2.py)
- Skip __init__.py files — they are not meaningfully testable
- Flag auth, payments, security modules as high regardless of drop size
- Do not propose architectural changes or refactors
- If no prior baseline exists, report all files below threshold as med priority
