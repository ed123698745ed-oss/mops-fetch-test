# 058 季報原始申報版本：資產負債表 ajax_t164sb03（存貨）、綜合損益表 ajax_t164sb04（營業成本）、電子書 t57sb01（上傳時間）
# 63 檔種子 × 民國102Q1～115Q2；054 已抓過的資產負債表與電子書清單（19 檔）不重抓，直接沿用 out/p054/raw
# 用法：python p058/fetch_fin.py <slice> <nslices>；已存在略過（可接力）；每次請求間隔 3 秒
import os, sys, time, gzip, urllib.request, urllib.parse
k, n = int(sys.argv[1]), int(sys.argv[2])
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
OUT = "out/p058/raw"; P54 = "out/p054/raw"; os.makedirs(OUT, exist_ok=True)
codes = [x.strip() for x in open(os.environ.get("CODES", "p058/codes_058.txt"), encoding="utf-8") if x.strip() and not x.startswith("#")][k::n]
log = open(f"out/p058/fin_log{os.environ.get('LOGTAG', '')}_{k}.txt", "a", encoding="utf-8")
def L(s): print(s, flush=True); log.write(s + "\n"); log.flush()
DEADLINE = time.time() + 52 * 60
def get(url, data=None, ref=None):
    h = {"User-Agent": UA}
    if ref: h["Referer"] = ref
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode() if data else None, headers=h)
    return urllib.request.urlopen(req, timeout=60).read()
def job(name, fn):
    f = f"{OUT}/{name}.html.gz"
    if os.path.exists(f) or os.path.exists(f"{P54}/{name}.html.gz"): return
    if time.time() > DEADLINE: L("時間到，下輪接力"); sys.exit(0)
    for a in range(3):
        try:
            b = fn()
            if b"SECURITY" in b[:3000]: L(f"{name} 被擋，停止"); raise SystemExit(2)
            gzip.open(f, "wb").write(b); L(f"{name} {len(b)}"); break
        except SystemExit: raise
        except Exception as e: L(f"{name} 第{a+1}次錯誤 {e}"); time.sleep(10)
    time.sleep(3)
quarters = [(y, s) for y in range(102, 116) for s in (1, 2, 3, 4) if (y, s) <= (115, 2)]
def q(api, c, y, s):
    return get(f"https://mopsov.twse.com.tw/mops/web/ajax_{api}",
               {"encodeURIComponent": 1, "step": 1, "firstin": 1, "off": 1, "queryName": "co_id", "inpuType": "co_id",
                "TYPEK": "all", "isnew": "false", "co_id": c, "year": y, "season": f"{s:02d}"},
               ref=f"https://mopsov.twse.com.tw/mops/web/{api}")
for c in codes:
    for y in range(102, 116):
        job(f"doc_{c}_{y}", lambda c=c, y=y: get(f"https://doc.twse.com.tw/server-java/t57sb01?step=1&colorchg=1&co_id={c}&year={y}&mtype=A&"))
    for y, s in quarters:
        job(f"is_{c}_{y}Q{s}", lambda c=c, y=y, s=s: q("t164sb04", c, y, s))
        job(f"bs_{c}_{y}Q{s}", lambda c=c, y=y, s=s: q("t164sb03", c, y, s))
L(f"slice {k} 完成")
