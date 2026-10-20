# 抓 025 事件股的 FinMind 日K與除權息（免費等級，未還原價）＋大盤指數
import csv, json, os, time, urllib.request, datetime as dt
B = "https://api.finmindtrade.com/api/v4/data?dataset={}&data_id={}&start_date={}&end_date={}"
def get(ds, sid, s, e):
    f = f"prices/raw/{ds}_{sid}.json"
    if os.path.exists(f): return
    for i in range(4):
        try:
            t = urllib.request.urlopen(B.format(ds, sid, s, e), timeout=90).read()
            d = json.loads(t)
            if d.get("status") != 200: print("ERR", ds, sid, d.get("msg")); time.sleep(60); continue
            open(f, "wb").write(t); return
        except Exception as ex: print("EXC", sid, ex); time.sleep(10)
os.makedirs("prices/raw", exist_ok=True)
E_ = list(csv.DictReader(open("out/025_事件表.csv", encoding="utf-8-sig")))
obs = [r for r in csv.DictReader(open("out/025_全候選判讀.csv", encoding="utf-8-sig")) if "土地出售附帶" in r["類別"]]
codes = {}
for r in E_ + obs:
    d = dt.datetime.strptime(r["發言日期"], "%Y%m%d")
    a, b = codes.get(r["公司代號"], (d, d)); codes[r["公司代號"]] = (min(a, d), max(b, d))
for sid in ["TAIEX", "TPEx"]:
    get("TaiwanStockPrice", sid, "2009-12-01", "2026-10-19")
for sid, (a, b) in sorted(codes.items()):
    s = (a - dt.timedelta(days=15)).strftime("%Y-%m-%d"); e = min(b + dt.timedelta(days=100), dt.datetime(2026, 10, 19)).strftime("%Y-%m-%d")
    get("TaiwanStockPrice", sid, s, e); get("TaiwanStockDividendResult", sid, s, e); time.sleep(0.5)
print("codes", len(codes))
