# 058 S2 訊號（時點版）：公開資訊觀測站原始申報＋電子書上傳時間＋更補正；月營收 FinMind＋營收更正重訊
import json, csv, collections, calendar, datetime as dt
W='/home/claude/w058'
# ---- 子鏈與成員（依 D-058-20261105-0029-1、1121-1、1121-2；純度判定見盤點報告與 purity 檔）----
SUB={'1a':{'U':['2383','6274','6213'],'D':['2368','3044','2313']},
     '1b':{'U':['2368','3044','2313'],'D':['2382','3231','6669']},
     '2a':{'U':['6121','3211'],'D':['2324','2356']},
     '2b':{'U':['6412','6282'],'D':['2324','2356']},
     '2c':{'U':['3324','3338'],'D':['2324','2356']},
     '2d':{'U':['2324','2356'],'D':['2357']},
     '6':{'U':['2379'],'D':['3596','6285']},
     '7a':{'U':['3234','3081'],'D':['4979','4908']},
     '8':{'U':['1452'],'D':['1476','1477','4438']},
     '9':{'U':['5306'],'D':['9921','9914']}}
CHAIN={'1a':1,'1b':1,'2a':2,'2b':2,'2c':2,'2d':2,'6':6,'7a':7,'8':8,'9':9}
# ---- 月營收 ----
rev={}
for c in {x for s in SUB.values() for x in s['D']}:
    d=json.load(open(f'{W}/raw_finmind/MonthRevenue_{c}.json'))['data']
    rev[c]={(x['revenue_year'],x['revenue_month']):x['revenue'] for x in d if x['revenue_year']>=2013}
def add(ym,k):
    t=ym[0]*12+ym[1]-1+k; return (t//12,t%12+1)
def G3(c,ym):
    r=rev[c]; num=[r.get(add(ym,-i)) for i in range(3)]; den=[r.get(add(ym,-12-i)) for i in range(3)]
    if None in num or None in den or sum(den)<=0: return None
    return sum(num)/sum(den)-1
# 營收更正（公告日前的截點不得使用涵蓋更正月份的 G3）
RC={'4967':[((2013,1),(2013,6),'20130822'),((2014,1),(2014,1),'20140210'),((2014,1),(2014,12),'20150430'),((2016,1),(2016,12),'20170412'),((2017,1),(2017,12),'20180424')],
    '2368':[((2015,7),(2015,7),'20160808')],'4438':[((2015,6),(2015,7),'20161019'),((2017,3),(2017,3),'20180410')],'4979':[((2019,9),(2019,9),'20191014')],
    '3363':[((2019,12),(2019,12),'20200109')],'6274':[((2025,4),(2025,7),'20250813')]}
def rev_unverified(c,ym,cut):
    months=[add(ym,-i) for i in range(5)]+[add(ym,-12-i) for i in range(5)]
    for a,b,d in RC.get(c,[]):
        if cut<d and any(a<=m<=b for m in months): return True
    return False
# ---- 季報 ----
F={}
for r in csv.DictReader(open(f'{W}/fund_mops.csv',encoding='utf-8')):
    F[(r['code'],int(r['y']),int(r['q']))]=r
def days_q(y,q): return [90+calendar.isleap(y),91,92,92][q-1]
def prevq(y,q): return (y,q-1) if q>1 else (y-1,4)
def dio(c,y,q):
    a,b=F.get((c,y,q)),F.get((c,)+prevq(y,q))
    if not a or not b or not a['inv'] or not b['inv'] or not a['cogs_q']: return None
    k=float(a['cogs_q'])
    if k<=0: return None
    return (float(a['inv'])+float(b['inv']))/2/k*days_q(y,q)
def latest_q(c,cutdt):
    best=None
    for (cc,y,q),r in F.items():
        if cc!=c or not r['upload']: continue
        if dt.datetime.strptime(r['upload'],'%Y-%m-%d %H:%M')<=cutdt and (best is None or (y,q)>best): best=(y,q)
    return best
def used_reports(y,q):
    rs=[(y,q),prevq(y,q),(y-1,q),prevq(y-1,q)]
    if q==4: rs+= [(y,3),(y-1,3)]
    return rs
def fin_status(c,cutdt):
    """回傳 (累庫 True/False/None, 說明)"""
    lq=latest_q(c,cutdt)
    if not lq: return None,'無已公告季報'
    y,q=lq; qend=dt.datetime(y,3*q,[31,30,30,31][q-1])
    if (cutdt-qend).days>180: return None,'季報距截點>180日'
    for (yy,qq) in used_reports(y,q):
        r=F.get((c,yy,qq))
        if not r or not r['upload']: return None,f'缺{yy}Q{qq}'
        if dt.datetime.strptime(r['upload'],'%Y-%m-%d %H:%M')>cutdt: return None,f'{yy}Q{qq}截點時未公告'
        for d in [x for x in r['corr_dates_flag'].split(';') if x]:
            if dt.datetime.strptime(d,'%Y%m%d')>cutdt: return None,f'{yy}Q{qq}截點後更補正({d})'
    a,b=dio(c,y,q),dio(c,y-1,q)
    if a is None or b is None: return None,'DIO無法計算'
    return a>b, f'{y}Q{q} DIO {a:.1f} vs {b:.1f}'
