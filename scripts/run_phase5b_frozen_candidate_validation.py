"""Phase 5B: frozen-candidate validation for conditional CPR regimes.

No new thresholds are fitted here. The exact TRAIN-Pareto leaves from Phase 5A
are frozen and tested for uncertainty, yearly stability, and adjacent-horizon
consistency.
"""
from __future__ import annotations
import argparse, re
from pathlib import Path
import numpy as np
import pandas as pd
from math import sqrt

HORIZONS={"intraday":("1bar","3bar","6bar","12bar","EOD"),
          "swing":("2session","3session","5session","10session")}
SPLITS=("TRAIN","VALIDATION","TEST")
SEED=20260918
BOOTSTRAPS=5000
MIN_YEAR_SIGNALS=50

def parse_rule(rule):
    if not rule or rule=="ALL": return []
    pat=re.compile(r"^([A-Za-z0-9_]+)\s*(<=|>)\s*(-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)$")
    out=[]
    for clause in rule.split(" AND "):
        m=pat.match(clause.strip())
        if not m: raise ValueError(f"Cannot parse frozen rule clause: {clause!r}")
        out.append((m.group(1),m.group(2),float(m.group(3))))
    return out

def rule_mask(df,rule):
    m=pd.Series(True,index=df.index)
    for col,op,v in parse_rule(rule):
        if col not in df: raise KeyError(col)
        m &= df[col] <= v if op=="<=" else df[col] > v
    return m

def metrics(pop,sel):
    y=(pop.return_R.to_numpy()>0)
    p=pop.index.isin(sel.index)
    tp=np.sum(p&y); fp=np.sum(p&~y); fn=np.sum(~p&y); tn=np.sum(~p&~y)
    se=tp/(tp+fn) if tp+fn else np.nan
    sp=tn/(tn+fp) if tn+fp else np.nan
    return se,sp,se+sp-1 if np.isfinite(se+sp) else np.nan

def mean_ci(sel,rng,n=BOOTSTRAPS,block=10):
    # Bootstrap the same event-level mean_R reported by split_row while
    # preserving within-day dependence via contiguous signal-day blocks.
    groups=[g.return_R.to_numpy() for _,g in sel.groupby("signal_day",sort=True)]
    nd=len(groups)
    if nd<2: return np.nan,np.nan
    blocks=[groups[i:i+block] for i in range(0,nd,block)]
    nb=int(np.ceil(nd/block)); sims=np.empty(n)
    for i in range(n):
        chosen=rng.integers(0,len(blocks),nb)
        sampled_days=[day for j in chosen for day in blocks[j]]
        sampled_days=sampled_days[:nd]
        vals=np.concatenate(sampled_days)
        sims[i]=vals.mean()
    return np.quantile(sims,[.025,.975])

def wilson_interval(successes, trials, z=1.959963984540054):
    if trials <= 0:
        return np.nan, np.nan
    p=successes/trials
    den=1+z*z/trials
    centre=(p+z*z/(2*trials))/den
    half=z*sqrt(p*(1-p)/trials+z*z/(4*trials*trials))/den
    return max(0.0,centre-half), min(1.0,centre+half)

def confusion_ci(pop,sel,rng,n=BOOTSTRAPS):
    # Fast analytic uncertainty intervals avoid repeated pandas resampling.
    # Youden bounds use conservative component-wise Wilson limits.
    y=pop.return_R.to_numpy()>0
    p=pop.index.isin(sel.index)
    tp=int(np.sum(p&y)); fp=int(np.sum(p&~y)); fn=int(np.sum(~p&y)); tn=int(np.sum(~p&~y))
    se_lo,se_hi=wilson_interval(tp,tp+fn)
    sp_lo,sp_hi=wilson_interval(tn,tn+fp)
    return se_lo,se_hi,sp_lo,sp_hi,se_lo+sp_lo-1 if np.isfinite(se_lo+sp_lo) else np.nan,se_hi+sp_hi-1 if np.isfinite(se_hi+sp_hi) else np.nan

def split_row(pop,sel,split,rng):
    q=pop[pop.split==split]; s=sel[sel.split==split]
    if q.empty:
        return dict(split=split,population=0,signals=0,mean_R=np.nan,win_rate=np.nan,
                    sensitivity=np.nan,specificity=np.nan,youden_J=np.nan,
                    mean_ci95_low=np.nan,mean_ci95_high=np.nan,
                    sensitivity_ci95_low=np.nan,sensitivity_ci95_high=np.nan,
                    specificity_ci95_low=np.nan,specificity_ci95_high=np.nan,
                    youden_ci95_low=np.nan,youden_ci95_high=np.nan)
    se,sp,j=metrics(q,s)
    lo,hi=mean_ci(s,rng); ci=confusion_ci(q,s,rng)
    return dict(split=split,population=len(q),signals=len(s),
                mean_R=s.return_R.mean() if len(s) else np.nan,
                win_rate=(s.return_R>0).mean() if len(s) else np.nan,
                sensitivity=se,specificity=sp,youden_J=j,
                mean_ci95_low=lo,mean_ci95_high=hi,
                sensitivity_ci95_low=ci[0],sensitivity_ci95_high=ci[1],
                specificity_ci95_low=ci[2],specificity_ci95_high=ci[3],
                youden_ci95_low=ci[4],youden_ci95_high=ci[5])

