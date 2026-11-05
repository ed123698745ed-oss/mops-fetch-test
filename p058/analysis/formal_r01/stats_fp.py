# 058 正式策略包 V02／R01 統計：十項＋回撤三項（bt_stats 1.2），樣本內／樣本外／最新年度並列
import sys, os, pickle, pandas as pd, numpy as np
sys.path.insert(0,'/home/claude/w058'); sys.path.insert(0,'/home/claude/w058/code')
os.environ['V058']='T'
import elon_tools as ET, engine as E      # 只用 E.TI（交易日曆索引）
bt=ET.load_bt_stats('/home/claude/w058/共用統計函式_bt_stats_v1.2.py'); assert ET.baseline_check(bt)
NSUB=10; O='/home/claude/w058/out_fp'
def iso(d): d=str(d); return f"{d[:4]}-{d[4:6]}-{d[6:]}"
def mk(df,combo,retcol,etest,cluster=False):
    df=df.reset_index(drop=True)
    return pd.DataFrame({'trade_id':[f'{combo}|{s}|{c}|{u}' for s,c,u in zip(df['sample'],df.cut,df['sub'] if 'sub' in df else ['M']*len(df))],
        'combo':combo,'is_etest':etest,'symbol':df['sub'].values if 'sub' in df else 'M',
        'info_time':[iso(c)+' 23:59' for c in df.cut],'entry_time':[iso(e)+' 09:00' for e in df.entry],'entry_date':[iso(e) for e in df.entry],
        'entry_px':np.nan,'exit_date':[iso(e) for e in df.exit],'exit_px':np.nan,'ret':df[retcol].astype(float).values,'hold_days':df.hold.astype(int).values,
        'cluster':(df.cut.values if cluster else None),'sample':df['sample'].values,'excluded_reason':None,'latest':df['latest'].values})
def series(name,prefix,etest,subs):
    B=pd.read_csv(f'{O}/{name}/baskets.csv',dtype={'cut':str,'entry':str,'exit':str})
    B['latest']=B['latest'].astype(str)=='True'
    T=B[B.status=='成交'].copy(); inc=set(B[B.status=='未完成'].cut)
    g=T.groupby('cut')
    M=pd.DataFrame({'cut':g.size().index,'n':g.size().values,'sample':g['sample'].first().values,'latest':g.latest.first().values,
        'entry':g.entry.first().values,'exit':g.exit.max().values,'hold':[E.TI[x]-E.TI[e] for e,x in zip(g.entry.first(),g.exit.max())],
        'ret':g.ret.sum().values/NSUB,'ret_eq':g.ret.mean().values,'ret_cash':g.ret_cash.sum().values/NSUB,'ret_loss':g.ret_loss.sum().values/NSUB})
    M=M[(M.n>=2)&(~M.cut.isin(inc))].copy()
    tabs={f'{prefix}-M':mk(M,f'{prefix}-M','ret',etest),f'{prefix}-Meq':mk(M,f'{prefix}-Meq','ret_eq',etest),
          f'{prefix}-P':mk(T,f'{prefix}-P','ret',etest,True),f'{prefix}-L':mk(T.assign(x=T.rl),f'{prefix}-L','x',etest,True),
          f'{prefix}-S':mk(T.assign(x=-T.rs),f'{prefix}-S','x',etest,True)}
    if prefix=='TR':
        tabs['TR-M留現金']=mk(M,'TR-M留現金','ret_cash',etest); tabs['TR-M全損']=mk(M,'TR-M全損','ret_loss',etest)
    for s in subs: tabs[f'{prefix}-{s}']=mk(T[T['sub']==s],f'{prefix}-{s}','ret',etest)
    return tabs,B,M
TS=['T1a','T1b','T2a','T2b','T2c','T3','T6','T7','T8','T9']; CS=['1a','1b','2a','2b','2c','2d','6','7a','8','9']
ALL={}; RAW={}
for name,prefix,etest,subs in (('T_rev_d2','TR',True,TS),('T_orig_d2','TO',True,TS),('C_orig_d2','C',False,CS)):
    tabs,B,M=series(name,prefix,etest,subs); ALL.update(tabs); RAW[prefix]=(B,M)
def periods(df):
    a=df.copy(); l=df[df.latest].copy(); l['sample']='最新年度'; l['trade_id']=l.trade_id+'|L'
    return pd.concat([a,l])
rows=[];dds=[]
for k,df in ALL.items():
    d=periods(df)
    if not len(d): continue
    cu='批次' if d.cluster.notna().all() else None
    t=ET.ten_table(d,bt,by=('combo','sample'),cluster_unit=cu); rows.append(t)
    for s,gs in d.groupby('sample'):
        if len(gs)>=2:
            x=ET.dd_table(gs.assign(combo=k+'／'+s),bt,by=('combo',)); dds.append(x)
R=pd.concat(rows); D=pd.concat(dds)
R.to_csv(f'{O}/stats_fp.csv',index=False); D.to_csv(f'{O}/dd_fp.csv',index=False)
pickle.dump((ALL,RAW),open(f'{O}/tabs_fp.pkl','wb'))
pd.set_option('display.width',260); pd.set_option('display.max_columns',30); pd.set_option('display.max_rows',300)
print(R[['combo／sample','樣本數','平均報酬','平均持有交易日數','單利年化','勝率','賠率R','凱利','標準差','t值','雙尾p']+[c for c in ['聚合單位數','聚合p'] if c in R]].to_string(index=False))
print(D[['combo','最大回撤','最差三次回撤平均','最長回撤期筆數','最長回撤期日曆日','最長回撤期未回復','最長回撤期聚合單位數','需註記']].to_string(index=False))
