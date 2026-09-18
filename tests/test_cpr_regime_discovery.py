import pandas as pd
import numpy as np

from scripts.run_cpr_regime_discovery import pareto_frontier, split_label


def test_chronological_split_is_fixed():
    assert split_label(pd.Timestamp("2018-12-31")) == "TRAIN"
    assert split_label(pd.Timestamp("2019-01-01")) == "VALIDATION"
    assert split_label(pd.Timestamp("2021-12-31")) == "VALIDATION"
    assert split_label(pd.Timestamp("2022-01-03")) == "TEST"


def test_pareto_frontier_removes_dominated_leaf():
    x=pd.DataFrame({
        "leaf":[1,2,3],
        "sensitivity":[0.80,0.70,0.90],
        "specificity":[0.80,0.90,0.70],
    })
    out=pareto_frontier(x)
    assert set(out.leaf)=={1,2,3}
