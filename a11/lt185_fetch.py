# A11：證交所 LT185「上市普通股股數增減公告」2019-07～2026-10（R05 起只補抓 2026-01～2026-10），按公告月份抓全部申報種類，原始 JSON 存 out/lt185/data/
import urllib.request, os, json, time, datetime as dt
os.makedirs('out/lt185/data', exist_ok=True)
UA={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/129.0 Safari/537.36','Referer':'https://www.twse.com.tw/zh/page/announcement/LT185.html'}
log=open('out/lt185/fetch_log.txt','a',encoding='utf-8')
d=dt.date(2026,1,1)
while d<dt.date(2026,11,1):
    e=(d.replace(day=28)+dt.timedelta(days=4)).replace(day=1)-dt.timedelta(days=1)
    fn=f'out/lt185/data/lt185_{d:%Y%m}.json'
    u=f'https://www.twse.com.tw/rwd/zh/announcement/LT185?response=json&selectType=&startDate1={d:%Y%m%d}&endDate1={e:%Y%m%d}&startDate2=&endDate2=&stockNo=&checkedtdr=false'
    for k in range(3):
        try:
            t=urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=60).read().decode('utf-8','replace')
            j=json.loads(t); break
        except Exception as ex:
            log.write(f'{d} err {ex}\n'); time.sleep(15); j=None; t=''
    json.dump({'url':u,'retrieved_at':dt.datetime.now(dt.timezone.utc).isoformat(),'response':j},open(fn,'w',encoding='utf-8'),ensure_ascii=False)
    log.write(f'{d} {len((j or {}).get("data") or [])} rows date={((j or {}).get("date"))}\n'); log.flush()
    time.sleep(4)
    d=e+dt.timedelta(days=1)
