# 058 正式策略包 V02／R01：樣本內＋樣本外（事前登記見 058_正式策略包_樣本外檢定事前登記_20261105.json）
# 用法：V058=''（策略卡組合）或 'T'（E-Test T 版）；DIR=orig（多減速下游、空累庫上游）或 rev（多累庫上游、空減速下游）；DECEL=連續減速次數（主值 2）
import sys, os, csv, collections, datetime as dt, statistics as st
sys.path.insert(0,'/home/claude/w058/code'); import signals as S, engine as E
DIR=os.environ.get('DIR','orig'); DECEL=int(os.environ.get('DECEL','2')); TAG=os.environ.get('TAG','')
IS_FIRST,IS_LAST='20140615','20220715'; ISO=('20220815','20220915'); OOS_FIRST,OOS_LAST='20221015','20260915'
cuts=[f"{y}{m:02d}15" for y in range(2014,2027) for m in range(1,13) if IS_FIRST<=f"{y}{m:02d}15"<=OOS_LAST and f"{y}{m:02d}15" not in ISO]
if os.environ.get('ISONLY'): cuts=[c for c in cuts if c<=IS_LAST]   # 除錯用：只跑樣本內
def sample(cut):
    if cut<=IS_LAST: return '樣本內'
    return '樣本外'
def latest(cut): return '20251015'<=cut<=OOS_LAST   # 最新年度＝樣本外最後 12 批（樣本外子集，非另一次檢定）
# ---- 減資換股比與每股退還現金：只用公司重大訊息原文（red_ratio.csv）；查無者該腿列未完成 ----
RR={}
if os.path.exists('/home/claude/w058/red_ratio.csv'):
    for r in csv.DictReader(open('/home/claude/w058/red_ratio.csv',encoding='utf-8')):
        RR[(r['code'],r['date'])]=(float(r['swap']),float(r['refund']),r['src'])
def leg_events(c):
    evs=[dict(date=E.pd_dt(e['date']),cash=e.get('cash',0),stock=e.get('stock',0)) for e in E.EV[c]]
    for d in E.RED[c]:
        if (c,d) in RR: sw,rf,_=RR[(c,d)]; evs.append(dict(date=E.pd_dt(d),swap=sw,refund=rf))
    return evs
def leg_return(c,ed,ep,xd,xp): return E.ET.share_return(E.pd_dt(ed),ep,E.pd_dt(xd),xp,leg_events(c))
def leg_flags(c,ed,xd):
    gap=[];flag=[];seo=[]
    for s in E.SEO[c]:
        if s['date'] and ed<s['date']<=xd: flag.append(f"現增除權{s['date']}（不認購）"); seo.append(s['date'])
    for r in E.RED[c]:
        if ed<r<=xd:
            if (c,r) in RR: flag.append(f"減資恢復買賣{r}（換股比{RR[(c,r)][0]}、退還{RR[(c,r)][1]}元，{RR[(c,r)][2]}）")
            else: gap.append(f'減資恢復買賣{r}換股比未取得')
    return gap,flag,seo
def elig(c,cut):
    sd=max(x for x in E.TD if x<=cut); i=E.TI[sd]; win=E.TD[i-20:i]
    x=E.PX[c].get(sd); lst=E.LIST.get(c,'')
    if not x or not x['c']: return False,'訊號日無收盤'
    if lst and lst>win[0]: return False,'未滿上市櫃20日'
    if x['c']<10: return False,'收盤<10元'
    a=sum(E.PX[c][d]['a'] if d in E.PX[c] else 0 for d in win)/20
    if a<5e7: return False,'20日均額<5000萬'
    return True,''
