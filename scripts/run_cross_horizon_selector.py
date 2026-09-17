"""Phase 4 leakage-safe cross-horizon selector for CPR swing signals."""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
HORIZONS=("2session","3session","5session","10session")
MAX_HORIZON=10
TRAIN_SESSIONS=756
VALIDATION_SESSIONS=252

def load_events(path:str)->pd.DataFrame:
    e=pd.read_csv(path,parse_dates=["signal_time","signal_date","entry_session","target_session"])
    e["signal_day"]=e.signal_date.dt.normalize()
    e["entry_day"]=e.entry_session.dt.normalize()
    e["target_day"]=e.target_session.dt.normalize()
    return e.sort_values(["signal_day","signal_time","horizon"]).reset_index(drop=True)

def choose_horizon(train:pd.DataFrame,side:str)->tuple[str,pd.DataFrame]:
    z=train[train.side==side]; rows=[]
    for h in HORIZONS:
        q=z[z.horizon==h]; daily=q.groupby("signal_day",as_index=False).return_R.mean()
        rows.append({"side":side,"horizon":h,"training_days":len(daily),"training_mean_R":float(daily.return_R.mean()) if len(daily) else np.nan})
    scores=pd.DataFrame(rows); valid=scores.dropna(subset=["training_mean_R"])
    if valid.empty:return HORIZONS[0],scores
    order={h:i for i,h in enumerate(HORIZONS)}; best=float(valid.training_mean_R.max())
    tied=valid[np.isclose(valid.training_mean_R,best,rtol=0,atol=1e-12)]
    return sorted(tied.horizon.tolist(),key=lambda h:order[h])[0],scores

def main()->None:
    p=argparse.ArgumentParser(); p.add_argument("--input",required=True); p.add_argument("--output-dir",required=True); a=p.parse_args()
    out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True); e=load_events(a.input)
    sessions=pd.Index(sorted(e.entry_day.dropna().unique()))
    if len(sessions)<TRAIN_SESSIONS+VALIDATION_SESSIONS+MAX_HORIZON:raise SystemExit("Insufficient sessions for fixed walk-forward design")
    selections=[]; oos_rows=[]; split_id=0; train_end_i=TRAIN_SESSIONS-1
    while train_end_i+MAX_HORIZON+VALIDATION_SESSIONS<len(sessions):
        purge_start_i=train_end_i+1; validation_start_i=purge_start_i+MAX_HORIZON
        validation_end_i=min(validation_start_i+VALIDATION_SESSIONS-1,len(sessions)-1); train_start_i=max(0,train_end_i-TRAIN_SESSIONS+1)
        train_start=sessions[train_start_i]; train_end=sessions[train_end_i]; purge_start=sessions[purge_start_i]; validation_start=sessions[validation_start_i]; validation_end=sessions[validation_end_i]
        train=e[(e.entry_day>=train_start)&(e.entry_day<=train_end)&(e.target_day<=train_end)]
        validation=e[(e.entry_day>=validation_start)&(e.entry_day<=validation_end)]; split_id+=1; chosen_by_side={}
        for side in ("LONG","SHORT"):
            chosen,scores=choose_horizon(train,side); chosen_by_side[side]=chosen
            selections.append({"split":split_id,"train_start":train_start,"train_end":train_end,"purge_start":purge_start,"validation_start":validation_start,"validation_end":validation_end,"side":side,"selected_horizon":chosen,"training_days_total":int(scores.training_days.sum()),"training_scores":"|".join(f"{r.horizon}:{r.training_mean_R:.8f}" for r in scores.itertuples())})
        v=validation.copy(); v["selected"]=v.apply(lambda r:r.horizon==chosen_by_side.get(r.side),axis=1); selected=v[v.selected].copy(); selected["split"]=split_id; oos_rows.append(selected); train_end_i=validation_end_i
    if not oos_rows:raise SystemExit("No walk-forward validation splits generated")
    oos=pd.concat(oos_rows,ignore_index=True); pd.DataFrame(selections).to_csv(out/"cross_horizon_selections.csv",index=False); oos.to_csv(out/"cross_horizon_selected_events.csv",index=False)
    oos_days=set(oos.entry_day); rows=[]; daily=oos.groupby("signal_day",as_index=False).return_R.mean()
    rows.append({"strategy":"SELECTED","signals":len(oos),"signal_days":len(daily),"mean_R":daily.return_R.mean(),"median_R":daily.return_R.median(),"win_day_rate":(daily.return_R>0).mean()})
    for h in HORIZONS:
        q=e[e.entry_day.isin(oos_days)&(e.horizon==h)]; d=q.groupby("signal_day",as_index=False).return_R.mean()
        rows.append({"strategy":h,"signals":len(q),"signal_days":len(d),"mean_R":d.return_R.mean(),"median_R":d.return_R.median(),"win_day_rate":(d.return_R>0).mean()})
    pd.DataFrame(rows).to_csv(out/"cross_horizon_oos_comparison.csv",index=False)
    yearly_rows=[]
    for year,q in oos.assign(year=oos.signal_date.dt.year).groupby("year"):
        d=q.groupby("signal_day",as_index=False).return_R.mean(); yearly_rows.append({"year":int(year),"signals":len(q),"signal_days":len(d),"mean_R":d.return_R.mean(),"median_R":d.return_R.median(),"win_day_rate":(d.return_R>0).mean()})
    pd.DataFrame(yearly_rows).to_csv(out/"cross_horizon_oos_yearly.csv",index=False)
    print("=== WALK-FORWARD HORIZON SELECTIONS ==="); print(pd.DataFrame(selections).to_string(index=False)); print("\n=== OOS COMPARISON ==="); print(pd.DataFrame(rows).to_string(index=False)); print("\n=== SELECTED OOS YEARLY ==="); print(pd.DataFrame(yearly_rows).to_string(index=False))

if __name__=="__main__":main()
