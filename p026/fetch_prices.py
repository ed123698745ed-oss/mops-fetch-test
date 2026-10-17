# 026 災害事故策略：FinMind 日K與公司行動資料抓取（GitHub Actions 執行）
# 用法：python p026/fetch_prices.py <slice_index> <slice_count>
# 輸出：out/p026/<代號>_<dataset>.json（原始回應），另由 slice 0 抓指數與交易日曆
# 不使用 token（匿名額度）；遇額度上限等待後重試。
import json, os, sys, time, urllib.request, urllib.parse
LOG = None

API = "https://api.finmindtrade.com/api/v4/data"
START, END = "2009-12-01", "2026-10-16"
OUT = "out/p026"
os.makedirs(OUT, exist_ok=True)

def get(params, path):
    if os.path.exists(path):
        return
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(30):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                d = json.load(r)
        except Exception as e:
            print("ERR", params, e, flush=True); time.sleep(20); continue
        if d.get("status") == 200:
            if path.endswith(".csv.gz"):
                import csv, gzip
                rows = d.get("data", [])
                with gzip.open(path, "wt", encoding="utf-8", newline="") as g:
                    if rows:
                        w = csv.DictWriter(g, list(rows[0].keys())); w.writeheader(); w.writerows(rows)
            else:
                json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False)
            return
        msg = str(d.get("msg", ""))
        print("WAIT", params.get("dataset"), params.get("data_id"), msg[:60], flush=True)
        LOG.write(f"{time.strftime('%H:%M:%S')} WAIT {params.get('dataset')} {params.get('data_id')} {msg[:80]}\n"); LOG.flush()
        if "upper limit" in msg:
            time.sleep(120)
        else:
            json.dump(d, open(path + ".err", "w", encoding="utf-8"), ensure_ascii=False)
            return
    print("GIVEUP", params, flush=True)

def checkpoint(i, final=False):
    os.system(f"git add {OUT} >/dev/null 2>&1 && git commit -q -m 'p026 slice {i} checkpoint [skip ci]' >/dev/null 2>&1; "
              "for k in 1 2 3 4 5 6; do git pull -q --rebase origin p026-data >/dev/null 2>&1; git push -q origin HEAD:p026-data && break; sleep $((RANDOM%10+3)); done")

def main():
    global LOG
    i, n = int(sys.argv[1]), int(sys.argv[2])
    LOG = open(f"{OUT}/_progress_{i}.log", "a")
    codes = [c.strip() for c in open("codes_026.txt") if c.strip()]
    mine = codes[i::n]
    if i == 0:
        get({"dataset": "TaiwanStockTradingDate", "start_date": START, "end_date": END}, f"{OUT}/_TradingDate.json")
        for idx in ("TAIEX", "TPEx"):
            get({"dataset": "TaiwanStockPrice", "data_id": idx, "start_date": START, "end_date": END}, f"{OUT}/_{idx}_Price.csv.gz")
            get({"dataset": "TaiwanStockTotalReturnIndex", "data_id": idx, "start_date": START, "end_date": END}, f"{OUT}/_{idx}_TotalReturn.csv.gz")
    for c in mine:
        for ds in ("TaiwanStockPrice", "TaiwanStockDividendResult", "TaiwanStockCapitalReductionReferencePrice",
                   "TaiwanStockSplitPrice", "TaiwanStockParValueChange"):
            ext = "csv.gz" if ds == "TaiwanStockPrice" else "json"
            get({"dataset": ds, "data_id": c, "start_date": START, "end_date": END}, f"{OUT}/{c}_{ds}.{ext}")
            time.sleep(1)
        LOG.write(f"{time.strftime('%H:%M:%S')} OK {c}\n"); LOG.flush()
        if mine.index(c) % 5 == 4: checkpoint(i)
    LOG.write(f"{time.strftime('%H:%M:%S')} DONE {len(mine)}\n"); LOG.close()
    checkpoint(i, True)
    print("DONE", i, len(mine), flush=True)

if __name__ == "__main__":
    main()
