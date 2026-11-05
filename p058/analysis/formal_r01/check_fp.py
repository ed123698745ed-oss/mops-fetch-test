# 交件前自檢（elon-backtest selfcheck）：E-Test（TR、TO）與策略卡組合（C）分表各跑一次
import sys, pickle, pandas as pd
sys.path.insert(0,'/home/claude/w058'); import elon_tools as ET
bt=ET.load_bt_stats('/home/claude/w058/共用統計函式_bt_stats_v1.2.py')
ALL,RAW=pickle.load(open('/home/claude/w058/out_fp/tabs_fp.pkl','rb'))
R=pd.read_csv('/home/claude/w058/out_fp/stats_fp.csv'); D=pd.read_csv('/home/claude/w058/out_fp/dd_fp.csv')
txt=open(sys.argv[1]).read() if len(sys.argv)>1 else None
def periods(df):
    l=df[df.latest].copy(); l['sample']='最新年度'; l['trade_id']=l.trade_id+'|L'; return pd.concat([df,l])
ok=True
for et,pre in ((True,('TR-','TO-')),(False,('C-',))):
    for cu in ('批次',None):
        ks=[k for k in ALL if k.startswith(pre) and ((ALL[k].cluster.notna().all())==(cu is not None))]
        t=pd.concat([periods(ALL[k]) for k in ks]).drop(columns='latest')
        rep=R[R['combo／sample'].str.split('｜').str[0].isin(ks)].copy()
        dd=D.copy(); dd['combo／sample']=dd['combo'].str.replace('／','｜',n=1); dd=dd[dd['combo／sample'].str.split('｜').str[0].isin(ks)]
        res=ET.selfcheck(t,bt,reported=rep,reported_dd=dd,by=('combo','sample'),cluster_unit=cu,etest=et,report_text=txt,
                         split=('2022-08-16','2022-10-17'),current_r='R01')
        print('==',('E-Test' if et else '策略卡'),cu); ok&=ET.print_check(res)
print('ALL OK' if ok else 'HAS FAIL')
