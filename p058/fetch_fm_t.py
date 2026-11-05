# 058 E-Test T 版：FinMind 匿名下載下游月營收與全部成分公司行動；已存在者略過
import json, os, sys, time, urllib.request, urllib.parse, urllib.error
k, n = int(sys.argv[1]), int(sys.argv[2])
API = "https://api.finmindtrade.com/api/v4/data"
rd = lambda p: [x.strip() for x in open(p, encoding="utf-8") if x.strip() and not x.startswith("#")]
jobs = [("TaiwanStockMonthRevenue", c, "2011-01-01") for c in rd("p058/codes_058t_dn.txt")]
jobs += [(ds, c, "2012-01-01") for c in rd("p058/codes_058t_all.txt") for ds in ("TaiwanStockDividend", "TaiwanStockDividendResult", "TaiwanStockCapitalReductionReferencePrice")]
jobs = jobs[k::n]
os.makedirs("out/p058/ca", exist_ok=True); os.makedirs("out/p058/rev", exist_ok=True)
DEADLINE = time.time() + 50 * 60
for ds, c, st in jobs:
    out = f"out/p058/{'rev' if ds.endswith('Revenue') else 'ca'}/{ds}_{c}.json"
    if os.path.exists(out) or os.path.exists(f"out/p054/px/{ds}_{c}.json"): continue
    url = API + "?" + urllib.parse.urlencode({"dataset": ds, "data_id": c, "start_date": st, "end_date": "2026-11-05"})
    while time.time() < DEADLINE:
        try: d = json.load(urllib.request.urlopen(url, timeout=90))
        except urllib.error.HTTPError as e:
            try: d = json.loads(e.read().decode("utf-8", "ignore"))
            except Exception: d = {"status": e.code}
        except Exception as e: print("ERR", e, flush=True); time.sleep(20); continue
        if d.get("status") == 200:
            json.dump(d, open(out, "w", encoding="utf-8"), ensure_ascii=False); print("OK", ds, c, len(d["data"]), flush=True); break
        print("WAIT", str(d.get("msg"))[:80], flush=True); time.sleep(90)
print("DONE")
