from pathlib import Path
import pandas as pd
from scripts.run_cross_horizon_selector import HORIZONS, choose_horizon


def test_phase4_files_and_horizons():
    assert Path("scripts/run_cross_horizon_selector.py").exists()
    assert HORIZONS == ("2session", "3session", "5session", "10session")


def test_choose_horizon_uses_daily_cluster_mean():
    rows=[]
    for day in range(1,5):
        for h, value in zip(HORIZONS, (0.1,0.2,0.3,0.4)):
            rows.append({"side":"LONG","signal_day":pd.Timestamp(f"2020-01-{day:02d}"),"horizon":h,"return_R":value})
    chosen, scores=choose_horizon(pd.DataFrame(rows),"LONG")
    assert chosen=="10session"
    assert len(scores)==4
    assert scores.training_days.sum()==16
