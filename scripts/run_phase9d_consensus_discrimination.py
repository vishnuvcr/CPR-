"""Phase 9D: fixed consensus directional discrimination validation.

Uses the frozen Phase 9B consensus taxonomy and the frozen Phase 5A frontier.
The prediction is pre-defined: for a native horizon/side event, a LONG
consensus state predicts a positive LONG return and a SHORT consensus state
predicts a positive SHORT return. NO_SIGNAL and CONFLICT are treated as
negative predictions. The binary outcome is realized_return_R > 0.

The eligible population is the complete set of base CPR directional events
for each native horizon/side, not only candidate activations. No thresholds,
states, horizons, or outcomes are fitted or selected in this phase.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import numpy as np
import pandas as pd

from cpr_lab.data_quality import load_ohlcv_csv
from cpr_lab.indicators import add_intraday_daily_features, daily_reference_features
from run_cpr_regime_discovery import build_intraday_events, build_swing_events, make_context
from run_phase9_shadow_engine import matches

FRONTIER_SHA256 = "601a72f5e64204aee7ff0bb77347d57b0e2b59871b8bc30011282c2dc02c28b2"
HORIZONS = {
    "intraday": ("1bar", "3bar", "6bar", "12bar", "EOD"),
    "swing": ("2session", "3session", "5session", "10session"),
}
STATES = ("NO_SIGNAL", "SINGLE_LONG", "MULTIPLE_LONG_2_3", "MULTIPLE_LONG_4_PLUS",
          "SINGLE_SHORT", "MULTIPLE_SHORT_2_3", "MULTIPLE_SHORT_4_PLUS", "CONFLICT")


def consensus_state(long_n: int, short_n: int) -> str:
    if long_n == 0 and short_n == 0:
        return "NO_SIGNAL"
    if long_n and short_n:
        return "CONFLICT"
    n = max(long_n, short_n)
    side = "LONG" if long_n else "SHORT"
    if n == 1:
        return f"SINGLE_{side}"
    if n <= 3:
        return f"MULTIPLE_{side}_2_3"
    return f"MULTIPLE_{side}_4_PLUS"


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return np.nan, np.nan
    p = k / n
    den = 1 + z*z/n
    centre = (p + z*z/(2*n)) / den
    half = z*np.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return max(0.0, centre-half), min(1.0, centre+half)


def classification_metrics(pred: np.ndarray, y: np.ndarray) -> dict:
    pred = np.asarray(pred, dtype=bool)
    y = np.asarray(y, dtype=bool)
    tp = int(np.sum(pred & y)); fp = int(np.sum(pred & ~y))
    fn = int(np.sum(~pred & y)); tn = int(np.sum(~pred & ~y))
    sens = tp/(tp+fn) if tp+fn else np.nan
    spec = tn/(tn+fp) if tn+fp else np.nan
    ppv = tp/(tp+fp) if tp+fp else np.nan
    npv = tn/(tn+fn) if tn+fn else np.nan
    bal = (sens+spec)/2 if np.isfinite(sens) and np.isfinite(spec) else np.nan
    j = sens+spec-1 if np.isfinite(sens) and np.isfinite(spec) else np.nan
    sens_lo,sens_hi=wilson(tp,tp+fn)
    spec_lo,spec_hi=wilson(tn,tn+fp)
    ppv_lo,ppv_hi=wilson(tp,tp+fp)
    npv_lo,npv_hi=wilson(tn,tn+fn)
    return dict(observations=len(y), positives=int(y.sum()), prevalence=float(y.mean()) if len(y) else np.nan,
                predicted_positive=int(pred.sum()), tp=tp,fp=fp,fn=fn,tn=tn,
                sensitivity=sens,sensitivity_ci95_low=sens_lo,sensitivity_ci95_high=sens_hi,
                specificity=spec,specificity_ci95_low=spec_lo,specificity_ci95_high=spec_hi,
                ppv=ppv,ppv_ci95_low=ppv_lo,ppv_ci95_high=ppv_hi,
                npv=npv,npv_ci95_low=npv_lo,npv_ci95_high=npv_hi,
                balanced_accuracy=bal,youden_J=j)


def build_population(bars: pd.DataFrame, frontier: pd.DataFrame) -> pd.DataFrame:
    daily=bars.resample("1D").agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
    x=add_intraday_daily_features(bars,daily_reference_features(daily))
    ctx=make_context(bars).reindex(x.index)
    events={"intraday":build_intraday_events(x,ctx),"swing":build_swing_events(x,ctx)}
    rows=[]
    for asset,ev in events.items():
        if ev.empty: continue
        # State is defined from every frozen candidate activated at this timestamp,
        # across all horizons; then evaluated against the event's native horizon.
        for ts, g in ev.groupby("signal_time"):
            c=ctx.loc[ts]
            if c.isna().any(): continue
            activated=[]
            for _,cand in frontier.iterrows():
                if cand.asset != asset: continue
                if matches(c, cand.rule):
                    activated.append(cand)
            longs=sum(1 for cnd in activated if cnd.side=="LONG")
            shorts=sum(1 for cnd in activated if cnd.side=="SHORT")
            st=consensus_state(longs,shorts)
            for _,e in g.iterrows():
                rows.append({
                    "signal_time":ts,"signal_day":pd.Timestamp(ts).normalize(),
                    "asset":asset,"horizon":e.horizon,"side":e.side,
                    "realized_return_R":float(e.return_R),"state":st,
                    "prediction_positive":bool((e.side=="LONG" and st in {"SINGLE_LONG","MULTIPLE_LONG_2_3","MULTIPLE_LONG_4_PLUS"}) or
                                               (e.side=="SHORT" and st in {"SINGLE_SHORT","MULTIPLE_SHORT_2_3","MULTIPLE_SHORT_4_PLUS"})),
                })
    return pd.DataFrame(rows)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--p7",required=True); ap.add_argument("--p8",required=True)
    ap.add_argument("--frontier",required=True); ap.add_argument("--output-dir",required=True)
    a=ap.parse_args(); out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True)
    frontier=pd.read_csv(a.frontier)
    if len(frontier)!=39: raise ValueError(f"Expected 39 frozen candidates, found {len(frontier)}")
    for label,path in [("PHASE7_INDEPENDENT",a.p7),("PHASE8_UNTOUCHED_2026",a.p8)]:
        bars=load_ohlcv_csv(path)
        pop=build_population(bars,frontier)
        pop["dataset"]=label
        pop.to_csv(out/f"phase9d_{label.lower()}_population.csv",index=False)
        rows=[]
        for (asset,horizon,side),q in pop.groupby(["asset","horizon","side"]):
            m=classification_metrics(q.prediction_positive.to_numpy(),(q.realized_return_R>0).to_numpy())
            rows.append({"dataset":label,"asset":asset,"horizon":horizon,"side":side,"prediction_definition":"matching-side consensus state","outcome_definition":"realized_return_R > 0",**m})
        for (asset,horizon,side,state),q in pop.groupby(["asset","horizon","side","state"]):
            m=classification_metrics(np.ones(len(q),dtype=bool),(q.realized_return_R>0).to_numpy())
            rows.append({"dataset":label,"asset":asset,"horizon":horizon,"side":side,"prediction_definition":f"state={state} (one-vs-rest positive event rate)","outcome_definition":"realized_return_R > 0",**m})
        pd.DataFrame(rows).to_csv(out/f"phase9d_{label.lower()}_metrics.csv",index=False)
    a7=pd.read_csv(out/"phase9d_phase7_independent_metrics.csv")
    a8=pd.read_csv(out/"phase9d_phase8_untouched_2026_metrics.csv")
    overall=pd.concat([a7,a8],ignore_index=True)
    overall.to_csv(out/"phase9d_metrics_all.csv",index=False)
    # Cross-dataset comparison is descriptive only; no selection.
    d=overall[overall.prediction_definition=="matching-side consensus state"].copy()
    wide=d.pivot_table(index=["asset","horizon","side"],columns="dataset",values=["sensitivity","specificity","youden_J"])
    wide.to_csv(out/"phase9d_cross_dataset_metrics.csv")
    pd.DataFrame([{
        "protocol":"Fixed Phase 9B taxonomy; frozen Phase 5A frontier.",
        "prediction":"For each native horizon/side event, matching-side consensus state is a positive prediction; NO_SIGNAL, CONFLICT and opposite-side states are negative.",
        "outcome":"realized_return_R > 0",
        "eligible_population":"All frozen-base CPR directional events at the native horizon/side, including timestamps with no candidate activation.",
        "selection":"NONE",
        "threshold_refitting":"NONE",
        "2026_holdout_role":"Untouched forward evaluation; no rule selection or parameter changes."
    }]).to_csv(out/"phase9d_provenance.csv",index=False)
    print("=== PHASE 9D ===")
    print(d[["dataset","asset","horizon","side","observations","prevalence","predicted_positive","sensitivity","specificity","youden_J"]].to_string(index=False))


if __name__=="__main__": main()
