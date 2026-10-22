# 029 資產處分策略：FinMind 日K、公司行動、已發行股數、匯率抓取（GitHub Actions 執行，匿名額度）
# 用法：python p029/fetch.py <slice_index> <slice_count>；輸出 out/p029/
import json, os, sys, time, urllib.request, urllib.parse, csv, gzip
API = "https://api.finmindtrade.com/api/v4/data"
OUT = "out/p029"; os.makedirs(OUT, exist_ok=True); LOG = None
END = "2026-10-21"
CURS = ["USD", "CNY", "HKD", "JPY", "EUR", "KRW", "SGD", "MYR", "THB", "VND", "GBP", "AUD", "PHP", "IDR", "INR", "CAD", "CHF", "NZD", "ZAR", "SEK"]
def get(params, path, keep=None):
    if os.path.exists(path) or os.path.exists(path + ".err"): return
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(40):
        try:
            with urllib.request.urlopen(url, timeout=90) as r: d = json.load(r)
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
        if "upper limit" in msg: time.sleep(90)
        else: json.dump(d, open(path + ".err", "w", encoding="utf-8"), ensure_ascii=False); return
    print("GIVEUP", params, flush=True)
def checkpoint(i):
    os.system(f"git add {OUT} >/dev/null 2>&1 && git commit -q -m 'p029 slice {i} checkpoint [skip ci]' >/dev/null 2>&1; "
              "for k in 1 2 3 4 5 6 7 8; do git pull -q --rebase origin p029-data >/dev/null 2>&1; git push -q origin HEAD:p029-data && break; sleep $((RANDOM%10+3)); done")
def main():
    global LOG
    i, n = int(sys.argv[1]), int(sys.argv[2])
    LOG = open(f"{OUT}/_progress_{i}.log", "a")
    rows = [l.strip().split(",") for l in open("codes_029.txt") if l.strip()]
    mine = rows[i::n]
    if i == 0:
        for idx in ("TAIEX", "TPEx"):
            get({"dataset": "TaiwanStockPrice", "data_id": idx, "start_date": "2009-12-01", "end_date": END}, f"{OUT}/_{idx}_Price.csv.gz")
    if i == 1:
        for c in CURS:
            get({"dataset": "TaiwanExchangeRate", "data_id": c, "start_date": "2009-12-01", "end_date": END}, f"{OUT}/_FX_{c}.csv.gz",
                keep=["date", "currency", "cash_buy", "cash_sell", "spot_buy", "spot_sell"]); time.sleep(1)
    n_ok = 0
    for c, s, e, sh in mine:
        for ds in ("TaiwanStockPrice", "TaiwanStockDividendResult", "TaiwanStockCapitalReductionReferencePrice", "TaiwanStockSplitPrice", "TaiwanStockParValueChange"):
            ext = "csv.gz" if ds == "TaiwanStockPrice" else "json"
            get({"dataset": ds, "data_id": c, "start_date": s, "end_date": e}, f"{OUT}/{c}_{ds}.{ext}"); time.sleep(0.5)
        if sh == "1":
            get({"dataset": "TaiwanStockShareholding", "data_id": c, "start_date": s, "end_date": e}, f"{OUT}/{c}_Shares.csv.gz", keep=["date", "stock_id", "NumberOfSharesIssued"])
        n_ok += 1
        LOG.write(f"{time.strftime('%H:%M:%S')} OK {c}\n"); LOG.flush()
        if n_ok % 5 == 0: checkpoint(i)
    LOG.write(f"{time.strftime('%H:%M:%S')} DONE {len(mine)}\n"); LOG.close(); checkpoint(i)
if __name__ == "__main__": main()
