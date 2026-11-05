import sys, pandas as pd, numpy as np
sys.path.insert(0,'/home/claude/w058'); sys.path.insert(0,'/home/claude/w058/code')
import os; os.environ['V058']='T'
import elon_tools as ET, engine as E
bt=ET.load_bt_stats('/home/claude/w058/共用統計函式_bt_stats_v1.2.py')
B=pd.read_csv('/home/claude/w058/out_t/baskets_is.csv',dtype={'cut':str,'entry':str,'exit':str})
NSUB=10
T=B[B.status=='成交'].copy()
inc=set(B[B.status=='未完成'].cut)   # 該月有未完成籃（現增除權、減資、無出場價）→主組合排除該月，另列 S1
TS1=B[B.status.isin(['成交','未完成'])&B.ret_s1.notna()].copy(); TS1['ret']=TS1.ret_s1
def iso(d): d=str(d); return f"{d[:4]}-{d[4:6]}-{d[6:]}"
def mk(df,combo,retcol,cluster=None):
    out=pd.DataFrame({'trade_id':[f'{combo}-{i:04d}' for i in range(len(df))],'combo':combo,'is_etest':False,'symbol':df['sub'].values if 'sub' in df else '',
        'info_time':[iso(c)+' 23:59' for c in df.cut],'entry_time':[iso(e)+' 09:00' for e in df.entry],'entry_date':[iso(e) for e in df.entry],
        'entry_px':np.nan,'exit_date':[iso(e) for e in df.exit],'exit_px':np.nan,'ret':df[retcol].values,'hold_days':df.hold.values.astype(int),
        'cluster':(df.cut.values if cluster else None),'sample':'樣本內','excluded_reason':None})
    return out
# M：每月跨子鏈（至少兩條子鏈成交），各子鏈 1/10 名目，未成交留現金
g=T.groupby('cut')
M=pd.DataFrame({'cut':g.size().index,'n':g.size().values,'entry':g.entry.first().values,'exit':g.exit.max().values,
                'hold':[E.TI[x]-E.TI[e] for e,x in zip(g.entry.first(),g.exit.max())],
                'ret':g.ret.sum().values/NSUB,'ret_eq':g.ret.mean().values,'rl':g.rl.sum().values/NSUB,'nrs':-g.rs.sum().values/NSUB})
M2=M[(M.n>=2)&(~M.cut.isin(inc))].copy()
g1=TS1.groupby('cut'); M1=pd.DataFrame({'cut':g1.size().index,'n':g1.size().values,'entry':g1.entry.first().values,'exit':g1.exit.max().values,
    'hold':[E.TI[x]-E.TI[e] for e,x in zip(g1.entry.first(),g1.exit.max())],'ret':g1.ret.sum().values/NSUB}); M1=M1[M1.n>=2]
tabs={}
tabs['M 主組合：跨子鏈（≥2條成交，各1/10名目）']=mk(M2,'M','ret')
tabs['M-eq 跨子鏈已成交子鏈等權（描述）']=mk(M2,'M-eq','ret_eq')
tabs['M-S1 敏感度：未完成籃以不認購／實際可得價計入']=mk(M1,'M-S1','ret')
tabs['P 子鏈籃子層（全部成交籃，批次聚合）']=mk(T,'P','ret',cluster=True)
tabs['L 多方腿（下游減速）']=mk(T.assign(x=T.rl),'L','x',cluster=True)
tabs['S 空方腿（−上游累庫報酬）']=mk(T.assign(x=-T.rs),'S','x',cluster=True)
for s in ['T1a','T1b','T2a','T2b','T2c','T3','T6','T7','T8','T9']:
    tabs[f'子鏈 {s}']=mk(T[T['sub']==s],f'sub{s}','ret')
pass
rows=[];dds=[]
for name,df in tabs.items():
    cu='批次' if df.cluster.notna().all() and len(df) else None
    t=ET.ten_table(df,bt,by=('combo',),cluster_unit=cu); t.insert(0,'組合',name); rows.append(t)
    if len(df)>=2: d=ET.dd_table(df,bt,by=('combo',)); d.insert(0,'組合',name); dds.append(d)
R=pd.concat(rows); D=pd.concat(dds)
pd.set_option('display.width',250); pd.set_option('display.max_columns',30)
print(R[['組合','樣本數','平均報酬','平均持有交易日數','單利年化','勝率','賠率R','凱利','標準差','t值','雙尾p']+[c for c in ['聚合單位數','聚合p'] if c in R]].to_string(index=False))
print(D[['組合','最大回撤','最差三次回撤平均','最長回撤期筆數','最長回撤期日曆日','最長回撤期未回復']].to_string(index=False))
R.to_csv('/home/claude/w058/out_t/stats_is.csv',index=False); D.to_csv('/home/claude/w058/out_t/dd_is.csv',index=False)
M.to_csv('/home/claude/w058/out_t/batches_is.csv',index=False)
import pickle; pickle.dump(tabs,open('/home/claude/w058/out_t/tabs.pkl','wb'))
