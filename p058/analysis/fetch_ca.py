# 058：FinMind 匿名下載公司行動（股利政策、除權息結果、減資恢復參考價）；054 已有者直接複製
import json, os, time, csv, shutil, urllib.request, urllib.parse, urllib.error
API="https://api.finmindtrade.com/api/v4/data"; OUT="raw_ca"; P54='/home/claude/mops-fetch-test/out/p054/px'
codes=sorted({r['代號'] for r in csv.DictReader(open('seeds.csv',encoding='utf-8'))})
DS=['TaiwanStockDividend','TaiwanStockDividendResult','TaiwanStockCapitalReductionReferencePrice']
for c in codes:
    for ds in DS:
        f=f'{OUT}/{ds}_{c}.json'
        if os.path.exists(f): continue
        if os.path.exists(f'{P54}/{ds}_{c}.json'): shutil.copy(f'{P54}/{ds}_{c}.json',f); continue
        url=API+'?'+urllib.parse.urlencode({'dataset':ds,'data_id':c,'start_date':'2012-01-01','end_date':'2026-11-05'})
        while True:
            try:
                d=json.load(urllib.request.urlopen(url,timeout=90))
            except urllib.error.HTTPError as e:
                try: d=json.loads(e.read().decode('utf-8','ignore'))
                except Exception: d={'status':e.code}
            except Exception as e:
                print('ERR',e,flush=True); time.sleep(20); continue
            if d.get('status')==200:
                json.dump(d,open(f,'w',encoding='utf-8'),ensure_ascii=False); print('OK',ds,c,len(d['data']),time.strftime('%H:%M:%S'),flush=True); break
            print('WAIT',str(d.get('msg'))[:80],flush=True); time.sleep(120)
print('DONE')
