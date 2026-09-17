"""Cost-free, point/R-normalized CPR signal baseline."""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
from cpr_lab.data_quality import load_ohlcv_csv
from cpr_lab.features import add_intraday_daily_features, daily_reference_features
from cpr_lab.strategy import StrategyConfig, generate_signals

def main():
    p=argparse.ArgumentParser(); p.add_argument('--input',required=True); p.add_argument('--output-dir',required=True); a=p.parse_args()
    out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True)
    bars=load_ohlcv_csv(a.input)
    daily=bars.resample('1D').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'}).dropna(subset=['open','high','low','close'])
    x=add_intraday_daily_features(bars,daily_reference_features(daily))
    s=generate_signals(x,StrategyConfig(narrow_x=.50,wide_y=1.0,atr_stop=1.0,target_r=2.0,exit_time='15:15'))
    rows=[]
    for i,(ts,r) in enumerate(x.iloc[:-1].iterrows()):
        side='LONG' if bool(s.loc[ts,'long_entry']) else 'SHORT' if bool(s.loc[ts,'short_entry']) else None
        atr=r.get('D_ATR20')
        if side is None or pd.isna(atr) or float(atr)<=0: continue
        n=x.iloc[i+1]; entry=float(n.open); atr=float(atr); d=1 if side=='LONG' else -1
        cp=d*(float(n.close)-entry); mfe=d*(float(n.high)-entry) if d==1 else d*(entry-float(n.low)); mae=d*(float(n.low)-entry) if d==1 else d*(entry-float(n.high))
        rows.append({'signal_time':ts,'entry_time':x.index[i+1],'side':side,'entry_price':entry,'next_close_pnl_points':cp,'next_close_return_pct':100*cp/entry,'mfe_points':mfe,'mae_points':mae,'close_pnl_r':cp/atr,'mfe_r':mfe/atr,'mae_r':mae/atr,'D_ATR20':atr})
    e=pd.DataFrame(rows)
    if e.empty: raise SystemExit('No CPR signals generated')
    e.to_csv(out/'signal_events.csv',index=False); s.to_csv(out/'signals.csv')
    def sm(z,g):
        r=z.close_pnl_r; return {'group':g,'signals':len(z),'long_signals':int((z.side=='LONG').sum()),'short_signals':int((z.side=='SHORT').sum()),'mean_close_R':r.mean(),'median_close_R':r.median(),'win_rate_close':(r>0).mean(),'mean_MFE_R':z.mfe_r.mean(),'median_MFE_R':z.mfe_r.median(),'mean_MAE_R':z.mae_r.mean(),'median_MAE_R':z.mae_r.median(),'p25_close_R':r.quantile(.25),'p75_close_R':r.quantile(.75)}
    m=[sm(e,'ALL')]+[sm(e[e.side==q],q) for q in ('LONG','SHORT') if (e.side==q).any()]
    pd.DataFrame(m).to_csv(out/'signal_metrics.csv',index=False); print(pd.DataFrame(m).to_string(index=False))
if __name__=='__main__': main()
