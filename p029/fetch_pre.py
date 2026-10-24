# 029 R03：2007～2009 獨立驗證用 FinMind 資料（日K、公司行動、股利拆分、已發行股數、指數、匯率）；輸出 out/p029pre/
# 用法：python p029/fetch_pre.py <slice> <count>；代號清單 p029/codes_pre.txt（代號,起日,迄日,是否抓股數）
import json, os, sys, time, urllib.request, urllib.parse, urllib.error, csv, gzip
API = "https://api.finmindtrade.com/api/v4/data"; OUT = "out/p029pre"; os.makedirs(OUT, exist_ok=True)
S0, S1 = "2006-11-01", "2010-05-31"
CURS = ["USD", "CNY", "HKD", "JPY", "EUR", "KRW", "SGD", "MYR", "THB", "VND", "GBP", "AUD", "PHP", "IDR", "INR", "CAD", "CHF", "NZD", "ZAR", "SEK"]
def get(params, path, keep=None):
    if os.path.exists(path) or os.path.exists(path + ".err"): return
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(40):
        try:
            with urllib.request.urlopen(url, timeout=90) as r: d = json.load(r)
        except urllib.error.HTTPError as e:
            try: d = json.loads(e.read().decode("utf-8", "ignore"))
            except Exception: d = {"status": e.code, "msg": str(e)}
        except Exception as e: print("ERR", params, e, flush=True); time.sleep(20); continue
        if d.get("status") == 200:
            rows = d.get("data", [])
            if keep: rows = [{k: x.get(k) for k in keep} for x in rows]
            if path.endswith(".csv.gz"):
                with gzip.open(path, "wt", encoding="utf-8", newline="") as g:
                    if rows: w = csv.DictWriter(g, list(rows[0].keys())); w.writeheader(); w.writerows(rows)
            else: json.dump({"status": 200, "data": rows}, open(path, "w", encoding="utf-8"), ensure_ascii=False)
            return
        msg = str(d.get("msg", "")); print("WAIT", params.get("dataset"), params.get("data_id"), msg[:80], flush=True)
        if "upper limit" in msg or d.get("status") == 402: time.sleep(90)
        else: json.dump(d, open(path + ".err", "w", encoding="utf-8"), ensure_ascii=False); return
i, n = int(sys.argv[1]), int(sys.argv[2])
if i == 0:
    get({"dataset": "TaiwanStockParValueChange", "start_date": S0, "end_date": S1}, f"{OUT}/_ParValueChange_all.json")
    for idx in ("TAIEX", "TPEx"): get({"dataset": "TaiwanStockPrice", "data_id": idx, "start_date": S0, "end_date": S1}, f"{OUT}/_{idx}_Price.csv.gz")
if i == 1:
    for c in CURS: get({"dataset": "TaiwanExchangeRate", "data_id": c, "start_date": S0, "end_date": S1}, f"{OUT}/_FX_{c}.csv.gz", keep=["date", "currency", "cash_buy", "cash_sell", "spot_buy", "spot_sell"])
rows = [l.strip().split(",") for l in open("p029/codes_pre.txt") if l.strip()]
for c, s, e, sh in rows[i::n]:
    for ds in ("TaiwanStockPrice", "TaiwanStockDividendResult", "TaiwanStockCapitalReductionReferencePrice", "TaiwanStockSplitPrice"):
        get({"dataset": ds, "data_id": c, "start_date": s, "end_date": e}, f"{OUT}/{c}_{ds}.{'csv.gz' if ds == 'TaiwanStockPrice' else 'json'}"); time.sleep(0.5)
    get({"dataset": "TaiwanStockDividend", "data_id": c, "start_date": "2005-01-01", "end_date": e}, f"{OUT}/{c}_TaiwanStockDividend.json")
    if sh == "1": get({"dataset": "TaiwanStockShareholding", "data_id": c, "start_date": s, "end_date": e}, f"{OUT}/{c}_Shares.csv.gz", keep=["date", "stock_id", "NumberOfSharesIssued"])
    print("OK", c, flush=True)
