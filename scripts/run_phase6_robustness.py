"""Phase 6: pre-specified robustness and falsification of frozen CPR regimes.

Phase 5A TRAIN-Pareto candidates are treated as frozen. No threshold is fitted
or selected from validation/test outcomes here.
"""
from __future__ import annotations
import argparse, re
from pathlib import Path
import numpy as np
import pandas as pd

SEED=20260918
BLOCK=10
BOOTSTRAPS=5000
PLACEBO_SIMS=5000
MIN_YEAR_SIGNALS=30
PERTURB_FRACTION=0.20
# Backward-compatible API retained for the existing regression tests.
PERTURBATIONS=((0.40,0.80),(0.50,1.00),(0.60,1.20))

def parse_rule(rule):
    if not rule or rule=="ALL": return []
    pat=re.compile(r"^([A-Za-z0-9_]+)\s*(<=|>)\s*(-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)$")
    out=[]
    for clause in rule.split(" AND "):
        m=pat.match(clause.strip())
        if not m: raise ValueError(f"Cannot parse frozen rule clause: {clause!r}")
        out.append((m.group(1),m.group(2),float(m.group(3))))
    return out

def rule_mask(df, rule):
    m=np.ones(len(df),dtype=bool)
    for col,op,v in parse_rule(rule):
        if col not in df.columns: raise KeyError(col)
        x=df[col].to_numpy(float)
        m &= x <= v if op=="<=" else x > v
    return pd.Series(m,index=df.index)

def block_bootstrap(x,n=BOOTSTRAPS,block=BLOCK,seed=SEED):
    """Reproducible contiguous block bootstrap; returns (low, mean, high)."""
    x=np.asarray(x,dtype=float)
    x=x[np.isfinite(x)]
    if len(x)<2: return (np.nan,np.nan,np.nan)
    rng=np.random.default_rng(seed)
    blocks=[x[i:i+block] for i in range(0,len(x),block)]
    sims=np.empty(int(n))
    for i in range(int(n)):
        vals=[]
        while sum(len(v) for v in vals)<len(x):
            vals.append(blocks[int(rng.integers(0,len(blocks)))])
        sims[i]=np.concatenate(vals)[:len(x)].mean()
    return (float(np.quantile(sims,.025)),float(x.mean()),float(np.quantile(sims,.975)))

def event_mean_ci(sel, rng, n=BOOTSTRAPS, block=BLOCK):
    groups=[g.return_R.to_numpy(float) for _,g in sel.groupby("signal_day",sort=True)]
    nd=len(groups)
    if nd<2: return np.nan,np.nan
    blocks=[groups[i:i+block] for i in range(0,nd,block)]
    nobs=sum(map(len,groups)); sims=np.empty(n)
    for i in range(n):
        vals=[]
        while sum(map(len,vals)) < nobs:
            vals.extend(blocks[int(rng.integers(0,len(blocks)))])
        sims[i]=np.concatenate(vals)[:nobs].mean()
    return float(np.quantile(sims,.025)),float(np.quantile(sims,.975))

def daily_mean(sel):
    return sel.groupby("signal_day",sort=True).return_R.mean()

def day_bootstrap_ci(sel,rng,n=BOOTSTRAPS):
    x=daily_mean(sel); x=x[np.isfinite(x)]
    if len(x)<2: return np.nan,np.nan
    sims=rng.choice(x.to_numpy(float),size=(n,len(x)),replace=True).mean(axis=1)
    return float(np.quantile(sims,.025)),float(np.quantile(sims,.975))

def placebo_p_daily(pop,sel,rng,n=PLACEBO_SIMS):
    days=pop.groupby("signal_day",sort=True).return_R.mean()
    chosen=sel.groupby("signal_day",sort=True).return_R.mean()
    if len(chosen)<2 or len(days)<=len(chosen): return np.nan
    obs=float(chosen.mean()); vals=days.to_numpy(float); k=len(chosen)
    sims=np.empty(n)
    for i in range(n):
        sims[i]=rng.choice(vals,size=k,replace=False).mean()
    return float((1+np.sum(sims>=obs))/(n+1))

