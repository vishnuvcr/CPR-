"""Statistical tear-sheet utilities."""
from __future__ import annotations

import numpy as np
import pandas as pd


def trade_metrics(returns: pd.Series, equity: pd.Series | None = None, periods_per_year: int = 252) -> dict[str, float]:
    r = pd.Series(returns).dropna().astype(float)
    if r.empty:
        return {}
    wins = r[r > 0]
    losses = r[r < 0]
    win_rate = float((r > 0).mean())
    avg_win = float(wins.mean()) if not wins.empty else 0.0
    avg_loss = float(-losses.mean()) if not losses.empty else 0.0
    expectancy = win_rate * avg_win - (1 - win_rate) * avg_loss
    profit_factor = float(wins.sum() / abs(losses.sum())) if not losses.empty and losses.sum() != 0 else np.inf
    sharpe = float(r.mean() / r.std(ddof=1) * np.sqrt(periods_per_year)) if r.std(ddof=1) else np.nan
    downside = r.clip(upper=0).std(ddof=1)
    sortino = float(r.mean() / downside * np.sqrt(periods_per_year)) if downside and downside > 0 else np.nan

    out = {
        "trade_count": float(len(r)),
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "expectancy": float(expectancy),
        "payoff_ratio": float(avg_win / avg_loss) if avg_loss else np.inf,
        "profit_factor": profit_factor,
        "sharpe": sharpe,
        "sortino": sortino,
    }

    if equity is not None:
        eq = pd.Series(equity).dropna().astype(float)
        peak = eq.cummax()
        dd = eq / peak - 1.0
        max_dd = float(dd.min())
        out["max_drawdown"] = max_dd
        duration = (dd < 0).astype(int)
        groups = duration.eq(0).cumsum()
        out["max_drawdown_duration_periods"] = float(duration.groupby(groups).sum().max()) if not duration.empty else 0.0
        years = len(eq) / periods_per_year
        cagr = float((eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1) if years > 0 and eq.iloc[0] > 0 else np.nan
        out["cagr"] = cagr
        out["calmar"] = float(cagr / abs(max_dd)) if max_dd < 0 and np.isfinite(cagr) else np.nan
    return out


def tear_sheet_frame(strategy_returns: dict[str, pd.Series], equities: dict[str, pd.Series]) -> pd.DataFrame:
    rows = []
    for name, r in strategy_returns.items():
        row = {"strategy": name}
        row.update(trade_metrics(r, equities.get(name)))
        rows.append(row)
    return pd.DataFrame(rows).set_index("strategy")
