# 抽出各子鏈上下游標的之逐日融資融券表狀態：是否列為信用交易標的、註記、券限額（正式策略包起含下游）
import gzip, json, os, csv, sys
sys.path.insert(0,'code'); import signals as S
import json
U=sorted({c for s in S.SUB.values() for c in s['U']+s['D']}|{c for v in json.load(open('subt.json')).values() for c in v['U']+v['D']})  # 正式策略包：反向組合放空下游，一併抽出下游
R='/home/claude/ed123698745ed-oss/sector-tracker/archive/raw'
w=csv.writer(open('margin_all.csv','w',encoding='utf-8',newline='')); w.writerow(['date','mkt','code','listed','note','short_limit'])
for mkt in ('twse_margin','tpex_margin'):
    for f in sorted(os.listdir(f'{R}/{mkt}')):
        d=f[:8]
        if d<'20140501': continue
        try: j=json.load(gzip.open(f'{R}/{mkt}/{f}'))
        except Exception: continue
        rows={}
        for t in j.get('tables',[]):
            fl=t.get('fields') or []
            if mkt=='twse_margin' and fl[:2]==['代號','名稱']:
                for r in t['data']: rows[r[0].strip()]=(r[15].strip() if len(r)>15 else '', r[13])
            if mkt=='tpex_margin' and fl and fl[0].strip()=='代號':
                for r in t['data']: rows[r[0].strip()]=(r[19].strip() if len(r)>19 else '', r[17])
        if not rows: continue
        for c in U:
            if c in rows: w.writerow([d,mkt,c,1,rows[c][0],rows[c][1]])
            else: w.writerow([d,mkt,c,0,'',''])
print('ok')
