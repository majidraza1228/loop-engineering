"""Basic smoke tests for loop_audit."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.loop_audit import score, level_for

def test_score_returns_int():
    total, passed, failed = score(Path("."))
    assert isinstance(total, int)
    assert 0 <= total <= 100

def test_level_for_low():
    label, level, _ = level_for(20)
    assert "L0" in level

def test_level_for_high():
    label, level, _ = level_for(90)
    assert "L2" in level or "L3" in level
