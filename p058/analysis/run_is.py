# 058 S2 樣本內快篩：只跑凍結紀錄的樣本內形成截點 2014-06-15～2022-07-15；樣本外不計算
import sys, csv, collections, datetime as dt, statistics as st
sys.path.insert(0,'/home/claude/w058/code'); import signals as S, engine as E
IS_FIRST,IS_LAST='20140615','20220715'
cuts=[f"{y}{m:02d}15" for y in range(2014,2023) for m in range(1,13) if IS_FIRST<=f"{y}{m:02d}15"<=IS_LAST]
def elig(c,cut):
    sd=max(x for x in E.TD if x<=cut); i=E.TI[sd]; win=E.TD[i-20:i]
    x=E.PX[c].get(sd); lst=E.LIST.get(c,'')
    if not x or not x['c']: return False,'訊號日無收盤'
    if lst and lst>win[0]: return False,'未滿上市櫃20日'
    if x['c']<10: return False,'收盤<10元'
    a=sum(E.PX[c][d]['a'] if d in E.PX[c] else 0 for d in win)/20
    if a<5e7: return False,'20日均額<5000萬'
    return True,''
legs=[]; baskets=[]; sigrows=[]
busy={}   # 子鏈 -> 最後出場日（未平倉資金不可重用）
for k,cut in enumerate(cuts):
    y,m=int(cut[:4]),int(cut[4:6]); cutdt=dt.datetime(y,m,15,23,59)
    rm=(y,m-1) if m>1 else (y-1,12)
    entry=E.nxt(cut); nextcut=f"{y+(m==12)}{(m%12)+1:02d}15"; xt=E.nxt(nextcut)
    # 角色判定
    role={}
    for sub,mem in S.SUB.items():
        for c in mem['D']:
            ok,why=elig(c,cut); g=[S.G3(c,S.add(rm,-i)) for i in range(3)]
            if not ok: st_=None; why2=why
            elif None in g: st_=None; why2='G3不足'
            elif S.rev_unverified(c,rm,cut): st_=None; why2='營收版本未驗證'
            else: st_=g[0]<g[1]<g[2]; why2=f'G3 {g[0]:.4f}<{g[1]:.4f}<{g[2]:.4f}' if st_ else 'G3未連兩次減速'
            role[(sub,'D',c)]=(st_,why2)
        for c in mem['U']:
            ok,why=elig(c,cut)
            if not ok: role[(sub,'U',c)]=(None,why); continue
            a,why2=S.fin_status(c,cutdt); role[(sub,'U',c)]=(a,why2)
    # 同鏈同月同時符合兩角色者兩邊排除
    both=set()
    for ch in set(S.CHAIN.values()):
        subs=[s for s in S.SUB if S.CHAIN[s]==ch]
        dset={c for s in subs for c in S.SUB[s]['D'] if role[(s,'D',c)][0]}
        uset={c for s in subs for c in S.SUB[s]['U'] if role[(s,'U',c)][0]}
        both|={(ch,c) for c in dset&uset}
    for (sub,r,c),(v,why) in role.items():
        sigrows.append([cut,sub,r,c,v,why,(S.CHAIN[sub],c) in both])
    for sub,mem in S.SUB.items():
        ch=S.CHAIN[sub]
        L=[c for c in mem['D'] if role[(sub,'D',c)][0] and (ch,c) not in both]
        Sh=[c for c in mem['U'] if role[(sub,'U',c)][0] and (ch,c) not in both]
        rec=dict(cut=cut,sub=sub,entry=entry,longs=' '.join(L),shorts=' '.join(Sh),status='',reason='',ret=None,ret_s1=None,rl=None,rs=None,exit='',hold=None,gap='')
        if not L or not Sh: rec['status']='無訊號'; baskets.append(rec); continue
        if busy.get(sub) and busy[sub]>entry: rec['status']='暫停'; rec['reason']=f'前期部位未平倉至{busy[sub]}'; baskets.append(rec); continue
        fail=[]
        for side,cs in (('L',L),('S',Sh)):
            for c in cs:
                ok,why=E.can_enter(c,entry,side)
                if not ok: fail.append(f'{c}{side}:{why}')
        if fail: rec['status']='取消'; rec['reason']='；'.join(fail); baskets.append(rec); continue
        rL=[];rS=[];rL1=[];rS1=[];xs=[];g=[]
        for side,cs in (('L',L),('S',Sh)):
            for c in cs:
                ep=E.PX[c][entry]['o']; xd,xp,dl=E.exit_day(c,xt,side)
                if xd is None: g.append(f'{c}無出場價'); continue
                r=E.leg_return(c,entry,ep,xd,xp); gp=E.gaps(c,entry,xd)
                legs.append(dict(cut=cut,sub=sub,side=side,code=c,entry=entry,entry_px=ep,exit=xd,exit_px=xp,delay=dl,ret=r,gap='；'.join(gp),
                                 hold=E.TI[xd]-E.TI[entry]))
                (rL1 if side=='L' else rS1).append(r)
                if gp: g+= [f'{c}{x}' for x in gp]
                else: (rL if side=='L' else rS).append(r)
                xs.append(xd)
        rec['exit']=max(xs) if xs else ''; rec['hold']=E.TI[rec['exit']]-E.TI[entry] if xs else None
        busy[sub]=rec['exit'] or busy.get(sub)
        rec['ret_s1']=(st.mean(rL1)-st.mean(rS1))/2 if rL1 and rS1 else None
        if g: rec['status']='未完成'; rec['gap']='；'.join(g)
        else:
            rec['status']='成交'; rec['rl']=st.mean(rL); rec['rs']=st.mean(rS); rec['ret']=(rec['rl']-rec['rs'])/2
        baskets.append(rec)
W='/home/claude/w058/out'; import os; os.makedirs(W,exist_ok=True)
def dump(name,rows,cols):
    w=csv.writer(open(f'{W}/{name}',"w",encoding='utf-8',newline='')); w.writerow(cols)
    for r in rows: w.writerow([r.get(c,'') if isinstance(r,dict) else r[i] for i,c in enumerate(cols)])
dump('signals_is.csv',sigrows,['cut','sub','role','code','signal','why','both_role_excluded'])
dump('baskets_is.csv',baskets,['cut','sub','entry','exit','hold','longs','shorts','status','reason','gap','rl','rs','ret','ret_s1'])
dump('legs_is.csv',legs,['cut','sub','side','code','entry','entry_px','exit','exit_px','delay','hold','ret','gap'])
c=collections.Counter((b['status']) for b in baskets); print(c)
print(collections.Counter(b['sub'] for b in baskets if b['status']=='成交'))
