---
name: ci-reader
description: Parses CI output and identifies the most likely failure cause.
---
# CI reader skill
## Output format
Return JSON:
{
  "failing_tests": ["test_name"],
  "likely_cause": "one sentence",
  "file": "path/to/file.py",
  "line_hint": 42,
  "confidence": "high|medium|low"
}
