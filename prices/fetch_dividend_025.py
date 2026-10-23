# 補抓 025 全部事件股的 FinMind TaiwanStockDividend（股利政策：現金／配股與除權息交易日），用於核對 DividendResult 有無遺漏除權息日（R04）
import csv, json, os, time, urllib.request
B = "https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockDividend&data_id={}&start_date=2009-01-01&end_date=2026-10-19"
codes = sorted({f.split("_")[1].split(".")[0] for f in os.listdir("prices/raw") if f.startswith("TaiwanStockDividendResult_")})
for sid in codes:
    f = f"prices/raw/TaiwanStockDividend_{sid}.json"
    if os.path.exists(f): continue
    for i in range(4):
        try:
            t = urllib.request.urlopen(B.format(sid), timeout=90).read(); d = json.loads(t)
            if d.get("status") != 200: print("ERR", sid, d.get("msg")); time.sleep(60); continue
            open(f, "wb").write(t); break
        except Exception as ex: print("EXC", sid, ex); time.sleep(10)
    time.sleep(0.6)
print("codes", len(codes))
