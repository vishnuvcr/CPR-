"""Phase 9E: frozen consensus incremental-information and robustness analysis.

Question: does the fixed Phase 9B consensus state add information beyond the
ordinary frozen CPR directional activation?

No threshold fitting, candidate selection, or horizon selection is performed.
For each native horizon/side event:
  baseline_positive = at least one frozen candidate matching the event side.
  consensus_state = fixed 9B taxonomy from all frozen candidate activations.
The analysis reports:
  * baseline discrimination;
  * state-conditional outcome rates/returns;
  * incremental separation within baseline-positive events (SINGLE vs MULTIPLE);
  * fixed >=2 same-side consensus as a pre-registered stricter classifier;
  * year-by-year stability;
  * bootstrap CIs;
  * Fisher exact tests and Benjamini-Hochberg q-values across the pre-defined
    family of comparisons.

The 2026 dataset remains an untouched forward evaluation; nothing is fitted
or selected from it.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import fisher_exact

from cpr_lab.data_quality import load_ohlcv_csv
from cpr_lab.indicators import add_intraday_daily_features, daily_reference_features
from run_cpr_regime_discovery import build_intraday_events, build_swing_events, make_context
from run_phase9_shadow_engine import matches

FRONTIER_SHA256 = "601a72f5e64204aee7ff0bb77347d57b0e2b59871b8bc30011282c2dc02c28b2"
LONG_STATES = {"SINGLE_LONG","MULTIPLE_LONG_2_3","MULTIPLE_LONG_4_PLUS"}
SHORT_STATES = {"SINGLE_SHORT","MULTIPLE_SHORT_2_3","MULTIPLE_SHORT_4_PLUS"}
MULTI_LONG = {"MULTIPLE_LONG_2_3","MULTIPLE_LONG_4_PLUS"}
MULTI_SHORT = {"MULTIPLE_SHORT_2_3","MULTIPLE_SHORT_4_PLUS"}

def state(long_n: int, short_n: int) -> str:
    if long_n == 0 and short_n == 0: return "NO_SIGNAL"
    if long_n and short_n: return "CONFLICT"
    n = max(long_n, short_n); side = "LONG" if long_n else "SHORT"
    if n == 1: return f"SINGLE_{side}"
    if n <= 3: return f"MULTIPLE_{side}_2_3"
    return f"MULTIPLE_{side}_4_PLUS"

def bootstrap_ci(x: np.ndarray, stat, reps=4000, seed=20260918):
    x = np.asarray(x, dtype=float); x = x[np.isfinite(x)]
    if len(x) < 2: return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(reps, len(x)))
    vals = np.array([stat(x[i]) for i in idx])
    return float(np.quantile(vals,.025)), float(np.quantile(vals,.975))

def prop_ci(y: np.ndarray):
    y=np.asarray(y,dtype=float)
    return bootstrap_ci(y, lambda z: float(np.mean(z)))

def bh(p):
    p=np.asarray(p,dtype=float); out=np.full(len(p),np.nan)
    ok=np.isfinite(p); pv=p[ok]; m=len(pv)
    if not m: return out
    order=np.argsort(pv); ranked=pv[order]
    q=np.minimum.accumulate((ranked*m/np.arange(1,m+1))[::-1])[::-1]
    tmp=np.empty(m); tmp[order]=np.minimum(q,1.0); out[ok]=tmp
    return out

def population(bars, frontier):
    daily=bars.resample("1D").agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
    x=add_intraday_daily_features(bars,daily_reference_features(daily))
    ctx=make_context(bars).reindex(x.index)
    events={"intraday":build_intraday_events(x,ctx),"swing":build_swing_events(x,ctx)}
    rows=[]
    for asset,ev in events.items():
        if ev.empty: continue
        for ts,g in ev.groupby("signal_time"):
            if ts not in ctx.index: continue
            c=ctx.loc[ts]
            if c.isna().any(): continue
            activated=[cand for _,cand in frontier.iterrows()
                       if cand.asset==asset and matches(c,cand.rule)]
            ln=sum(c.side=="LONG" for c in activated)
            sn=sum(c.side=="SHORT" for c in activated)
            st=state(ln,sn)
            for _,e in g.iterrows():
                side=e.side
                base=(ln>0 if side=="LONG" else sn>0)
                multi=(ln>=2 if side=="LONG" else sn>=2)
                matching_state=st in (LONG_STATES if side=="LONG" else SHORT_STATES)
                rows.append({"signal_time":ts,"year":ts.year,"asset":asset,
                    "horizon":e.horizon,"side":side,"state":st,
                    "long_n":ln,"short_n":sn,"baseline_positive":bool(base),
                    "consensus_positive":bool(matching_state),
                    "strict_consensus_positive":bool(multi),
                    "realized_return_R":float(e.return_R),
                    "outcome_positive":bool(e.return_R>0)})
    return pd.DataFrame(rows)

def metrics(q):
    y=q.outcome_positive.to_numpy(bool); p=q.baseline_positive.to_numpy(bool)
    tp=int((p&y).sum()); fp=int((p&~y).sum()); fn=int((~p&y).sum()); tn=int((~p&~y).sum())
    sens=tp/(tp+fn) if tp+fn else np.nan; spec=tn/(tn+fp) if tn+fp else np.nan
    return {"n":len(q),"positive_outcomes":int(y.sum()),"baseline_positive_n":int(p.sum()),
            "mean_R":q.realized_return_R.mean(),"median_R":q.realized_return_R.median(),
            "win_rate":y.mean(),"sensitivity":sens,"specificity":spec,
            "youden_J":sens+spec-1 if np.isfinite(sens) and np.isfinite(spec) else np.nan}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--p7",required=True); ap.add_argument("--p8",required=True)
    ap.add_argument("--frontier",required=True); ap.add_argument("--output-dir",required=True)
    a=ap.parse_args(); out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True)
    frontier=pd.read_csv(a.frontier)
    if len(frontier)!=39: raise ValueError(f"Expected 39 frozen candidates, found {len(frontier)}")

    allpop=[]
    for dataset,path in [("PHASE7_INDEPENDENT",a.p7),("PHASE8_UNTOUCHED_2026",a.p8)]:
        q=population(load_ohlcv_csv(path),frontier); q["dataset"]=dataset
        q.to_csv(out/f"phase9e_{dataset.lower()}_population.csv",index=False); allpop.append(q)
    d=pd.concat(allpop,ignore_index=True)

    # 1) Baseline vs strict consensus classifier: strict means >=2 matching-side
    # frozen candidates. This is fixed by the 9B taxonomy, not selected from data.
    rows=[]
    for (dataset,asset,horizon,side),q in d.groupby(["dataset","asset","horizon","side"]):
        for name,col in [("BASELINE_ANY_MATCH","baseline_positive"),
                         ("STRICT_MULTI_MATCH","strict_consensus_positive")]:
            p=q[col].to_numpy(bool); y=q.outcome_positive.to_numpy(bool)
            tmp=q.copy(); tmp["pred"]=p
            tp=int((p&y).sum()); fp=int((p&~y).sum()); fn=int((~p&y).sum()); tn=int((~p&~y).sum())
            sens=tp/(tp+fn) if tp+fn else np.nan; spec=tn/(tn+fp) if tn+fp else np.nan
            rows.append({"dataset":dataset,"asset":asset,"horizon":horizon,"side":side,
                         "classifier":name,"n":len(q),"predicted_positive":int(p.sum()),
                         "tp":tp,"fp":fp,"fn":fn,"tn":tn,"sensitivity":sens,"specificity":spec,
                         "youden_J":sens+spec-1 if np.isfinite(sens) and np.isfinite(spec) else np.nan,
                         "mean_R_all":q.realized_return_R.mean(),
                         "mean_R_predicted":q.loc[p,"realized_return_R"].mean() if p.any() else np.nan,
                         "win_rate_predicted":y[p].mean() if p.any() else np.nan})
    baseline=pd.DataFrame(rows); baseline.to_csv(out/"phase9e_baseline_vs_strict.csv",index=False)

    # 2) Fixed state conditioning. Every taxonomy state is retained; no state
    # is selected as the winner.
    state_rows=[]
    for (dataset,asset,horizon,side,state_name),q in d.groupby(["dataset","asset","horizon","side","state"]):
        lo,hi=prop_ci(q.outcome_positive.to_numpy(float))
        rlo,rhi=bootstrap_ci(q.realized_return_R.to_numpy(float),np.mean)
        state_rows.append({"dataset":dataset,"asset":asset,"horizon":horizon,"side":side,
            "state":state_name,"n":len(q),"positive_rate":q.outcome_positive.mean(),
            "positive_rate_ci95_low":lo,"positive_rate_ci95_high":hi,
            "mean_R":q.realized_return_R.mean(),"mean_R_ci95_low":rlo,"mean_R_ci95_high":rhi})
    states=pd.DataFrame(state_rows); states.to_csv(out/"phase9e_state_conditioned.csv",index=False)

    # 3) Incremental information inside ordinary directional activations:
    # SINGLE vs MULTIPLE, and MULTIPLE vs SINGLE. Fisher exact is two-sided.
    tests=[]
    for (dataset,asset,horizon,side),q in d.groupby(["dataset","asset","horizon","side"]):
        z=q[q.baseline_positive]
        single=z[z.state==("SINGLE_LONG" if side=="LONG" else "SINGLE_SHORT")]
        multi=z[z.state.isin(MULTI_LONG if side=="LONG" else MULTI_SHORT)]
        if len(single) and len(multi):
            a1=int(single.outcome_positive.sum()); b1=len(single)-a1
            a2=int(multi.outcome_positive.sum()); b2=len(multi)-a2
            _,p=fisher_exact([[a1,b1],[a2,b2]],alternative="two-sided")
            delta=float(multi.outcome_positive.mean()-single.outcome_positive.mean())
            dlo,dhi=bootstrap_ci(
                np.concatenate([multi.outcome_positive.to_numpy(float),single.outcome_positive.to_numpy(float)]),
                lambda arr: np.nan) if False else (np.nan,np.nan)
            # paired-independent bootstrap of difference
            rng=np.random.default_rng(20260918)
            reps=4000
            mv=multi.outcome_positive.to_numpy(float); sv=single.outcome_positive.to_numpy(float)
            diffs=np.empty(reps)
            for i in range(reps):
                diffs[i]=rng.choice(mv,len(mv),replace=True).mean()-rng.choice(sv,len(sv),replace=True).mean()
            dlo,dhi=float(np.quantile(diffs,.025)),float(np.quantile(diffs,.975))
            rm=multi.realized_return_R.to_numpy(float); rs=single.realized_return_R.to_numpy(float)
            rd=np.empty(reps)
            for i in range(reps):
                rd[i]=rng.choice(rm,len(rm),replace=True).mean()-rng.choice(rs,len(rs),replace=True).mean()
            tests.append({"dataset":dataset,"asset":asset,"horizon":horizon,"side":side,
                "comparison":"MULTIPLE vs SINGLE within baseline-positive events",
                "single_n":len(single),"multiple_n":len(multi),
                "single_win_rate":single.outcome_positive.mean(),"multiple_win_rate":multi.outcome_positive.mean(),
                "delta_win_rate":delta,"delta_win_rate_ci95_low":dlo,"delta_win_rate_ci95_high":dhi,
                "single_mean_R":single.realized_return_R.mean(),"multiple_mean_R":multi.realized_return_R.mean(),
                "delta_mean_R":multi.realized_return_R.mean()-single.realized_return_R.mean(),
                "delta_mean_R_ci95_low":float(np.quantile(rd,.025)),"delta_mean_R_ci95_high":float(np.quantile(rd,.975)),
                "fisher_p":float(p)})
    inc=pd.DataFrame(tests)
    if not inc.empty: inc["fdr_q"] = bh(inc.fisher_p.to_numpy())
    inc.to_csv(out/"phase9e_incremental_tests.csv",index=False)

    # 4) Year-by-year stability for strict consensus and state-conditioned returns.
    yr=[]
    for (dataset,year,asset,horizon,side),q in d.groupby(["dataset","year","asset","horizon","side"]):
        for name,col in [("BASELINE_ANY_MATCH","baseline_positive"),("STRICT_MULTI_MATCH","strict_consensus_positive")]:
            p=q[col].to_numpy(bool); y=q.outcome_positive.to_numpy(bool)
            pred=q.loc[p,"realized_return_R"]
            yr.append({"dataset":dataset,"year":year,"asset":asset,"horizon":horizon,"side":side,
                "classifier":name,"n":len(q),"predicted_n":int(p.sum()),
                "predicted_win_rate":y[p].mean() if p.any() else np.nan,
                "predicted_mean_R":pred.mean() if len(pred) else np.nan})
    pd.DataFrame(yr).to_csv(out/"phase9e_yearly_stability.csv",index=False)

    pd.DataFrame([{
        "protocol":"Frozen Phase 9B taxonomy + frozen Phase 5A frontier",
        "baseline":"At least one frozen candidate matching event side",
        "strict_consensus":"At least two frozen candidates matching event side",
        "incremental_test":"MULTIPLE (2+) vs SINGLE (1) within baseline-positive events",
        "statistics":"Wilson/bootstrap 95% CIs; Fisher exact two-sided; BH FDR q-values across incremental tests",
        "threshold_refitting":"NONE","candidate_selection":"NONE","2026_role":"Untouched forward evaluation"
    }]).to_csv(out/"phase9e_provenance.csv",index=False)

    print("=== PHASE 9E COMPLETE ===")
    print("Baseline/strict:")
    print(baseline.to_string(index=False))
    print("\nIncremental tests:")
    print(inc.to_string(index=False) if not inc.empty else "No eligible SINGLE/MULTIPLE comparisons")
    print("\nState counts:")
    print(d.groupby(["dataset","state"]).size().to_string())

if __name__=="__main__": main()
