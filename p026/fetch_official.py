# 026 R04：在 GitHub Actions 抓官方個股日成交資訊（證交所上市、櫃買上櫃），原始回應存 out/p026_official/
import json, os, time, urllib.request, sys
OUT = "out/p026_official"; os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0"}
need = [l.split() for l in open(sys.argv[1] if len(sys.argv) > 1 else "p026/official_need.txt") if l.strip()]
fail = []
for mkt, code, ym in need:
    path = f"{OUT}/{mkt}_{code}_{ym}.json"
    if os.path.exists(path): continue
    y, m = ym[:4], ym[4:]
    url = (f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={y}{m}01&stockNo={code}" if mkt == "sii"
           else f"https://www.tpex.org.tw/www/zh-tw/afterTrading/tradingStock?code={code}&date={y}/{m}/01&response=json")
    ok = False
    for k in range(6):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read().decode("utf-8", "ignore")
            if raw.lstrip().startswith("<"): raise RuntimeError("blocked page")
            json.dump(json.loads(raw), open(path, "w", encoding="utf-8"), ensure_ascii=False); ok = True; break
        except Exception as e:
            print("retry", url, e, flush=True); time.sleep(60 * (k + 1))
    if not ok: fail.append(url)
    print("ok" if ok else "FAIL", mkt, code, ym, flush=True)
    time.sleep(10 if mkt == "sii" else 3)
open(f"{OUT}/_fail.txt", "w").write("\n".join(fail))
print("done fail", len(fail))
