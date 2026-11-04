# 054：公開資訊觀測站公司基本資料（ajax_t05st03，含「主要經營業務」）；用於主業判定證據
import os, time, gzip, urllib.request, urllib.parse
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
OUT = "out/p054/basic"; os.makedirs(OUT, exist_ok=True)
log = open("out/p054/basic_log.txt", "a", encoding="utf-8")
codes = [l.split(",")[0] for l in open("p054/codes_054all.txt", encoding="utf-8") if l[:1].isdigit()]
for c in codes:
    f = f"{OUT}/t05st03_{c}.html.gz"
    if os.path.exists(f) and os.path.getsize(f) > 200: continue
    body = urllib.parse.urlencode({"encodeURIComponent": 1, "step": 1, "firstin": 1, "off": 1, "keyword4": "", "code1": "",
                                   "TYPEK2": "", "checkbtn": "", "queryName": "co_id", "inpuType": "co_id", "TYPEK": "all", "co_id": c}).encode()
    try:
        b = urllib.request.urlopen(urllib.request.Request("https://mopsov.twse.com.tw/mops/web/ajax_t05st03", data=body,
            headers={"User-Agent": UA, "Referer": "https://mopsov.twse.com.tw/mops/web/t05st03"}), timeout=60).read()
        if b"SECURITY" in b[:3000]: log.write(f"{c} 被擋\n"); raise SystemExit(2)
        gzip.open(f, "wb").write(b); log.write(f"{c} {len(b)}\n"); log.flush()
    except SystemExit: raise
    except Exception as e: log.write(f"{c} 錯誤 {e}\n")
    time.sleep(3)
log.write("完成\n")
