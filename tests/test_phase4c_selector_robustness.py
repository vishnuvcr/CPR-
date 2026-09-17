from pathlib import Path

import pandas as pd

from scripts.run_phase4c_selector_robustness import actual_mapping, daily_mean, outcome_for_mapping


HORIZONS = ("2session", "3session", "5session", "10session")


def test_daily_mean_averages_daily_means_not_all_rows():
    df = pd.DataFrame({"signal_day": ["2026-01-01", "2026-01-01", "2026-01-02"], "r": [1.0, 3.0, 5.0]})
    assert daily_mean(df, "r") == 3.5


def test_actual_mapping_uses_selected_horizon():
    s = pd.DataFrame({
        "split": [1, 2],
        "side": ["LONG", "SHORT"],
        "entry_bucket": ["09:15-10:00", "14:01+"],
        "selected_horizon": ["2session", "10session"],
    })
    m = actual_mapping(s)
    assert list(m.mapped_horizon) == ["2session", "10session"]


def test_outcome_mapping_resolves_one_candidate_per_signal():
    selected = pd.DataFrame({
        "split": [1],
        "signal_time": pd.to_datetime(["2026-01-01 10:00"]),
        "side": ["LONG"],
        "entry_bucket": ["09:15-10:00"],
        "signal_day": pd.to_datetime(["2026-01-01"]),
    })
    events = pd.DataFrame({
        "signal_time": pd.to_datetime(["2026-01-01 10:00"] * 4),
        "side": ["LONG"] * 4,
        "entry_bucket": ["09:15-10:00"] * 4,
        "horizon": list(HORIZONS),
        "return_R": [1.0, 2.0, 3.0, 4.0],
    })
    mapping = pd.DataFrame({
        "split": [1], "side": ["LONG"], "entry_bucket": ["09:15-10:00"], "mapped_horizon": ["5session"]
    })
    q = outcome_for_mapping(selected, events, mapping)
    assert len(q) == 1
    assert q.iloc[0].mapped_R == 3.0


def test_script_exists():
    assert Path("scripts/run_phase4c_selector_robustness.py").exists()
