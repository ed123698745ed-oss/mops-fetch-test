# 054：財務報告更(補)正詳細資料（電子書清單「詳細資料」按鈕連到的 t56sb31_q1），只抓合併財報(DTYPE=I1)
# 用法：python p054/fetch_corr.py；網址清單 p054/corr_urls.txt；已存在略過；間隔 3 秒
import os, time, gzip, re, urllib.request
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
OUT = "out/p054/corr"; os.makedirs(OUT, exist_ok=True)
log = open("out/p054/corr_log.txt", "a", encoding="utf-8")
for u in [x.strip() for x in open("p054/corr_urls.txt", encoding="utf-8") if x.strip()]:
    cid, ys, dt = re.search(r"CID=(\d+)&YEAR_SEASON=(\d+)&.*DTYPE=(\w+)", u).groups()
    f = f"{OUT}/corr_{cid}_{ys}_{dt}.html.gz"
    if os.path.exists(f): continue
    for a in range(3):
        try:
            b = urllib.request.urlopen(urllib.request.Request(u.replace("http://", "https://"),
                headers={"User-Agent": UA, "Referer": "https://doc.twse.com.tw/"}), timeout=60).read()
            if b"SECURITY" in b[:3000]: log.write(f"{f} 被擋\n"); raise SystemExit(2)
            gzip.open(f, "wb").write(b); log.write(f"{f} {len(b)}\n"); log.flush(); break
        except SystemExit: raise
        except Exception as e:
            log.write(f"{f} 錯誤 {e}\n"); time.sleep(10)
    time.sleep(3)
log.write("完成\n")
