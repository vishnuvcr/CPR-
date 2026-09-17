from pathlib import Path


def test_swing_characterization_script_exists():
    assert Path('scripts/run_swing_characterization.py').exists()


def test_swing_workflow_exists():
    assert Path('.github/workflows/swing-characterization.yml').exists()
