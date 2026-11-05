# 058：FinMind 匿名下載公司行動（股利政策、除權息結果、減資恢復參考價），63 檔種子；054 已有者略過
import json, os, time, urllib.request, urllib.parse, urllib.error
API = "https://api.finmindtrade.com/api/v4/data"; OUT = "out/p058/ca"; os.makedirs(OUT, exist_ok=True)
P54 = "out/p054/px"
codes = [x.strip() for x in open("p058/codes_058.txt", encoding="utf-8") if x.strip() and not x.startswith("#")]
DS = ["TaiwanStockDividend", "TaiwanStockDividendResult", "TaiwanStockCapitalReductionReferencePrice"]
DEADLINE = time.time() + 50 * 60
for c in codes:
    for ds in DS:
        f = f"{OUT}/{ds}_{c}.json"
        if os.path.exists(f) or os.path.exists(f"{P54}/{ds}_{c}.json"): continue
        url = API + "?" + urllib.parse.urlencode({"dataset": ds, "data_id": c, "start_date": "2012-01-01", "end_date": "2026-11-05"})
        while time.time() < DEADLINE:
            try:
                d = json.load(urllib.request.urlopen(url, timeout=90))
            except urllib.error.HTTPError as e:
                try: d = json.loads(e.read().decode("utf-8", "ignore"))
                except Exception: d = {"status": e.code}
            except Exception as e:
                print("ERR", e, flush=True); time.sleep(20); continue
            if d.get("status") == 200:
                json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False); print("OK", ds, c, len(d["data"]), flush=True); break
            print("WAIT", str(d.get("msg"))[:80], flush=True); time.sleep(90)
print("DONE")
