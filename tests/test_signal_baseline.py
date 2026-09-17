from pathlib import Path


def test_signal_baseline_script_exists():
    assert Path("scripts/run_signal_baseline.py").exists()
