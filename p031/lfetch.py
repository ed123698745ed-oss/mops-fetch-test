# 本機（雲端工作區）補抓：與 p031/fetch.py 相同資料集與參數，逐筆節流
import json, os, sys, time, urllib.request, urllib.parse, urllib.error, csv, gzip
API = "https://api.finmindtrade.com/api/v4/data"; OUT = "data/out/p031"; END = "2026-10-21"; START = "2009-12-01"
def get(params, path):
    if os.path.exists(path): return True
    url = API + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=90) as r: d = json.load(r)
    except urllib.error.HTTPError as e:
        d = json.loads(e.read().decode("utf-8", "ignore") or "{}")
    if d.get("status") != 200: print("FAIL", params.get("data_id"), params["dataset"], str(d.get("msg"))[:60], flush=True); return False
    rows = d.get("data", [])
    if path.endswith(".csv.gz"):
        with gzip.open(path, "wt", encoding="utf-8", newline="") as g:
            if rows: w = csv.DictWriter(g, list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    else: json.dump({"status": 200, "data": rows}, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    return True
get({"dataset": "TaiwanStockSplitPrice", "start_date": START, "end_date": END}, f"{OUT}/_SplitPrice_all.json")
for c in [l.strip() for l in open(sys.argv[1]) if l.strip()]:
    for ds in ("TaiwanStockPrice", "TaiwanStockDividendResult", "TaiwanStockCapitalReductionReferencePrice"):
        ext = "csv.gz" if ds == "TaiwanStockPrice" else "json"
        if not get({"dataset": ds, "data_id": c, "start_date": START, "end_date": END}, f"{OUT}/{c}_{ds}.{ext}"): time.sleep(600); continue
        time.sleep(11)
    print("OK", c, flush=True)
