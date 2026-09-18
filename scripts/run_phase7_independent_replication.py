"""Apply all frozen Phase 5A candidates to the independent Phase 7 dataset."""
from __future__ import annotations
import argparse,re
from pathlib import Path
import numpy as np,pandas as pd
from cpr_lab.data_quality import load_ohlcv_csv
from cpr_lab.indicators import add_intraday_daily_features,daily_reference_features
# This file is executed directly by CI, so scripts/ is on sys.path.
from run_cpr_regime_discovery import make_context,build_intraday_events,build_swing_events

SEED=20260918; BOOTSTRAPS=5000; BLOCK=10
PAT=re.compile(r"^([A-Za-z0-9_]+)\s*(<=|>)\s*(-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)$")

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
        x=df[col].to_numpy(float)
        m &= x<=v if op=="<=" else x>v
    return pd.Series(m,index=df.index)

def ci(sel,rng):
    groups=[g.return_R.to_numpy(float) for _,g in sel.groupby("signal_day",sort=True)]
    nd=len(groups)
    if nd<2:return np.nan,np.nan
    blocks=[groups[i:i+BLOCK] for i in range(0,nd,BLOCK)]
    nobs=sum(map(len,groups)); sims=np.empty(BOOTSTRAPS)
    for i in range(BOOTSTRAPS):
        vals=[]
        while sum(map(len,vals))<nobs:
            vals.extend(blocks[int(rng.integers(0,len(blocks)))])
        sims[i]=np.concatenate(vals)[:nobs].mean()
    return float(np.quantile(sims,.025)),float(np.quantile(sims,.975))

def metrics(pop,sel):
    y=pop.return_R.to_numpy(float)>0;p=pop.index.isin(sel.index)
    tp=np.sum(p&y);fp=np.sum(p&~y);fn=np.sum(~p&y);tn=np.sum(~p&~y)
    se=tp/(tp+fn) if tp+fn else np.nan;sp=tn/(tn+fp) if tn+fp else np.nan
    return se,sp,se+sp-1 if np.isfinite(se+sp) else np.nan

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True);ap.add_argument("--frontier",required=True);ap.add_argument("--output-dir",required=True)
    a=ap.parse_args();out=Path(a.output_dir);out.mkdir(parents=True,exist_ok=True)
    frontier=pd.read_csv(a.frontier)
    if len(frontier)!=39: raise ValueError(f"Expected frozen 39 candidates, found {len(frontier)}")
    bars=load_ohlcv_csv(a.input)
    daily=bars.resample("1D").agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
    x=add_intraday_daily_features(bars,daily_reference_features(daily))
    ctx=make_context(bars).reindex(x.index)
    intr=build_intraday_events(x,ctx); swing=build_swing_events(x,ctx)
    rng=np.random.default_rng(SEED);rows=[];year=[]
    for cid,c in frontier.reset_index(drop=True).iterrows():
        e=intr if c.asset=="intraday" else swing
        z=e[(e.horizon==c.horizon)&(e.side==c.side)].dropna(subset=["return_R"])
        s=z[mask(z,c.rule)]
        lo,hi=ci(s,rng);se,sp,j=metrics(z,s)
        rows.append({"candidate_id":cid,"asset":c.asset,"horizon":c.horizon,"side":c.side,"rule":c.rule,
                     "signals":len(s),"signal_days":s.signal_day.nunique(),"mean_R":s.return_R.mean() if len(s) else np.nan,
                     "ci95_low":lo,"ci95_high":hi,"sensitivity":se,"specificity":sp,"youden_J":j})
        for yr,q in z.groupby(z.signal_day.dt.year):
            sy=q[mask(q,c.rule)];se2,sp2,j2=metrics(q,sy)
            year.append({"candidate_id":cid,"year":int(yr),"population":len(q),"signals":len(sy),
                         "mean_R":sy.return_R.mean() if len(sy) else np.nan,"sensitivity":se2,"specificity":sp2,"youden_J":j2})
    s=pd.DataFrame(rows);y=pd.DataFrame(year)
    s["ci_excludes_zero"]=s.ci95_low>0
    yy=y[y.signals>=30].groupby("candidate_id").mean_R.agg(positive_year_fraction=lambda x:(x>0).mean(),years_with_min_signals="count").reset_index()
    s=s.merge(yy,on="candidate_id",how="left")
    s["note"]="Frozen Phase 5A rule applied unchanged to independent data; no fitting or candidate selection."
    s.to_csv(out/"phase7_independent_replication.csv",index=False);y.to_csv(out/"phase7_yearly.csv",index=False)
    print("=== PHASE 7 INDEPENDENT REPLICATION ===")
    print(s.to_string(index=False))

if __name__=="__main__": main()
