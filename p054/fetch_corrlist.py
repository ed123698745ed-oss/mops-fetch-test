# 054：財務報告更(補)正查詢（ajax_t56sb31）各年季清單，用來取得更補正日期；上市 sii、上櫃 otc
import os, time, gzip, urllib.request, urllib.parse
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
OUT = "out/p054/corrlist"; os.makedirs(OUT, exist_ok=True)
log = open("out/p054/corrlist_log.txt", "a", encoding="utf-8")
for y in range(2013, 2027):
    for s in (1, 2, 3, 4):
        if (y, s) > (2026, 2): continue
        for tk in ("sii", "otc"):
            f = f"{OUT}/list_{y}{s:02d}_{tk}.html.gz"
            if os.path.exists(f): continue
            body = urllib.parse.urlencode({"encodeURIComponent": 1, "step": 1, "firstin": 1, "off": 1, "isQuery": "Y",
                                           "TYPEK": tk, "year": y - 1911, "season": f"{s:02d}"}).encode()
            try:
                b = urllib.request.urlopen(urllib.request.Request("https://mopsov.twse.com.tw/mops/web/ajax_t56sb31_q1", data=body,
                    headers={"User-Agent": UA, "Referer": "https://mopsov.twse.com.tw/mops/web/t56sb31_q1"}), timeout=60).read()
                if b"SECURITY" in b[:3000]: log.write(f"{f} 被擋\n"); raise SystemExit(2)
                gzip.open(f, "wb").write(b); log.write(f"{f} {len(b)}\n"); log.flush()
            except SystemExit: raise
            except Exception as e: log.write(f"{f} 錯誤 {e}\n")
            time.sleep(3)
log.write("完成\n")
