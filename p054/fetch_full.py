# 054 全量抓取（D-054-20261104-1940-1，試抓可行後續做）
# 1) 資產負債表 ajax_t164sb03：71 檔種子 × 民國102Q1～115Q2，保存原始 HTML(gzip)
# 2) 電子書 t57sb01：71 檔 × 民國102～115 年財報檔案清單（含上傳日期、更補正欄），保存原始 HTML(gzip)
# 用法：python p054/fetch_full.py <slice> <nslices>；已存在的檔案略過（可接力）；每次請求間隔 3 秒
import os, sys, time, gzip, urllib.request, urllib.parse
k, n = int(sys.argv[1]), int(sys.argv[2])
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
OUT = "out/p054/raw"; os.makedirs(OUT, exist_ok=True)
codes = [x.strip() for x in open("p054/codes_054.txt", encoding="utf-8") if x.strip() and not x.startswith("#")]
codes = [c.split(",")[0] for c in codes][k::n]
log = open(f"out/p054/fetch_log_{k}.txt", "a", encoding="utf-8")
def L(s): print(s); log.write(s + "\n"); log.flush()
DEADLINE = time.time() + 52 * 60

def get(url, data=None, ref=None):
    h = {"User-Agent": UA}
    if ref: h["Referer"] = ref
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode() if data else None, headers=h)
    return urllib.request.urlopen(req, timeout=60).read()

def job(name, fn):
    f = f"{OUT}/{name}.html.gz"
    if os.path.exists(f): return
    for a in range(3):
        try:
            b = fn()
            if b"SECURITY" in b[:3000]:
                L(f"{name} 被擋，停止"); raise SystemExit(2)
            gzip.open(f, "wb").write(b); L(f"{name} {len(b)}"); break
        except SystemExit: raise
        except Exception as e:
            L(f"{name} 第{a+1}次錯誤 {e}"); time.sleep(10)
    time.sleep(3)

quarters = [(y, s) for y in range(102, 116) for s in (1, 2, 3, 4) if (y, s) <= (115, 2)]
for c in codes:
    for y in range(102, 116):
        if time.time() > DEADLINE: L("時間到，下輪接力"); sys.exit(0)
        job(f"doc_{c}_{y}", lambda c=c, y=y: get(
            f"https://doc.twse.com.tw/server-java/t57sb01?step=1&colorchg=1&co_id={c}&year={y}&mtype=A&"))
    for y, s in quarters:
        if time.time() > DEADLINE: L("時間到，下輪接力"); sys.exit(0)
        job(f"bs_{c}_{y}Q{s}", lambda c=c, y=y, s=s: get(
            "https://mopsov.twse.com.tw/mops/web/ajax_t164sb03",
            {"encodeURIComponent": 1, "step": 1, "firstin": 1, "off": 1, "queryName": "co_id", "inpuType": "co_id",
             "TYPEK": "all", "isnew": "false", "co_id": c, "year": y, "season": f"{s:02d}"},
            ref="https://mopsov.twse.com.tw/mops/web/t164sb03"))
L(f"slice {k} 完成")