legs=[]; baskets=[]; sigrows=[]; busy={}
for cut in cuts:
    y,m=int(cut[:4]),int(cut[4:6]); cutdt=dt.datetime(y,m,15,23,59)
    rm=(y,m-1) if m>1 else (y-1,12)
    entry=E.nxt(cut); nextcut=f"{y+(m==12)}{(m%12)+1:02d}15"; xt=E.nxt(nextcut)
    role={}
    for sub,mem in S.SUB.items():
        for c in mem['D']:
            ok,why=elig(c,cut); g=[S.G3(c,S.add(rm,-i)) for i in range(DECEL+1)]
            if not ok: st_=None; why2=why
            elif None in g: st_=None; why2='G3不足'
            elif S.rev_unverified(c,rm,cut): st_=None; why2='營收版本未驗證'
            else:
                st_=all(g[i]<g[i+1] for i in range(DECEL)); why2=('G3 '+'<'.join(f'{v:.4f}' for v in g)) if st_ else f'G3未連{DECEL}次減速'
            role[(sub,'D',c)]=(st_,why2)
        for c in mem['U']:
            ok,why=elig(c,cut)
            if not ok: role[(sub,'U',c)]=(None,why); continue
            a,why2=S.fin_status(c,cutdt); role[(sub,'U',c)]=(a,why2)
    both=set()
    for ch in set(S.CHAIN.values()):
        subs=[s for s in S.SUB if S.CHAIN[s]==ch]
        dset={c for s in subs for c in S.SUB[s]['D'] if role[(s,'D',c)][0]}
        uset={c for s in subs for c in S.SUB[s]['U'] if role[(s,'U',c)][0]}
        both|={(ch,c) for c in dset&uset}
    for (sub,r,c),(v,why) in role.items():
        sigrows.append(dict(cut=cut,sub=sub,role=r,code=c,signal=v,why=why,both_role_excluded=(S.CHAIN[sub],c) in both))
    for sub,mem in S.SUB.items():
        ch=S.CHAIN[sub]
        Dn=[c for c in mem['D'] if role[(sub,'D',c)][0] and (ch,c) not in both]
        Up=[c for c in mem['U'] if role[(sub,'U',c)][0] and (ch,c) not in both]
        L,Sh=(Dn,Up) if DIR=='orig' else (Up,Dn)
        rec=dict(cut=cut,sample=sample(cut),latest=latest(cut),sub=sub,entry=entry,longs=' '.join(L),shorts=' '.join(Sh),status='',reason='',
                 ret=None,ret_cash=None,ret_loss=None,rl=None,rs=None,exit='',hold=None,gap='',flag='')
        if not L or not Sh: rec['status']='無訊號'; baskets.append(rec); continue
        if busy.get(sub) and busy[sub]>entry: rec['status']='暫停'; rec['reason']=f'前期部位未平倉至{busy[sub]}'; baskets.append(rec); continue
        fail=[]
        for side,cs in (('L',L),('S',Sh)):
            for c in cs:
                ok,why=E.can_enter(c,entry,side)
                if not ok: fail.append(f'{c}{side}:{why}')
        if fail: rec['status']='取消'; rec['reason']='；'.join(fail); baskets.append(rec); continue
        R={'L':[],'S':[]}; RC={'L':[],'S':[]}; RLs={'L':[],'S':[]}; xs=[]; gaps=[]; flags=[]
        for side,cs in (('L',L),('S',Sh)):
            for c in cs:
                ep=E.PX[c][entry]['o']; xd,xp,dl=E.exit_day(c,xt,side)
                if xd is None:
                    gaps.append(f'{c}無出場價'); legs.append(dict(cut=cut,sample=sample(cut),sub=sub,side=side,code=c,entry=entry,entry_px=ep,exit='',exit_px='',delay=dl,hold='',ret='',ret_cash='',ret_loss='',gap='無出場價',flag=''))
                    continue
                g,f,seo=leg_flags(c,entry,xd)
                r=None if g else leg_return(c,entry,ep,xd,xp)
                rc=rl_=r
                if seo and r is not None:
                    d0=min(seo); pdd=max(x for x in E.TD if x<d0 and E.PX[c].get(x) and E.PX[c][x]['c'])
                    rc=leg_return(c,entry,ep,pdd,E.PX[c][pdd]['c'])   # 留現金：除權前一交易日收盤出清
                    rl_=-1.0 if side=='L' else 1.0                      # 全損：該腿損失全部名目
                legs.append(dict(cut=cut,sample=sample(cut),sub=sub,side=side,code=c,entry=entry,entry_px=ep,exit=xd,exit_px=xp,delay=dl,
                                 hold=E.TI[xd]-E.TI[entry],ret=r,ret_cash=rc,ret_loss=rl_,gap='；'.join(g),flag='；'.join(f)))
                xs.append(xd)
                if g: gaps+=[f'{c}{x}' for x in g]
                else: R[side].append(r); RC[side].append(rc); RLs[side].append(rl_)
                if f: flags+=[f'{c}{x}' for x in f]
        rec['exit']=max(xs) if xs else ''; rec['hold']=E.TI[rec['exit']]-E.TI[entry] if xs else None
        busy[sub]=rec['exit'] or busy.get(sub); rec['flag']='；'.join(flags)
        if gaps: rec['status']='未完成'; rec['gap']='；'.join(gaps)
        else:
            rec['status']='成交'; rec['rl']=st.mean(R['L']); rec['rs']=st.mean(R['S']); rec['ret']=(rec['rl']-rec['rs'])/2
            rec['ret_cash']=(st.mean(RC['L'])-st.mean(RC['S']))/2; rec['ret_loss']=(st.mean(RLs['L'])-st.mean(RLs['S']))/2
        baskets.append(rec)
name=f"{'T' if S.V=='T' else 'C'}_{DIR}_d{DECEL}{TAG}"
OUT=f'/home/claude/w058/out_fp/{name}'; os.makedirs(OUT,exist_ok=True)
def dump(fn,rows):
    if not rows: return
    cols=list(rows[0].keys()); w=csv.DictWriter(open(f'{OUT}/{fn}','w',encoding='utf-8',newline=''),fieldnames=cols); w.writeheader(); w.writerows(rows)
dump('signals.csv',sigrows); dump('baskets.csv',baskets); dump('legs.csv',legs)
c=collections.Counter((b['sample'],b['status']) for b in baskets); print(name,sorted(c.items()))
