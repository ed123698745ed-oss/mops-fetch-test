# 029 R03：FinMind TaiwanStockDividend（現金股利與股票股利分開），供現金流報酬計算；輸出 out/p029div/
import json, os, sys, time, urllib.request, urllib.parse, urllib.error
API = "https://api.finmindtrade.com/api/v4/data"; OUT = "out/p029div"; os.makedirs(OUT, exist_ok=True)
for c in [l.strip() for l in open("p029/div_codes.txt") if l.strip()]:
    p = f"{OUT}/{c}_TaiwanStockDividend.json"
    if os.path.exists(p): continue
    url = API + "?" + urllib.parse.urlencode({"dataset": "TaiwanStockDividend", "data_id": c, "start_date": "2005-01-01", "end_date": "2026-10-21"})
    for k in range(30):
        try:
            with urllib.request.urlopen(url, timeout=90) as r: d = json.load(r)
        except urllib.error.HTTPError as e:
            try: d = json.loads(e.read().decode("utf-8", "ignore"))
            except Exception: d = {"status": e.code}
        except Exception as e: print("ERR", c, e); time.sleep(20); continue
        if d.get("status") == 200: json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False); print("OK", c, len(d.get("data", []))); break
        print("WAIT", c, str(d.get("msg", ""))[:80]); time.sleep(90 if "upper limit" in str(d.get("msg", "")) or d.get("status") == 402 else 5)
    time.sleep(1)
