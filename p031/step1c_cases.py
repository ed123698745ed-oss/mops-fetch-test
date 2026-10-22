# 031 步驟1c：組案件——A＝首次確認會計師端主動退出（同一舊所365日內之後續公告併同案）、A接任狀態、B＝同案首次公告已委任接任；比較組同公司同(舊所,新所)90日內只取首次
import pandas as pd, re, datetime as dt
s=pd.read_pickle('cls2.pkl'); s=s[~s['子公司'].astype(bool)].copy()
def nf(x): return re.sub(r'思','施',re.sub(r'[\s()（）「」、,，.。:：\'"]|聯合|會計師事務所|會計事務所|事務所|會計師務所','',x or ''))[:6]
PEND=r'洽談|遴選|尚未|未定|待|暫缺|評估|物色|覓'
def named(x):
    x=x or ''
    if re.search(PEND,x) or re.fullmatch(r'(不適用|不適⽤|無|NA|N/A|-|)[。.]?',x.strip()): return False
    return bool(re.search(r'事務所|會計|CPA|LLP|Corporation|Accounting|&|Young|KPMG|Price|Deloitte',x,re.I))
def status(x):
    if named(x): return '已委任'
    if re.search(PEND,x or ''): return '明確尚未委任'
    return '未說明'
D=lambda t: dt.datetime.strptime(t[:8],'%Y%m%d')
used=set(); A=[]; 
for c,g in s.groupby('公司代號'):
    g=g.sort_values('ts')
    rows=list(g.itertuples())
    for i,r in enumerate(rows):
        if r.Index in used or r.分類!='主動退出': continue
        if nf(r.oldfirm) in ('','不適用','無'): continue
        if (re.search(r'解任',r.f8) and not re.search(r'來函',r.f8)) or (re.search(r'公司.{0,8}(營運|管理|業務|內部|需求|需要|考量)|強化公司治理',r.f8) and not re.search(r'會計師|事務所',r.f8)) or re.search(r'公司不再繼續接受',r.f9):
            s.loc[r.Index,'分類']='不明'; continue
        ofirm=nf(r.oldfirm)
        case=[r]; used.add(r.Index); B=None
        st=status(r.newfirm)
        for q in rows[i+1:]:
            if (D(q.ts)-D(r.ts)).days>365: break
            qo=nf(q.oldfirm)
            if qo in (ofirm,'','不適用','無') or ofirm=='' or qo[:2]==ofirm[:2] or (B is not None and q.ts[:8]<=str(int(B.ts[:8])+20000) and q.分類=='主動退出' and nf(B.newfirm)==qo and re.search(r'原|擬委任',q.f9)):
                case.append(q); used.add(q.Index)
                if B is None and named(q.newfirm) and st!='已委任': B=q
            elif q.分類=='主動退出': break
        A.append(dict(事件ID=f'A-{c}-{r.ts[:8]}',公司代號=c,公司名稱=r.公司名稱,S日期=r.發言日期,S時間=r.發言時間.zfill(6),主旨=r.主旨.replace('\n',''),
            舊所=r.oldfirm,A時新所欄=r.newfirm,A接任狀態=st,F9=r.f9,F8=r.f8[:120],
            B日期=(B.發言日期 if B is not None else ''),B時間=(B.發言時間.zfill(6) if B is not None else ''),B新所=(B.newfirm if B is not None else ''),
            公告鏈=';'.join(x.發言日期+x.發言時間.zfill(6) for x in case)))
A=pd.DataFrame(A); A.to_csv('A_events.csv',index=False,encoding='utf-8-sig')
# 比較組
C=[]
for c,g in s.groupby('公司代號'):
    last={}
    for r in g.sort_values('ts').itertuples():
        if r.Index in used or r.分類=='主動退出': continue
        key=(nf(r.oldfirm),nf(r.newfirm))
        if key in last and (D(r.ts)-D(last[key])).days<=90: continue
        last[key]=r.ts
        C.append(dict(事件ID=f'C-{c}-{r.ts[:8]}-{len(C)}',公司代號=c,公司名稱=r.公司名稱,S日期=r.發言日期,S時間=r.發言時間.zfill(6),分類=r.分類,主旨=r.主旨.replace('\n',''),舊所=r.oldfirm,新所=r.newfirm,F9=r.f9,F8=r.f8[:120]))
C=pd.DataFrame(C); C.to_csv('C_events.csv',index=False,encoding='utf-8-sig')
print('A cases',len(A)); print(A['A接任狀態'].value_counts()); print('B晚於A',(A['B日期']!='').sum())
print(C['分類'].value_counts())
print(A[['事件ID','A接任狀態','B日期','舊所','A時新所欄']].to_string())
