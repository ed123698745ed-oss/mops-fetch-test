"""038 R03 往前驗證：抓證交所 MI_MARGN（融資融券彙總，全部）官方原檔，日期見 p038/dates_twse.txt（進場前一交易日）。原檔 gzip 存 p038/margin/。"""
import json, gzip, os, sys, time, urllib.request
K,N=(int(sys.argv[1]),int(sys.argv[2])) if len(sys.argv)>2 else (0,1)
UA={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/129.0 Safari/537.36'}
os.makedirs('p038/margin',exist_ok=True)
for j,ds in enumerate(open('p038/dates_twse.txt').read().split()):
    if j%N!=K: continue
    f=f'p038/margin/MI_MARGN_{ds}.json.gz'
    if os.path.exists(f): continue
    url=f'https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date={ds}&selectType=ALL&response=json'
    for i in range(5):
        try:
            d=json.loads(urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=40).read())
            json.dump(d,gzip.open(f,'wt'),ensure_ascii=False); print(ds,d.get('stat'),flush=True); break
        except Exception as e: print('retry',ds,e,flush=True); time.sleep(20*(i+1))
    time.sleep(3)
