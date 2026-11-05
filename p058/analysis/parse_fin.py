# 058：解析公開資訊觀測站原始申報（存貨、營業成本、電子書上傳時間、更補正清單）
import gzip, re, os, csv, glob, datetime as dt
R58='/home/claude/mops-fetch-test/out/p058/raw'; R54='/home/claude/mops-fetch-test/out/p054/raw'
CL='/home/claude/mops-fetch-test/out/p054/corrlist'
codes=[x.strip() for x in open('/home/claude/mops-fetch-test/p058/codes_058.txt',encoding='utf-8') if x.strip() and not x.startswith('#')]
def page(name):
    for d in (R58,R54):
        f=f'{d}/{name}.html.gz'
        if os.path.exists(f): return gzip.open(f).read(), f
    return None, None
def cells(b):
    t=b.decode('utf-8','ignore')
    t=re.sub(r'<[^>]+>','|',t); t=re.sub(r'&nbsp;',' ',t); t=re.sub(r'\|[\s|]*\|','|',t)
    return [c.strip() for c in t.split('|')]
def num(s):
    s=s.replace(',','').strip()
    if s in ('','-'): return None
    neg=s.startswith('(') and s.endswith(')')
    s=s.strip('()')
    try: v=float(s)
    except: return None
    return -v if neg else v
def after(cs,label,k):
    """回傳 label 後第 k 個數值欄（金額欄，略過百分比）"""
    for i,c in enumerate(cs):
        if c==label:
            vals=[num(x) for x in cs[i+1:i+1+4*k+4]]
            amt=[v for j,v in enumerate(vals) if j%2==0]
            return amt[:k]
    return None
rows=[]
for c in codes:
    for y in range(102,116):
        for s in (1,2,3,4):
            if (y,s)>(115,2): continue
            bs,fb=page(f'bs_{c}_{y}Q{s}'); is_,fi=page(f'is_{c}_{y}Q{s}')
            inv=cogs_q=cogs_cum=None; basis=''; note=[]
            if bs:
                cs=cells(bs)
                if '合併資產負債表' in ''.join(cs[:40]): basis='合併'
                elif any('資產負債表' in x for x in cs[:40]): basis='個別'
                v=after(cs,'存貨',1); inv=v[0] if v else None
                if v is None and '查無' not in ''.join(cs) and '不存在' not in ''.join(cs): note.append('BS無存貨列')
            if is_:
                cs=cells(is_)
                lab='營業成本合計' if '營業成本合計' in cs else ('營業成本' if '營業成本' in cs else None)
                if lab:
                    v=after(cs,lab,4 if s<4 else 2)
                    if v:
                        if s<4: cogs_q=v[0]; cogs_cum=v[2] if len(v)>2 else None
                        else: cogs_cum=v[0]
            rows.append(dict(code=c,y=y+1911,q=s,basis=basis,inv=inv,cogs_q=cogs_q,cogs_cum=cogs_cum,note=';'.join(note)))
# Q4 單季 = 全年 − Q3 累計
idx={(r['code'],r['y'],r['q']):r for r in rows}
for r in rows:
    if r['q']==4 and r['cogs_cum'] is not None:
        q3=idx.get((r['code'],r['y'],3))
        r['cogs_q']=r['cogs_cum']-q3['cogs_cum'] if q3 and q3['cogs_cum'] is not None else None
# 電子書上傳時間（AI1 合併財報，無則 AI3/A 其他中文版最早）
up={}
for c in codes:
    for y in range(102,116):
        b,f=page(f'doc_{c}_{y}')
        if not b: continue
        t=b.decode('big5','ignore')
        for m in re.finditer(r'(\d{4})(\d{2})_%s_(A[^.]*)\.pdf.*?(\d{3})/(\d{2})/(\d{2}) (\d{2}):(\d{2}):(\d{2})'%c,t,re.S):
            yy,qq,kind=int(m.group(1)),int(m.group(2)),m.group(3)
            if kind.endswith('A') : continue   # 英文版
            ts=dt.datetime(int(m.group(4))+1911,int(m.group(5)),int(m.group(6)),int(m.group(7)),int(m.group(8)))
            key=(c,yy,qq); pri=0 if kind=='AI1' else 1
            if key not in up or (pri,ts)<up[key]: up[key]=(pri,ts)
# 更補正
corr={}
KW=re.compile(r'存貨|營業成本|資產負債|損益表|四大報表|財務報表|XBRL',re.I)
for f in sorted(glob.glob(f'{CL}/list_*.html.gz')):
    yq=re.search(r'list_(\d{4})(\d{2})_',f); yy,qq=int(yq.group(1)),int(yq.group(2))
    cs=cells(gzip.open(f).read())
    for i,x in enumerate(cs):
        if x in codes and i+4<len(cs) and re.fullmatch(r'\d{8}',cs[i+2] or ''):
            desc=cs[i+3]+' '+cs[i+4]
            if '英文' in cs[i+3]: continue
            corr.setdefault((x,yy,qq),[]).append((cs[i+2],bool(KW.search(cs[i+4])),cs[i+4][:80]))
w=csv.writer(open('/home/claude/w058/fund_mops.csv','w',encoding='utf-8',newline=''))
w.writerow(['code','y','q','basis','inv','cogs_q','upload','corr_dates_flag','corr_desc','note'])
for r in rows:
    u=up.get((r['code'],r['y'],r['q'])); cl=corr.get((r['code'],r['y'],r['q']),[])
    w.writerow([r['code'],r['y'],r['q'],r['basis'],r['inv'],r['cogs_q'],u[1].strftime('%Y-%m-%d %H:%M') if u else '',
                ';'.join(d for d,fl,_ in cl if fl),' / '.join(f'{d}:{s}' for d,fl,s in cl),r['note']])
print(len(rows), sum(1 for r in rows if r['inv'] is not None), sum(1 for r in rows if r['cogs_q'] is not None), len(up), sum(len(v) for v in corr.values()))