def add_split(df):
    y=df.signal_day.dt.year
    df=df.copy()
    df["split"]=np.where(y<=2018,"TRAIN",np.where(y<=2021,"VALIDATION","TEST"))
    return df

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--intraday-events",required=True); p.add_argument("--swing-events",required=True)
    p.add_argument("--frontier",required=True); p.add_argument("--output-dir",required=True)
    a=p.parse_args(); out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(SEED)
    frontier=pd.read_csv(a.frontier)
    if frontier.empty: raise RuntimeError("No frozen TRAIN-Pareto candidates.")
    events={k:add_split(pd.read_csv(v,parse_dates=["signal_time","signal_day"]))
            for k,v in {"intraday":a.intraday_events,"swing":a.swing_events}.items()}
    rows=[]; yearly=[]; adjacent=[]
    for cid,c in frontier.reset_index(drop=True).iterrows():
        e=events[c.asset]; base=e[(e.horizon==c.horizon)&(e.side==c.side)].dropna(subset=["return_R"]).copy()
        selected=base[rule_mask(base,c.rule)]
        for split in SPLITS:
            rows.append({"candidate_id":cid,"asset":c.asset,"source_horizon":c.horizon,
                         "side":c.side,"rule":c.rule,**split_row(base,selected,split,rng)})
        for year,q in base.groupby(base.signal_day.dt.year):
            s=q[rule_mask(q,c.rule)]; se,sp,j=metrics(q,s)
            yearly.append({"candidate_id":cid,"asset":c.asset,"source_horizon":c.horizon,
                           "side":c.side,"rule":c.rule,"year":int(year),"population":len(q),
                           "signals":len(s),"mean_R":s.return_R.mean() if len(s) else np.nan,
                           "win_rate":(s.return_R>0).mean() if len(s) else np.nan,
                           "sensitivity":se,"specificity":sp,"youden_J":j})
        for h in HORIZONS[c.asset]:
            q=e[(e.horizon==h)&(e.side==c.side)].dropna(subset=["return_R"]).copy()
            s=q[rule_mask(q,c.rule)]; se,sp,j=metrics(q,s)
            adjacent.append({"candidate_id":cid,"asset":c.asset,"source_horizon":c.horizon,
                             "evaluated_horizon":h,"side":c.side,"rule":c.rule,
                             "population":len(q),"signals":len(s),
                             "mean_R":s.return_R.mean() if len(s) else np.nan,
                             "win_rate":(s.return_R>0).mean() if len(s) else np.nan,
                             "sensitivity":se,"specificity":sp,"youden_J":j})
    v=pd.DataFrame(rows); y=pd.DataFrame(yearly); ad=pd.DataFrame(adjacent)
    summary=[]
    for cid,c in frontier.reset_index(drop=True).iterrows():
        t=v[(v.candidate_id==cid)&(v.split=="TEST")].iloc[0]
        yy=y[(y.candidate_id==cid)&(y.signals>=MIN_YEAR_SIGNALS)]
        summary.append({"candidate_id":cid,"asset":c.asset,"source_horizon":c.horizon,
                        "side":c.side,"rule":c.rule,"test_signals":int(t.signals),
                        "test_mean_R":t.mean_R,"test_mean_ci95_low":t.mean_ci95_low,
                        "test_mean_ci95_high":t.mean_ci95_high,
                        "test_sensitivity":t.sensitivity,"test_specificity":t.specificity,
                        "test_youden_J":t.youden_J,
                        "years_with_50plus_signals":len(yy),
                        "positive_year_fraction":(yy.mean_R>0).mean() if len(yy) else np.nan,
                        "min_annual_mean_R":yy.mean_R.min() if len(yy) else np.nan,
                        "max_annual_mean_R":yy.mean_R.max() if len(yy) else np.nan})
    s=pd.DataFrame(summary)
    v.to_csv(out/"phase5b_candidate_validation.csv",index=False)
    y.to_csv(out/"phase5b_yearly_stability.csv",index=False)
    ad.to_csv(out/"phase5b_adjacent_horizon.csv",index=False)
    s.to_csv(out/"phase5b_summary.csv",index=False)
    pd.DataFrame([{"frozen_candidate_count":len(frontier),"bootstrap_replicates":BOOTSTRAPS,
                   "seed":SEED,"minimum_year_signals":MIN_YEAR_SIGNALS,
                   "selection_note":"No candidate was selected or re-optimized in Phase 5B."}]
                ).to_csv(out/"phase5b_provenance.csv",index=False)
    print("=== PHASE 5B FROZEN-CANDIDATE SUMMARY ===")
    print(s.to_string(index=False))
    print(f"Frozen candidates evaluated: {len(frontier)}")
    print("No candidate was selected or re-optimized.")

if __name__=="__main__": main()
