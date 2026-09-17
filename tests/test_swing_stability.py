from pathlib import Path


def test_swing_stability_script_exists():
    assert Path('scripts/run_swing_stability.py').exists()


def test_swing_stability_workflow_exists():
    assert Path('.github/workflows/swing-stability.yml').exists()
