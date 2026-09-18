"""Phase 6: pre-specified robustness and falsification diagnostics.

No optimization: fixed subperiods, volatility terciles, direction splits,
dependence-aware block bootstrap, and symmetric CPR-threshold perturbations.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

from cpr_lab.data_quality import load_ohlcv_csv
from cpr_lab.indicators import add_intraday_daily_features, daily_reference_features
from cpr_lab.strategies import StrategyConfig, intraday_directional_signals

HORIZONS=(2,3,5,10)
BLOCK=10
SIMULATIONS=5000
PERTURBATIONS=((0.40,0.80),(0.50,1.00),(0.60,1.20))


def daily_mean(z: pd.DataFrame) -> pd.Series:
    return z.groupby("signal_day",as_index=False)["return_R"].mean().set_index("signal_day")["return_R"]


def block_bootstrap(values: np.ndarray, simulations: int, block: int, seed: int=20260918) -> tuple[float,float,float,float]:
    x=np.asarray(values,float); x=x[np.isfinite(x)]
    if len(x)<2: return (np.nan,np.nan,np.nan,np.nan)
    rng=np.random.default_rng(seed)
    blocks=[x[i:i+block] for i in range(0,len(x)-block+1,block)]
    if not blocks: blocks=[x]
    means=np.empty(simulations)
    n=len(x)
    for k in range(simulations):
        sample=[]
        while len(sample)<n:
            sample.extend(blocks[int(rng.integers(0,len(blocks)))])
        means[k]=np.mean(sample[:n])
    return float(np.mean(x)),float(np.quantile(means,.025)),float(np.quantile(means,.975)),float(np.mean(means))


def characterize(events: pd.DataFrame, label: str) -> pd.DataFrame:
    rows=[]
    for h,z in events.groupby("horizon",sort=True):
        d=daily_mean(z); mean,lo,hi,boot=block_bootstrap(d.to_numpy(),SIMULATIONS,BLOCK)
        rows.append({"configuration":label,"horizon":h,"signals":len(z),"signal_days":len(d),
                      "mean_R":mean,"block_bootstrap_95_lo":lo,"block_bootstrap_95_hi":hi,
                      "bootstrap_mean":boot,"win_day_rate":float((d>0).mean())})
        for side in ("LONG","SHORT"):
            q=z[z.side==side]; dd=daily_mean(q)
            if len(dd):
                m,l,u,b=block_bootstrap(dd.to_numpy(),SIMULATIONS,BLOCK)
                rows.append({"configuration":label,"horizon":h,"signals":len(q),"signal_days":len(dd),
                             "mean_R":m,"block_bootstrap_95_lo":l,"block_bootstrap_95_hi":u,
                             "bootstrap_mean":b,"win_day_rate":float((dd>0).mean()),"side":side})
    return pd.DataFrame(rows)


def make_events(bars: pd.DataFrame, nx: float, wy: float) -> pd.DataFrame:
    daily=bars.resample("1D").agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
    x=add_intraday_daily_features(bars,daily_reference_features(daily))
    sig=intraday_directional_signals(x,StrategyConfig(narrow_x=nx,wide_y=wy,atr_stop=1.0,target_r=2.0,exit_time="15:15"))
    session_dates=pd.Series(x.index.date,index=x.index)
    sessions=pd.Index(sorted(session_dates.unique()))
    pos={d:i for i,d in enumerate(sessions)}
    rows=[]
    for i in range(len(x)-1):
        ts=x.index[i]
        side="LONG" if bool(sig.loc[ts,"long_entry"]) else "SHORT" if bool(sig.loc[ts,"short_entry"]) else None
        atr=x.iloc[i].get("D_ATR20"); width=x.iloc[i].get("D_CPR_width_ATR_ratio")
        if side is None or pd.isna(atr) or float(atr)<=0 or pd.isna(width): continue
        entry_i=i+1; entry_ts=x.index[entry_i]; ed=entry_ts.date()
        if ed not in pos: continue
        direction=1 if side=="LONG" else -1
        for h in HORIZONS:
            ti=pos[ed]+h-1
            if ti>=len(sessions): continue
            td=sessions[ti]
            end=np.flatnonzero(session_dates.to_numpy()==td)
            if len(end)==0: continue
            future=x.iloc[entry_i:int(end[-1])+1]
            pnl=direction*(float(future.iloc[-1].close)-float(x.iloc[entry_i].open))
            mfe=direction*((future.high.max() if direction==1 else future.low.min())-float(x.iloc[entry_i].open))
            mae=direction*((future.low.min() if direction==1 else future.high.max())-float(x.iloc[entry_i].open))
            rows.append({"signal_day":pd.Timestamp(ts.date()),"signal_time":ts,"side":side,"horizon":f"{h}session",
                         "return_R":pnl/float(atr),"mfe_R":mfe/float(atr),"mae_R":mae/float(atr),
                         "D_ATR20_pct":100*float(atr)/float(x.iloc[i].close)})
    return pd.DataFrame(rows)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True); p.add_argument("--swing-events",required=True); p.add_argument("--output-dir",required=True)
    p.add_argument("--simulations",type=int,default=SIMULATIONS); a=p.parse_args()
    global SIMULATIONS; SIMULATIONS=a.simulations
    out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True)
    swing=pd.read_csv(a.swing_events,parse_dates=["signal_time","signal_date","entry_session","target_session"])
    swing["signal_day"]=swing.signal_date.dt.normalize()

    base=characterize(swing,"baseline")
    base.to_csv(out/"phase6_block_bootstrap.csv",index=False)

    # Fixed chronological eras; no search over boundaries.
    eras=[("2015-2019","2015-01-01","2019-12-31"),("2020-2024","2020-01-01","2024-12-31")]
    rows=[]
    for label,start,end in eras:
        z=swing[(swing.signal_day>=start)&(swing.signal_day<=end)]
        q=characterize(z,label); rows.append(q)
    pd.concat(rows,ignore_index=True).to_csv(out/"phase6_subperiod_stability.csv",index=False)

    # Volatility terciles are descriptive partitions of the pre-existing D_ATR20/close.
    v=swing.copy()
    v["vol_rank"]=v.groupby("horizon")["width_ratio"].transform(lambda s: s.rank(pct=True))
    # width_ratio is not volatility; use signal-day ATR/close merged from canonical data below.
    bars=load_ohlcv_csv(a.input)
    daily=bars.resample("1D").agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
    x=add_intraday_daily_features(bars,daily_reference_features(daily))
    vol=x[["D_ATR20"]].copy()
    vol["signal_day"]=vol.index.normalize()
    vol_daily=vol.groupby("signal_day").D_ATR20.first()
    close_daily=x.groupby(x.index.normalize()).close.first()
    vol_ratio=(vol_daily/close_daily).dropna()
    v["vol_ratio"]=v.signal_day.map(vol_ratio)
    v["vol_tercile"]=pd.qcut(v.vol_ratio,3,labels=["LOW","MID","HIGH"],duplicates="drop")
    vol_rows=[]
    for bucket,z in v.groupby(["vol_tercile","horizon"],observed=True):
        d=daily_mean(z); m,l,u,b=block_bootstrap(d.to_numpy(),SIMULATIONS,BLOCK)
        vol_rows.append({"vol_tercile":str(bucket[0]),"horizon":bucket[1],"signals":len(z),"signal_days":len(d),
                         "mean_R":m,"block_bootstrap_95_lo":l,"block_bootstrap_95_hi":u})
    pd.DataFrame(vol_rows).to_csv(out/"phase6_volatility_regimes.csv",index=False)

    # Direction-only decomposition on the frozen baseline signal population.
    dir_rows=[]
    for side,z in swing.groupby(["side","horizon"]):
        d=daily_mean(z); m,l,u,b=block_bootstrap(d.to_numpy(),SIMULATIONS,BLOCK)
        dir_rows.append({"side":side[0],"horizon":side[1],"signals":len(z),"signal_days":len(d),
                         "mean_R":m,"block_bootstrap_95_lo":l,"block_bootstrap_95_hi":u})
    pd.DataFrame(dir_rows).to_csv(out/"phase6_direction_robustness.csv",index=False)

    # Symmetric ±20% perturbation around frozen thresholds. No selection/winner is chosen.
    perturb=[]
    for nx,wy in PERTURBATIONS:
        e=make_events(bars,nx,wy)
        if e.empty: continue
        q=characterize(e,f"narrow={nx:.2f},wide={wy:.2f}")
        perturb.append(q)
    pd.concat(perturb,ignore_index=True).to_csv(out/"phase6_threshold_perturbation.csv",index=False)

    print("=== Phase 6 baseline block bootstrap ==="); print(base.to_string(index=False))
    print("\nPhase 6 robustness outputs written.")
if __name__=="__main__": main()
