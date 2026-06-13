"""
scripts/validate_patterns.py

Checks that every pattern in patterns/registry.yaml has:
  - A matching .md file in patterns/
  - A matching starter directory in starters/
  - At least a run.py in that starter directory

Run: python scripts/validate_patterns.py
Used by: .github/workflows/validate-patterns.yml
"""

import sys
from pathlib import Path

try:
    import yaml
    def load_yaml(path):
        with open(path) as f:
            return yaml.safe_load(f)
except ImportError:
    import json
    def load_yaml(path):
        # fallback: parse the simple registry.yaml manually
        data = {"patterns": []}
        with open(path) as f:
            current = {}
            for line in f:
                line = line.rstrip()
                if line.startswith("  - name:"):
                    if current:
                        data["patterns"].append(current)
                    current = {"name": line.split(":", 1)[1].strip()}
                elif line.startswith("    ") and ":" in line:
                    k, v = line.strip().split(":", 1)
                    current[k.strip()] = v.strip()
            if current:
                data["patterns"].append(current)
        return data

ROOT = Path(__file__).parent.parent
REGISTRY = ROOT / "patterns" / "registry.yaml"

errors = []

data = load_yaml(REGISTRY)
for p in data.get("patterns", []):
    name = p["name"]

    # check .md file
    md_path = ROOT / p.get("file", f"patterns/{name}.md")
    if not md_path.exists():
        errors.append(f"MISSING pattern doc: {md_path.relative_to(ROOT)}")

    # check starter dir
    starter = ROOT / p.get("starter", f"starters/{name}")
    if not starter.is_dir():
        errors.append(f"MISSING starter dir: {starter.relative_to(ROOT)}")
    elif not (starter / "run.py").exists():
        errors.append(f"MISSING run.py in starter: {starter.relative_to(ROOT)}/run.py")

if errors:
    print("Pattern validation FAILED:")
    for e in errors:
        print(f"  ✗ {e}")
    sys.exit(1)
else:
    n = len(data.get("patterns", []))
    print(f"✓ All {n} patterns validated.")
