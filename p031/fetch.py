# 031 會計師異動策略：FinMind 日K、公司行動抓取（GitHub Actions 執行，匿名額度）
# 用法：python p031/fetch.py <slice_index> <slice_count>；輸出 out/p031/
import json, os, sys, time, urllib.request, urllib.parse, urllib.error, csv, gzip
API = "https://api.finmindtrade.com/api/v4/data"
OUT = "out/p031"; os.makedirs(OUT, exist_ok=True); LOG = None
END = "2026-10-21"; START = "2009-12-01"
CURS = ["USD", "CNY", "HKD", "JPY", "EUR", "KRW", "SGD", "MYR", "THB", "VND", "GBP", "AUD", "PHP", "IDR", "INR", "CAD", "CHF", "NZD", "ZAR", "SEK"]
def get(params, path, keep=None):
    if os.path.exists(path) or os.path.exists(path + ".err"): return
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(40):
        try:
            with urllib.request.urlopen(url, timeout=90) as r: d = json.load(r)
        except urllib.error.HTTPError as e:   # 400／402 等：讀回應內容，交由下方判斷（不重試 400）
            try: d = json.loads(e.read().decode("utf-8", "ignore"))
            except Exception: d = {"status": e.code, "msg": str(e)}
        except Exception as e:
            print("ERR", params, e, flush=True); time.sleep(20); continue
        if d.get("status") == 200:
            rows = d.get("data", [])
            if keep: rows = [{k: x.get(k) for k in keep} for x in rows]
            if path.endswith(".csv.gz"):
                with gzip.open(path, "wt", encoding="utf-8", newline="") as g:
                    if rows: w = csv.DictWriter(g, list(rows[0].keys())); w.writeheader(); w.writerows(rows)
            else: json.dump({"status": 200, "data": rows}, open(path, "w", encoding="utf-8"), ensure_ascii=False)
            return
        msg = str(d.get("msg", ""))
        LOG.write(f"{time.strftime('%H:%M:%S')} WAIT {params.get('dataset')} {params.get('data_id')} {msg[:80]}\n"); LOG.flush()
        if "upper limit" in msg or d.get("status") == 402: time.sleep(90)
        else: json.dump(d, open(path + ".err", "w", encoding="utf-8"), ensure_ascii=False); return
    print("GIVEUP", params, flush=True)
def checkpoint(i):
    os.system(f"git add {OUT} >/dev/null 2>&1 && git commit -q -m 'p031 slice {i} checkpoint [skip ci]' >/dev/null 2>&1; "
              "for k in 1 2 3 4 5 6 7 8; do git pull -q --rebase origin p031-data >/dev/null 2>&1; git push -q origin HEAD:p031-data && break; sleep $((RANDOM%10+3)); done")
def main():
    global LOG
    i, n = int(sys.argv[1]), int(sys.argv[2])
    LOG = open(f"{OUT}/_progress_{i}.log", "a")
    rows = [l.strip() for l in open("codes_031.txt") if l.strip()]
    mine = rows[i::n]
    if i == 0:
        get({"dataset": "TaiwanStockParValueChange", "start_date": "2009-12-01", "end_date": END}, f"{OUT}/_ParValueChange_all.json")
        for idx in ("TAIEX", "TPEx"):
            get({"dataset": "TaiwanStockPrice", "data_id": idx, "start_date": "2009-12-01", "end_date": END}, f"{OUT}/_{idx}_Price.csv.gz")
    n_ok = 0
    for c in mine:
        s, e = START, END
        for ds in ("TaiwanStockPrice", "TaiwanStockDividendResult", "TaiwanStockCapitalReductionReferencePrice", "TaiwanStockSplitPrice"):
            ext = "csv.gz" if ds == "TaiwanStockPrice" else "json"
            get({"dataset": ds, "data_id": c, "start_date": s, "end_date": e}, f"{OUT}/{c}_{ds}.{ext}"); time.sleep(0.5)
        n_ok += 1
        LOG.write(f"{time.strftime('%H:%M:%S')} OK {c}\n"); LOG.flush()
        if n_ok % 5 == 0: checkpoint(i)
    LOG.write(f"{time.strftime('%H:%M:%S')} DONE {len(mine)}\n"); LOG.close(); checkpoint(i)
if __name__ == "__main__": main()
