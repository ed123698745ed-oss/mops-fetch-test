# 診斷（描述，不作通過判定）：逐年、逐一移除子鏈、前五大正貢獻、財報資料年齡、連續訊號段
import sys, pickle, pandas as pd, numpy as np, collections
sys.path.insert(0,'/home/claude/w058'); import elon_tools as ET
bt=ET.load_bt_stats('/home/claude/w058/共用統計函式_bt_stats_v1.2.py')
ALL,RAW=pickle.load(open('/home/claude/w058/out_fp/tabs_fp.pkl','rb'))
B,M=RAW['TR']; NSUB=10
def st(x):
    t=pd.DataFrame({'ret':x,'hold_days':20}); r=bt.summarize_df(t,ret='ret',hold='hold_days'); return r.iloc[0]
out=[]
M['year']=M.cut.str[:4]
for (s,y),g in M.groupby(['sample','year']):
    r=st(g.ret.values); out.append(['逐年',s,y,len(g),g.ret.mean(),r['雙尾p'] if len(g)>1 else np.nan])
T=B[B.status=='成交']; inc=set(B[B.status=='未完成'].cut)
for s in sorted(T['sub'].unique()):
    for smp in ('樣本內','樣本外'):
        TT=T[(T['sub']!=s)&(T['sample']==smp)]; g=TT.groupby('cut'); n=g.size(); r=g.ret.sum()/NSUB
        r=r[(n>=2)&(~r.index.isin(inc))]; q=st(r.values); out.append(['移除子鏈',smp,s,len(r),r.mean(),q['雙尾p']])
for smp in ('樣本內','樣本外'):
    g=M[M['sample']==smp]; pos=g.ret[g.ret>0].sort_values(ascending=False)
    out.append(['前五大正貢獻占正報酬合計',smp,'',len(g),pos.head(5).sum()/pos.sum(),np.nan])
    out.append(['前五大正貢獻占淨報酬合計',smp,'',len(g),pos.head(5).sum()/g.ret.sum() if g.ret.sum()!=0 else np.nan,np.nan])
D=pd.DataFrame(out,columns=['項目','樣本','分組','批數','平均或占比','雙尾p'])
D.to_csv('/home/claude/w058/out_fp/diag_TR.csv',index=False)
pd.set_option('display.width',200); pd.set_option('display.max_rows',200); print(D.to_string(index=False))
# 財報資料年齡與連續訊號段（上游＝本組合多方）
S=pd.read_csv('/home/claude/w058/out_fp/T_rev_d2/signals.csv',dtype=str)
u=S[(S.role=='U')&(S.signal=='True')]
print('上游累庫訊號（股票月）',len(u))
seg=0
for (sub,c),g in u.groupby(['sub','code']):
    cs=sorted(g.cut); prev=None
    for x in cs:
        y,m=int(x[:4]),int(x[4:6]); k=y*12+m
        if prev is None or k!=prev+1: seg+=1
        prev=k
print('同子鏈同股連續訊號段',seg)
