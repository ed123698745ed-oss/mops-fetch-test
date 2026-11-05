# 從 sector-tracker 官方每日行情原始檔抽出 63 檔種子日K（未還原）
import gzip, json, os, csv, re
S='/home/claude/ed123698745ed-oss/sector-tracker/archive/raw'
import json,os
codes={r['代號'] for r in csv.DictReader(open('seeds.csv',encoding='utf-8'))}|{c for v in json.load(open('subt.json')).values() for k in v for c in v[k]}
def num(x):
    x=str(x).replace(',','').strip()
    try: return float(x)
    except: return None
w=csv.writer(open('px_all.csv','w',encoding='utf-8',newline='')); w.writerow(['date','code','mkt','open','high','low','close','vol','amt'])
days=set()
for mkt in ('twse','tpex'):
    for f in sorted(os.listdir(f'{S}/{mkt}')):
        d=f[:8]
        if d<'20120101': continue
        try: j=json.load(gzip.open(f'{S}/{mkt}/{f}'))
        except Exception as e: print('bad',f,e); continue
        rows=None
        for tb in j.get('tables',[]):
            fl=tb.get('fields') or []
            if mkt=='twse' and fl[:2]==['證券代號','證券名稱']: rows=[(r[0],r[5],r[6],r[7],r[8],r[2],r[4]) for r in tb['data']]
            if mkt=='tpex' and fl and fl[0].strip()=='代號': rows=[(r[0],r[4],r[5],r[6],r[2],r[7],r[8]) for r in tb['data']]
        if rows is None:
            if j.get('stat') not in (None,'OK','ok'): pass
            continue
        days.add((d,mkt))
        for r in rows:
            c=r[0].strip()
            if c in codes: w.writerow([d,c,mkt]+[num(x) for x in r[1:]])
print(len(days))
