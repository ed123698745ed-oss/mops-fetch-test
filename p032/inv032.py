import pandas as pd,json,numpy as np
E=pd.read_csv('/home/claude/p032/event_review_v1.csv',dtype=str).fillna('')
L=pd.read_csv('/home/claude/mops-fetch-test/listing/上市櫃期間表.csv',dtype=str).fillna('').set_index('公司代號')
cal=sorted({r['date'] for r in json.load(open('/home/claude/p032/px/2330.json'))['data']})
cal=pd.to_datetime(pd.Series(cal))
PX={}
def px(c):
    if c not in PX:
        d=pd.DataFrame(json.load(open(f'/home/claude/p032/px/{c}.json'))['data']); d['date']=pd.to_datetime(d['date']); PX[c]=d.set_index('date')
    return PX[c]
ev=E[E['事件判定'].isin(['主事件','候選-非解盲停試'])].copy()
rows=[]
for _,r in ev.iterrows():
    S=pd.to_datetime(r['發言日期']); t=r['發言時間'].zfill(6)
    after=cal[cal>S]; Eday=after.iloc[0] if len(after) else pd.NaT
    Strade=(cal==S).any()
    if not Strade: seg='非交易日'
    elif t<'090000': seg='盤前'
    elif t<'133000': seg='盤中'
    else: seg='盤後'
    a,b=L.loc[r['公司代號'],'初次上市櫃日'],L.loc[r['公司代號'],'終止上市櫃日']
    inlist = pd.notna(Eday) and Eday>=pd.to_datetime(a) and (b=='' or Eday<pd.to_datetime(b))
    p=px(r['公司代號'])
    st='—'
    if pd.notna(Eday):
        if Eday in p.index and p.loc[Eday,'Trading_Volume']>0: st='正常交易'
        else:
            nxt=p[(p.index>Eday)&(p['Trading_Volume']>0)]
            st='停牌/無成交'; resume=nxt.index[0] if len(nxt) else pd.NaT
    # S當日是否停牌（交易日）
    s_halt = Strade and not (S in p.index and p.loc[S,'Trading_Volume']>0)
    pre=p[p.index<S]
    rows.append(dict(cid=r['cid'],公司代號=r['公司代號'],公司名稱=r['公司名稱'],S=S.date(),發言時間=t,時段=seg,E=Eday.date() if pd.notna(Eday) else '',
        E日上市櫃=inlist,E日狀態=st,S日停牌=s_halt,復牌日=(resume.date() if st=='停牌/無成交' and pd.notna(resume) else ''),
        上市後交易日數=len(p[(p.index>=pd.to_datetime(a))&(p.index<=Eday)]) if pd.notna(Eday) else None,
        事前20日資料=len(pre)>=21,事件判定=r['事件判定'],結果分類=r['結果分類'],期別=r['期別'],指標性質=r['指標性質'],結果階段=r['結果階段']))
I=pd.DataFrame(rows); I.to_csv('/home/claude/p032/inventory_v1.csv',index=False,encoding='utf-8-sig')
m=I[I['事件判定']=='主事件']
print('主事件',len(m),'E日不在上市櫃期間',(~m['E日上市櫃']).sum())
ok=m[m['E日上市櫃']]
print(ok['E日狀態'].value_counts().to_string()); print('S日停牌',ok['S日停牌'].sum())
print(ok['時段'].value_counts().to_string())
print('上市後<=5交易日',(ok['上市後交易日數']<=5).sum())
print(m[~m['E日上市櫃']][['公司名稱','S','E']].to_string())
print(ok[ok['E日狀態']!='正常交易'][['公司名稱','S','時段','E','復牌日','結果分類']].to_string())
