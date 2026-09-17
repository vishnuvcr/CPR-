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
    """Create chronological folds on the supplied period index.

    For intraday data, pass a DAILY index so 252/63 means trading days rather
    than 5-minute bars. The returned timestamps are then used to slice the
    higher-frequency dataframe.
    """
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
    fold_index: pd.DatetimeIndex | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Select parameters on each train fold and freeze them on the next test fold.

    ``fold_index`` controls the unit of time used by the WFO schedule. This is
    essential for intraday datasets: use the daily index for a 252/63/63
    trading-day protocol while retaining the original intraday bars for
    strategy evaluation.
    """
    schedule_index = fold_index if fold_index is not None else data.index
    folds = []
    test_frames = []
    for f in make_folds(schedule_index, train_periods, test_periods, step):
        train = data.loc[f["train"][0] : f["train"][1]]
        test = data.loc[f["test"][0] : f["test"][1]]
        scores = [(params, evaluator(train, params)) for params in parameter_grid]
        params, score = max(scores, key=lambda x: x[1])
        folds.append(WFOFold(f["train"][0], f["train"][1], f["test"][0], f["test"][1], params, float(score)))
        test_frames.append(test.assign(**{f"param_{k}": v for k, v in params.items()}))
    fold_df = pd.DataFrame([x.__dict__ for x in folds])
    stitched = pd.concat(test_frames) if test_frames else pd.DataFrame(index=data.index[:0])
    return fold_df, stitched
