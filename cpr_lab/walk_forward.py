"""Walk-forward optimization utilities."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Callable, Iterable
import pandas as pd


@dataclass(frozen=True)
class WFOFold:
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    params: dict
    train_score: float


def make_folds(index: pd.DatetimeIndex, train_periods: int = 252, test_periods: int = 63, step: int = 63):
    idx = pd.DatetimeIndex(index).sort_values().unique()
    i = train_periods
    while i + test_periods <= len(idx):
        yield {
            "train": (idx[i - train_periods], idx[i - 1]),
            "test": (idx[i], idx[i + test_periods - 1]),
        }
        i += step


def grid(params: dict[str, Iterable]) -> list[dict]:
    keys = list(params)
    return [dict(zip(keys, vals)) for vals in product(*[params[k] for k in keys])]


def optimize_wfo(
    data: pd.DataFrame,
    parameter_grid: list[dict],
    evaluator: Callable[[pd.DataFrame, dict], float],
    train_periods: int = 252,
    test_periods: int = 63,
    step: int = 63,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Select parameters on each train fold and freeze them on the subsequent test fold."""
    folds = []
    test_frames = []
    for f in make_folds(data.index, train_periods, test_periods, step):
        train = data.loc[f["train"][0] : f["train"][1]]
        test = data.loc[f["test"][0] : f["test"][1]]
        scores = [(params, evaluator(train, params)) for params in parameter_grid]
        params, score = max(scores, key=lambda x: x[1])
        folds.append(WFOFold(f["train"][0], f["train"][1], f["test"][0], f["test"][1], params, float(score)))
        test_frames.append(test.assign(**{f"param_{k}": v for k, v in params.items()}))
    fold_df = pd.DataFrame([x.__dict__ for x in folds])
    stitched = pd.concat(test_frames) if test_frames else pd.DataFrame(index=data.index[:0])
    return fold_df, stitched
