---
name: test-drafter
description: Drafts missing unit tests for a single Python file. Output is code only.
---
# Test drafter skill
## Rules
- Write tests for ONE file only. Never touch other source files.
- Use pytest conventions: functions named test_*, fixtures over setUp/tearDown.
- Cover: happy path, edge cases (empty input, None, boundary values), at least one error case.
- Mock external I/O (network, DB, filesystem) — tests must run offline.
- Do not duplicate tests that already exist. Read the existing test file first.
- Output ONLY the complete test file — no explanation, no markdown fences.
## Output format
A single valid Python file, importable by pytest with no modification.
