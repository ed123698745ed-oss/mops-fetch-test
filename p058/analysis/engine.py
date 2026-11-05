# 058 S2 快篩引擎：建籃、可成交檢查（L1＋L2）、出場順延、固定股數加實得現金報酬
import json, csv, sys, collections, datetime as dt
from decimal import Decimal
sys.path.insert(0,'/home/claude/w058/code'); sys.path.insert(0,'/home/claude/w058')
import signals as S
import elon_tools as ET
W='/home/claude/w058'
# ---- 行情 ----
PX=collections.defaultdict(dict); MKT={}
for r in csv.DictReader(open(f'{W}/{"px_all" if S.V=="T" else "px_seeds"}.csv',encoding='utf-8')):
    o=r['open']
    PX[r['code']][r['date']]=dict(o=float(o) if o not in ('',None) else None,h=float(r['high']) if r['high'] else None,
        l=float(r['low']) if r['low'] else None,c=float(r['close']) if r['close'] else None,v=float(r['vol'] or 0),a=float(r['amt'] or 0),mkt=r['mkt'])
TD=sorted({d for c in PX for d in PX[c]})          # 種子聯集交易日
TI={d:i for i,d in enumerate(TD)}
LIST={r['公司代號']:r['初次上市櫃日'].replace('-','') for r in csv.DictReader(open('/home/claude/mops-fetch-test/listing/上市櫃期間表.csv',encoding='utf-8-sig'))}
def nxt(d): 
    for x in TD:
        if x>d: return x
def prev_trade(c,d):
    i=TI[d]-1
    while i>=0:
        x=PX[c].get(TD[i])
        if x and x['c']: return TD[i],x
        i-=1
    return None,None
# ---- 公司行動 ----
LIMOFF={}
import os
def cap(ds,c):
    for p in (f'{W}/raw_ca/{ds}_{c}.json',f'/home/claude/mops-fetch-test/out/p058/ca/{ds}_{c}.json',f'/home/claude/mops-fetch-test/out/p054/px/{ds}_{c}.json'):
        if os.path.exists(p): return p
    return f'{W}/raw_ca/{ds}_{c}.json'
EV=collections.defaultdict(list); SEO=collections.defaultdict(list); RED=collections.defaultdict(list); REF={}
for c in PX:
    try: dv=json.load(open(cap('TaiwanStockDividend',c)))['data']
    except FileNotFoundError: dv=[]
    for x in dv:
        cash=(x.get('CashEarningsDistribution') or 0)+(x.get('CashStatutorySurplus') or 0)
        stk=((x.get('StockEarningsDistribution') or 0)+(x.get('StockStatutorySurplus') or 0))/10
        if cash>0 and x.get('CashExDividendTradingDate'): EV[c].append(dict(date=x['CashExDividendTradingDate'].replace('-',''),cash=cash,src=f"FinMind Dividend {x['date']}"))
        if stk>0 and x.get('StockExDividendTradingDate'): EV[c].append(dict(date=x['StockExDividendTradingDate'].replace('-',''),stock=stk,src=f"FinMind Dividend {x['date']}"))
        if (x.get('CashIncreaseSubscriptionRate') or 0)>0:
            dd=(x.get('StockExDividendTradingDate') or '').replace('-','')
            SEO[c].append(dict(date=dd,rate=x['CashIncreaseSubscriptionRate'],px=x.get('CashIncreaseSubscriptionpRrice'),ann=x.get('date')))
    try: rr=json.load(open(cap('TaiwanStockDividendResult',c)))['data']
    except FileNotFoundError: rr=[]
    for x in rr: REF[(c,x['date'].replace('-',''))]=x['reference_price']
    try: cr=json.load(open(cap('TaiwanStockCapitalReductionReferencePrice',c)))['data']
    except FileNotFoundError: cr=[]
    for x in cr:
        dd=x['date'].replace('-',''); RED[c].append(dd); REF[(c,dd)]=x.get('OpeningReferencePrice') or x.get('PostReductionReferencePrice')
        if x.get('LimitUp') and x.get('LimitDown'): LIMOFF[(c,dd)]=(float(x['LimitUp']),float(x['LimitDown']))
def ref_price(c,d):
    if (c,d) in REF and REF[(c,d)]: return float(REF[(c,d)]),'官方參考價'
    pd_,x=prev_trade(c,d)
    return (x['c'],'前一成交日收盤') if x else (None,'')
