"""Conditional CPR regime discovery for trade-decision design.

Goal: discover *where* the frozen CPR signal behaves best, not test whether it
works uniformly across all regimes. Discovery is chronological and produces
interpretable decision-tree leaves plus a sensitivity/specificity Pareto
frontier. No test-period information is used to build the regimes.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier, export_text

from cpr_lab.data_quality import load_ohlcv_csv
from cpr_lab.indicators import add_intraday_daily_features, daily_reference_features
from cpr_lab.strategies import StrategyConfig, intraday_directional_signals

FEATURES = [
    "cpr_width_atr",
    "atr_pct",
    "gap_atr",
    "intraday_move_atr",
    "intraday_range_atr",
    "close_vs_cpr_mid_atr",
    "close_vs_p_atr",
    "close_vs_pdh_atr",
    "close_vs_pdl_atr",
    "prior_day_return_atr",
    "prior_day_range_atr",
    "trigger_extension_atr",
    "minute_from_open",
]
HORIZONS_INTRADAY=("1bar","3bar","6bar","12bar","EOD")
HORIZONS_SWING=("2session","3session","5session","10session")
MIN_LEAF=100
MAX_DEPTH=3
SEED=20260918


def make_context(bars: pd.DataFrame) -> pd.DataFrame:
    daily=bars.resample("1D").agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
    dfeat=daily_reference_features(daily)
    x=add_intraday_daily_features(bars,dfeat)
    day=x.index.normalize()
    prior_close=pd.Series(daily.close.to_numpy(),index=daily.index).shift(1)
    prior_range=daily.high-daily.low
    prior_ret=daily.close.pct_change()
    prior_atr=dfeat["D_ATR20"]
    day_open=x.groupby(day).open.transform("first")
    day_high=x.groupby(day).high.cummax()
    day_low=x.groupby(day).low.cummin()
    upper=x[["D_R1","D_PDH"]].max(axis=1)
    lower=x[["D_S1","D_PDL"]].min(axis=1)
    direction=np.where(x.close >= upper,1,np.where(x.close <= lower,-1,np.nan))
    out=pd.DataFrame(index=x.index)
    atr=x["D_ATR20"].astype(float)
    atr_safe=atr.replace(0,np.nan)
    out["cpr_width_atr"]=x["D_CPR_width_ATR_ratio"]
    out["atr_pct"]=atr_safe/x.close
    out["gap_atr"]=(day_open-x["D_Close"])/atr_safe
    out["intraday_move_atr"]=(x.close-day_open)/atr_safe
    out["intraday_range_atr"]=(day_high-day_low)/atr_safe
    cpr_mid=(x.D_CPR_low+x.D_CPR_high)/2
    out["close_vs_cpr_mid_atr"]=(x.close-cpr_mid)/atr_safe
    out["close_vs_p_atr"]=(x.close-x.D_P)/atr_safe
    out["close_vs_pdh_atr"]=(x.close-x.D_PDH)/atr_safe
    out["close_vs_pdl_atr"]=(x.close-x.D_PDL)/atr_safe
    day_key=day
    out["prior_day_return_atr"]=day_key.map((daily.close-daily.close.shift(1))/dfeat["D_ATR20"])
    out["prior_day_range_atr"]=day_key.map((daily.high-daily.low)/dfeat["D_ATR20"])
    out["minute_from_open"]=((x.index.hour*60+x.index.minute)-555).astype(float)
    # Direction-aware extension beyond the trigger. Positive for a valid breakout.
    out["trigger_extension_atr"]=np.where(direction==1,(x.close-upper)/atr_safe,
                                   np.where(direction==-1,(lower-x.close)/atr_safe,np.nan))
    out["signal_day"]=day_key
    return out


def build_intraday_events(x: pd.DataFrame, context: pd.DataFrame) -> pd.DataFrame:
    sig=intraday_directional_signals(x,StrategyConfig(narrow_x=.5,wide_y=1.0,atr_stop=1,target_r=2,exit_time="15:15"))
    rows=[]
    idx=x.index
    for i in range(len(x)-1):
        ts=idx[i]
        side="LONG" if bool(sig.loc[ts,"long_entry"]) else "SHORT" if bool(sig.loc[ts,"short_entry"]) else None
        if side is None: continue
        entry_i=i+1
        if context.iloc[i].isna().any(): continue
        direction=1 if side=="LONG" else -1
        same_date=idx.date==idx[entry_i].date()
        day_end=np.flatnonzero(same_date & (np.arange(len(idx))>=entry_i))
        if len(day_end)==0: continue
        end=int(day_end[-1])
        for h in (1,3,6,12):
            j=entry_i+h-1
            if j>end: continue
            future=x.iloc[entry_i:j+1]
            entry=float(x.iloc[entry_i].open); atr=float(x.iloc[i].D_ATR20)
            pnl=direction*(float(future.iloc[-1].close)-entry)
            rows.append({**context.iloc[i].to_dict(),"side":side,"horizon":f"{h}bar","return_R":pnl/atr,
                         "signal_time":ts,"signal_day":ts.normalize()})
        future=x.iloc[entry_i:end+1]; entry=float(x.iloc[entry_i].open); atr=float(x.iloc[i].D_ATR20)
        pnl=direction*(float(future.iloc[-1].close)-entry)
        rows.append({**context.iloc[i].to_dict(),"side":side,"horizon":"EOD","return_R":pnl/atr,
                     "signal_time":ts,"signal_day":ts.normalize()})
    return pd.DataFrame(rows)


def build_swing_events(x: pd.DataFrame, context: pd.DataFrame) -> pd.DataFrame:
    sig=intraday_directional_signals(x,StrategyConfig(narrow_x=.5,wide_y=1.0,atr_stop=1,target_r=2,exit_time="15:15"))
    sessions=pd.Index(sorted(x.index.normalize().unique()))
    pos={d:i for i,d in enumerate(sessions)}
    session_end={d:int(np.flatnonzero(x.index.normalize()==d)[-1]) for d in sessions}
    rows=[]
    for i in range(len(x)-1):
        ts=x.index[i]
        side="LONG" if bool(sig.loc[ts,"long_entry"]) else "SHORT" if bool(sig.loc[ts,"short_entry"]) else None
        if side is None or context.iloc[i].isna().any(): continue
        entry_i=i+1; entry_day=x.index[entry_i].normalize()
        if entry_day not in pos: continue
        direction=1 if side=="LONG" else -1
        for h in (2,3,5,10):
            ti=pos[entry_day]+h-1
            if ti>=len(sessions): continue
            end=session_end[sessions[ti]]
            future=x.iloc[entry_i:end+1]
            entry=float(x.iloc[entry_i].open); atr=float(x.iloc[i].D_ATR20)
            pnl=direction*(float(future.iloc[-1].close)-entry)
            rows.append({**context.iloc[i].to_dict(),"side":side,"horizon":f"{h}session","return_R":pnl/atr,
                         "signal_time":ts,"signal_day":ts.normalize()})
    return pd.DataFrame(rows)


def split_label(d: pd.Timestamp) -> str:
    y=int(d.year)
    if y<=2018:return "TRAIN"
    if y<=2021:return "VALIDATION"
    return "TEST"


def leaf_rules(tree, feature_names, leaf_id) -> str:
    tree_=tree.tree_
    rules=[]
    def walk(node, path):
        if node==leaf_id:
            rules.extend(path); return True
        if tree_.children_left[node] != -1:
            f=feature_names[tree_.feature[node]]
            thr=tree_.threshold[node]
            if walk(tree_.children_left[node],path+[f+" <= "+f"{thr:.4g}"]): return True
            if walk(tree_.children_right[node],path+[f+" > "+f"{thr:.4g}"]): return True
        return False
    walk(0,[])
    return " AND ".join(rules) if rules else "ALL"


def metrics_for_leaf(y, leaf_ids, leaf):
    pred=(leaf_ids==leaf)
    y=np.asarray(y,dtype=int)
    tp=int(np.sum(pred & (y==1))); fp=int(np.sum(pred & (y==0)))
    fn=int(np.sum(~pred & (y==1))); tn=int(np.sum(~pred & (y==0)))
    sens=tp/(tp+fn) if tp+fn else np.nan
    spec=tn/(tn+fp) if tn+fp else np.nan
    return tp,fp,fn,tn,sens,spec


def pareto_frontier(df: pd.DataFrame) -> pd.DataFrame:
    keep=[]
    for i,r in df.iterrows():
        dominated=((df.sensitivity>=r.sensitivity)&(df.specificity>=r.specificity)&
                   ((df.sensitivity>r.sensitivity)|(df.specificity>r.specificity))).any()
        if not dominated: keep.append(i)
    return df.loc[keep].sort_values(["sensitivity","specificity"],ascending=False)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--output-dir",required=True)
    a=p.parse_args()
    out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True)
    bars=load_ohlcv_csv(a.input)
    daily=bars.resample("1D").agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
    x=add_intraday_daily_features(bars,daily_reference_features(daily))
    ctx=make_context(bars).reindex(x.index)
    intr=build_intraday_events(x,ctx)
    swing=build_swing_events(x,ctx)
    intr.to_csv(out/"regime_discovery_intraday_events.csv",index=False)
    swing.to_csv(out/"regime_discovery_swing_events.csv",index=False)
    all_front=[]; all_eval=[]
    for asset,events,horizons in [("intraday",intr,HORIZONS_INTRADAY),("swing",swing,HORIZONS_SWING)]:
        events=events.copy()
        events["split"]=events.signal_day.map(split_label)
        for horizon in horizons:
            for side in ("LONG","SHORT"):
                z=events[(events.horizon==horizon)&(events.side==side)].dropna(subset=FEATURES+["return_R"]).copy()
                tr=z[z.split=="TRAIN"]; va=z[z.split=="VALIDATION"]; te=z[z.split=="TEST"]
                if len(tr)<MAX_DEPTH*MIN_LEAF*2 or len(va)<MIN_LEAF or len(te)<MIN_LEAF: continue
                y=(tr.return_R>0).astype(int)
                tree=DecisionTreeClassifier(max_depth=MAX_DEPTH,min_samples_leaf=MIN_LEAF,random_state=SEED,criterion="gini")
                tree.fit(tr[FEATURES],y)
                for name,q in [("TRAIN",tr),("VALIDATION",va),("TEST",te)]:
                    leaves=tree.apply(q[FEATURES])
                    for leaf in np.unique(leaves):
                        tp,fp,fn,tn,sens,spec=metrics_for_leaf((q.return_R>0).astype(int).to_numpy(),leaves,leaf)
                        all_eval.append({"asset":asset,"horizon":horizon,"side":side,"split":name,"leaf":int(leaf),
                                         "rule":leaf_rules(tree,FEATURES,int(leaf)),"signals":len(q[leaves==leaf]),
                                         "mean_R":float(q.loc[leaves==leaf,"return_R"].mean()),"win_rate":float((q.loc[leaves==leaf,"return_R"]>0).mean()),
                                         "sensitivity":sens,"specificity":spec,"youden_J":sens+spec-1 if np.isfinite(sens+spec) else np.nan})
                # Candidate leaves are defined only from TRAIN Pareto frontier.
                tr_eval=pd.DataFrame([r for r in all_eval if r["asset"]==asset and r["horizon"]==horizon and r["side"]==side and r["split"]=="TRAIN"])
                pf=pareto_frontier(tr_eval)
                for _,r in pf.iterrows():
                    all_front.append({**r.to_dict(),"candidate":"TRAIN_PARETO"})
                with open(out/f"tree_{asset}_{horizon}_{side.lower()}.txt","w",encoding="utf-8") as fh:
                    fh.write(export_text(tree,feature_names=FEATURES,decimals=3))
    frontier=pd.DataFrame(all_front); evaluation=pd.DataFrame(all_eval)
    frontier.to_csv(out/"regime_discovery_train_pareto.csv",index=False)
    evaluation.to_csv(out/"regime_discovery_leaf_evaluation.csv",index=False)
    if not frontier.empty:
        oos=evaluation.merge(frontier[["asset","horizon","side","leaf"]].drop_duplicates(),
                             on=["asset","horizon","side","leaf"],how="inner")
        oos.to_csv(out/"regime_discovery_pareto_oos.csv",index=False)
    print("=== TRAIN PARETO REGIMES ===")
    print(frontier.to_string(index=False))
    print("\n=== PARETO REGIMES OOS ===")
    print(pd.read_csv(out/"regime_discovery_pareto_oos.csv").to_string(index=False) if (out/"regime_discovery_pareto_oos.csv").exists() else "none")


if __name__=="__main__": main()