def perturb_rule(rule, frac=PERTURB_FRACTION):
    clauses=parse_rule(rule); out=[]
    for i,(col,op,v) in enumerate(clauses):
        delta=frac*abs(v) if v!=0 else frac
        for nv,tag in ((v-delta,"minus"),(v+delta,"plus")):
            c=clauses.copy(); c[i]=(col,op,nv)
            text=" AND ".join(f"{a} {b} {x:.12g}" for a,b,x in c)
            out.append((f"clause{i+1}_{tag}",text))
    return out

def metric_row(pop,sel):
    y=pop.return_R.to_numpy(float)>0
    p=pop.index.isin(sel.index)
    tp=int(np.sum(p&y)); fp=int(np.sum(p&~y)); fn=int(np.sum(~p&y)); tn=int(np.sum(~p&~y))
    se=tp/(tp+fn) if tp+fn else np.nan
    sp=tn/(tn+fp) if tn+fp else np.nan
    return se,sp,se+sp-1 if np.isfinite(se+sp) else np.nan

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--intraday-events",required=True); ap.add_argument("--swing-events",required=True)
    ap.add_argument("--frontier",required=True); ap.add_argument("--output-dir",required=True)
    ap.add_argument("--bootstraps",type=int,default=BOOTSTRAPS); ap.add_argument("--placebo-sims",type=int,default=PLACEBO_SIMS)
    a=ap.parse_args(); out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True)
    frontier=pd.read_csv(a.frontier)
    if frontier.empty: raise RuntimeError("No frozen Phase 5A TRAIN-Pareto candidates.")
    events={"intraday":pd.read_csv(a.intraday_events,parse_dates=["signal_time","signal_day"]),
            "swing":pd.read_csv(a.swing_events,parse_dates=["signal_time","signal_day"])}
    rng=np.random.default_rng(SEED); summary=[]; yearly=[]; adjacent=[]; perturb=[]
    for cid,c in frontier.reset_index(drop=True).iterrows():
        e=events[c.asset]; base=e[(e.horizon==c.horizon)&(e.side==c.side)].dropna(subset=["return_R"]).copy()
        test=base[base.signal_day.dt.year>=2022]; stest=test[rule_mask(test,c.rule)]
        lo,hi=event_mean_ci(stest,rng,a.bootstraps); dlo,dhi=day_bootstrap_ci(stest,rng,a.bootstraps)
        se,sp,j=metric_row(test,stest); p=placebo_p_daily(test,stest,rng,a.placebo_sims)
        summary.append({"candidate_id":cid,"asset":c.asset,"source_horizon":c.horizon,"side":c.side,"rule":c.rule,
                        "test_signals":len(stest),"test_signal_days":stest.signal_day.nunique(),"test_mean_R":stest.return_R.mean() if len(stest) else np.nan,
                        "test_mean_ci95_low":lo,"test_mean_ci95_high":hi,"test_daily_mean_ci95_low":dlo,"test_daily_mean_ci95_high":dhi,
                        "test_sensitivity":se,"test_specificity":sp,"test_youden_J":j,"placebo_p_daily":p})
        for year,q in test.groupby(test.signal_day.dt.year):
            s=q[rule_mask(q,c.rule)]; se2,sp2,j2=metric_row(q,s)
            yearly.append({"candidate_id":cid,"asset":c.asset,"horizon":c.horizon,"side":c.side,"year":int(year),"population":len(q),
                           "signals":len(s),"mean_R":s.return_R.mean() if len(s) else np.nan,"sensitivity":se2,"specificity":sp2,"youden_J":j2})
        horizons=("1bar","3bar","6bar","12bar","EOD") if c.asset=="intraday" else ("2session","3session","5session","10session")
        for h in horizons:
            q=e[(e.horizon==h)&(e.side==c.side)]; q=q[q.signal_day.dt.year>=2022]; ss=q[rule_mask(q,c.rule)]
            adjacent.append({"candidate_id":cid,"asset":c.asset,"source_horizon":c.horizon,"evaluated_horizon":h,"side":c.side,
                             "signals":len(ss),"mean_R":ss.return_R.mean() if len(ss) else np.nan,"positive":bool(len(ss) and ss.return_R.mean()>0)})
        for tag,prule in perturb_rule(c.rule):
            ss=test[rule_mask(test,prule)]
            perturb.append({"candidate_id":cid,"asset":c.asset,"source_horizon":c.horizon,"side":c.side,"perturbation":tag,"rule":prule,
                            "signals":len(ss),"retention":len(ss)/len(stest) if len(stest) else np.nan,"mean_R":ss.return_R.mean() if len(ss) else np.nan,
                            "positive":bool(len(ss) and ss.return_R.mean()>0)})
    s=pd.DataFrame(summary); y=pd.DataFrame(yearly); ad=pd.DataFrame(adjacent); pe=pd.DataFrame(perturb)
    p=s.placebo_p_daily.to_numpy(float); order=np.argsort(np.where(np.isfinite(p),p,1.0)); q=np.full(len(s),np.nan); finite=np.isfinite(p); m=int(finite.sum())
    if m:
        vals=p[order][:m]; adj=np.minimum.accumulate((vals*m/np.arange(1,m+1))[::-1])[::-1]; q[order[:m]]=np.minimum(adj,1.0)
    s["placebo_q_fdr"]=q; s["ci_excludes_zero"]=s.test_mean_ci95_low>0
    pp=pe.groupby("candidate_id").positive.mean().rename("perturb_positive_fraction"); aa=ad.groupby("candidate_id").positive.mean().rename("adjacent_positive_fraction")
    yy=y[y.signals>=MIN_YEAR_SIGNALS].groupby("candidate_id").mean_R.agg(positive_year_fraction=lambda x: float((x>0).mean()),years_with_min_signals="count").reset_index()
    s=s.merge(pp,left_on="candidate_id",right_index=True,how="left").merge(aa,left_on="candidate_id",right_index=True,how="left").merge(yy,on="candidate_id",how="left")
    s["robustness_profile"]=np.select([s.ci_excludes_zero&(s.placebo_q_fdr<=0.10)&(s.perturb_positive_fraction>=0.75),s.ci_excludes_zero&(s.perturb_positive_fraction>=0.50)],
                                      ["strong_evidence_profile","directionally_stable_profile"],default="fragile_or_uncertain_profile")
    s["selection_note"]="Diagnostic only; no candidate selected."
    s.to_csv(out/"phase6_candidate_robustness.csv",index=False); y.to_csv(out/"phase6_yearly_test_stability.csv",index=False)
    ad.to_csv(out/"phase6_adjacent_horizon_test.csv",index=False); pe.to_csv(out/"phase6_threshold_perturbation_test.csv",index=False)
    pd.DataFrame([{"candidate_count":len(frontier),"seed":SEED,"bootstrap_replicates":a.bootstraps,"placebo_sims":a.placebo_sims,"block_length":BLOCK,
                   "min_year_signals":MIN_YEAR_SIGNALS,"perturbation_fraction":PERTURB_FRACTION,"note":"All Phase 5A TRAIN-Pareto rules frozen; Phase 6 performs diagnostics only."}]
                ).to_csv(out/"phase6_provenance.csv",index=False)
    print("=== PHASE 6 ROBUSTNESS SUMMARY ===")
    print(s[["candidate_id","asset","source_horizon","side","test_signals","test_mean_R","test_mean_ci95_low","test_mean_ci95_high","test_sensitivity","test_specificity",
             "test_youden_J","placebo_q_fdr","perturb_positive_fraction","adjacent_positive_fraction","robustness_profile"]].to_string(index=False))
    print(f"Frozen candidates evaluated: {len(s)}"); print("No candidate selected.")

if __name__=="__main__": main()