def limits(c,d):
    if (c,d) in LIMOFF: return LIMOFF[(c,d)]   # 減資恢復買賣日用官方漲跌停
    ref,src=ref_price(c,d)
    if ref is None: return None,None
    lst=LIST.get(c,'')
    if lst and TI.get(d,0)-TI.get(max([x for x in TD if x<=lst] or [TD[0]]),0)<5: return None,None   # 新上市前五日無漲跌幅
    return ET.limit_prices(ref,f"{d[:4]}-{d[4:6]}-{d[6:]}")
# ---- 融資融券（空方）----
MG={}
for r in csv.DictReader(open(f'{W}/{"margin_all" if S.V=="T" else "margin_up"}.csv',encoding='utf-8')):
    if r['listed']=='1': MG[(r['code'],r['date'])]=(r['note'],r['short_limit'])
MG_DAYS=sorted({r for (_,r) in MG})
def short_ok(c,d):
    """L2：前一營業日融資融券表（備註表明次一營業日狀況）列為標的、註記無 X 或 !、券限額>0；平盤下放空規則期 B～E"""
    pdays=[x for x in TD if x<d]; p=pdays[-1]
    m=MG.get((c,p))
    if not m: return False,'前一營業日融資融券表未列'
    note,lim=m
    if 'X' in note or '!' in note: return False,f'停止融券({note.strip()})'
    try:
        if float(str(lim).replace(',',''))<=0: return False,'券限額0'
    except ValueError: pass
    x=PX[c].get(d); ref,_=ref_price(c,d)
    if x and x['o'] is not None and ref is not None and x['o']<ref-1e-9:
        if '20150824'<=d<='20150918': return False,'規則期C全面禁止平盤下融券'
        pd_,px_=prev_trade(c,d)
        up,dn=limits(c,pd_) if pd_ else (None,None)
        if px_ and (dn is not None and abs(px_['c']-dn)<1e-9 or px_['v']==0): return False,'規則期B前一日跌停或無成交，平盤下不得融券'
        if ('20200320'<=d<='20200609' or '20221024'<=d<='20230223'):
            pp,ppx=prev_trade(c,pd_)
            if ppx and px_ and px_['c']/ppx['c']-1<=-0.035: return False,'規則期D/E前一日跌幅≥3.5%，不得低於前收融券'
    return True,''
# ---- 成交檢查 ----
def can_enter(c,d,side):
    x=PX[c].get(d)
    if not x or x['o'] is None or x['v']==0: return False,'進場日無成交'
    up,dn=limits(c,d)
    if side=='L' and up is not None and abs(x['o']-up)<1e-9: return False,'開盤漲停，無法證實買進成交'
    if side=='S':
        if dn is not None and abs(x['o']-dn)<1e-9: return False,'開盤跌停，無法證實放空成交'
        ok,why=short_ok(c,d)
        if not ok: return False,why
    return True,''
def exit_day(c,d0,side):
    """d0 預定出場日；空方回補遇開盤漲停、多方賣出遇開盤跌停、無成交→順延至可成交日開盤"""
    i=TI[d0]; delay=0
    while i<len(TD):
        d=TD[i]; x=PX[c].get(d)
        if x and x['o'] is not None and x['v']>0:
            up,dn=limits(c,d)
            blocked=(side=='L' and dn is not None and abs(x['o']-dn)<1e-9) or (side=='S' and up is not None and abs(x['o']-up)<1e-9)
            if not blocked: return d,x['o'],delay
        i+=1; delay+=1
    return None,None,delay
def leg_return(c,ed,ep,xd,xp):
    evs=[dict(date=pd_dt(e['date']),cash=e.get('cash',0),stock=e.get('stock',0)) for e in EV[c]]
    return ET.share_return(pd_dt(ed),ep,pd_dt(xd),xp,evs)
def pd_dt(s): return f"{s[:4]}-{s[4:6]}-{s[6:]}"
def gaps(c,ed,xd):
    g=[]
    for s in SEO[c]:
        if s['date'] and ed<s['date']<=xd: g.append(f"現增除權{s['date']}（認購率{s['rate']}‰）")
    for r in RED[c]:
        if ed<r<=xd: g.append(f'減資恢復買賣{r}')
    return g
