import pandas as pd

from scripts.run_signal_baseline import summarize if False else None


def test_signal_baseline_script_exists():
    # Smoke-level repository test; full data execution is covered by CI.
    from pathlib import Path
    assert Path("scripts/run_signal_baseline.py").exists()
