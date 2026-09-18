"""Evaluate all frozen Phase 5A candidates on untouched 2026 forward windows."""
from __future__ import annotations
import argparse,re
from pathlib import Path
import numpy as np,pandas as pd
from cpr_lab.data_quality import load_ohlcv_csv
from cpr_lab.indicators import add_intraday_daily_features,daily_reference_features
from run_cpr_regime_discovery import make_context,build_intraday_events,build_swing_events

PAT=re.compile(r"^([A-Za-z0-9_]+)\s*(<=|>)\s*(-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)$")
WINDOWS=[("2026Q1","2026-01-01","2026-03-31"),("2026Q2","2026-04-01","2026-06-30"),("2026Q3_partial","2026-07-01","2026-09-30")]

def parse(rule):
    if rule=="ALL": return []
    out=[]
    for c in rule.split(" AND "):
        m=PAT.match(c.strip())
        if not m: raise ValueError(f"Cannot parse rule: {c}")
        out.append((m.group(1),m.group(2),float(m.group(3))))
    return out
def mask(df,rule):
    m=np.ones(len(df),bool)
    for col,op,v in parse(rule):
        m &= df[col].to_numpy(float)<=v if op=="<=" else df[col].to_numpy(float)>v
    return pd.Series(m,index=df.index)
def metrics(pop,sel):
    y=pop.return_R.to_numpy(float)>0; p=pop.index.isin(sel.index)
    tp=np.sum(p&y);fp=np.sum(p&~y);fn=np.sum(~p&y);tn=np.sum(~p&~y)
    se=tp/(tp+fn) if tp+fn else np.nan;sp=tn/(tn+fp) if tn+fp else np.nan
    return se,sp,se+sp-1 if np.isfinite(se+sp) else np.nan

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--input",required=True);ap.add_argument("--frontier",required=True);ap.add_argument("--output-dir",required=True)
    a=ap.parse_args(); out=Path(a.output_dir);out.mkdir(parents=True,exist_ok=True)
    frontier=pd.read_csv(a.frontier)
    if len(frontier)!=39: raise ValueError(f"Expected 39 frozen candidates, found {len(frontier)}")
    bars=load_ohlcv_csv(a.input)
    daily=bars.resample("1D").agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
    x=add_intraday_daily_features(bars,daily_reference_features(daily));ctx=make_context(bars).reindex(x.index)
    events={"intraday":build_intraday_events(x,ctx),"swing":build_swing_events(x,ctx)}
    rows=[]
    for cid,c in frontier.reset_index(drop=True).iterrows():
        e=events[c.asset]; z=e[(e.horizon==c.horizon)&(e.side==c.side)].dropna(subset=["return_R"]).copy()
        for wn,ws,we in WINDOWS:
            sdate=pd.Timestamp(ws,tz="Asia/Kolkata"); edate=pd.Timestamp(we,tz="Asia/Kolkata")+pd.Timedelta(days=1)
            q=z[(z.signal_day>=sdate)&(z.signal_day<edate)];s=q[mask(q,c.rule)]
            se,sp,j=metrics(q,s)
            rows.append({"candidate_id":cid,"asset":c.asset,"horizon":c.horizon,"side":c.side,"window":wn,"window_start":ws,"window_end":we,
                         "population":len(q),"signals":len(s),"signal_days":s.signal_day.nunique(),
                         "mean_R":s.return_R.mean() if len(s) else np.nan,"median_R":s.return_R.median() if len(s) else np.nan,
                         "sensitivity":se,"specificity":sp,"youden_J":j})
    df=pd.DataFrame(rows)
    # Cumulative untouched holdout summaries: Q1; H1; Q1-Q3.
    cum=[]
    for cid,c in frontier.reset_index(drop=True).iterrows():
        e=events[c.asset];z=e[(e.horizon==c.horizon)&(e.side==c.side)].dropna(subset=["return_R"])
        for wn,we in [("2026Q1","2026-03-31"),("2026H1","2026-06-30"),("2026YTD_Q3","2026-09-30")]:
            q=z[z.signal_day < pd.Timestamp(we,tz="Asia/Kolkata")+pd.Timedelta(days=1)];q=q[q.signal_day>=pd.Timestamp("2026-01-01",tz="Asia/Kolkata")]
            s=q[mask(q,c.rule)];se,sp,j=metrics(q,s)
            cum.append({"candidate_id":cid,"asset":c.asset,"horizon":c.horizon,"side":c.side,"window":wn,"population":len(q),"signals":len(s),
                        "mean_R":s.return_R.mean() if len(s) else np.nan,"sensitivity":se,"specificity":sp,"youden_J":j})
    df.to_csv(out/"phase8_window_results.csv",index=False);pd.DataFrame(cum).to_csv(out/"phase8_cumulative_results.csv",index=False)
    pd.DataFrame([{"candidate_count":len(frontier),"windows":",".join(w[0] for w in WINDOWS),
                   "method":"Frozen rules only; no fitting, threshold adjustment, ranking or selection on 2026 holdout.",
                   "source":"ganeshbiyer/Nse_Historical_Data_2026","source_commit":"e8f19f3f53ca6fac0b116e83508e814e568dca54"}]).to_csv(out/"phase8_provenance.csv",index=False)
    print("=== PHASE 8 FINAL UNTOUCHED FORWARD HOLDOUT ===");print(df.to_string(index=False));print("Frozen candidates evaluated:",len(frontier))
if __name__=="__main__":main()
