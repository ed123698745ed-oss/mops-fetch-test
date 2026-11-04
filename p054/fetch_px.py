# 054：FinMind 未還原日K、除權息結果、股利政策、減資參考價、交易日；GitHub Actions 匿名額度
# 用法：python p054/fetch_px.py；輸出 out/p054/px/；已存在略過；遇額度上限等待
import json, os, time, urllib.request, urllib.parse, urllib.error
API = "https://api.finmindtrade.com/api/v4/data"
OUT = "out/p054/px"; os.makedirs(OUT, exist_ok=True)
START, END = "2013-01-01", "2026-11-04"
LOG = open("out/p054/px_log.txt", "a", encoding="utf-8")
def L(s): print(s, flush=True); LOG.write(s + "\n"); LOG.flush()
DEADLINE = time.time() + 300 * 60
def get(params, path):
    if os.path.exists(path): return
    url = API + "?" + urllib.parse.urlencode(params)
    for a in range(60):
        if time.time() > DEADLINE: L("時間到"); raise SystemExit(0)
        try:
            with urllib.request.urlopen(url, timeout=90) as r: d = json.load(r)
        except urllib.error.HTTPError as e:
            try: d = json.loads(e.read().decode("utf-8", "ignore"))
            except Exception: d = {"status": e.code, "msg": str(e)}
        except Exception as e:
            L(f"ERR {params} {e}"); time.sleep(20); continue
        if d.get("status") == 200:
            json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False)
            L(f"OK {params.get('dataset')} {params.get('data_id','')} {len(d.get('data', []))}"); return
        msg = str(d.get("msg", ""))
        if d.get("status") == 402 or "upper limit" in msg:
            L(f"WAIT {params.get('dataset')} {params.get('data_id','')}"); time.sleep(120); continue
        L(f"FAIL {params} {msg[:120]}"); json.dump(d, open(path + ".err", "w", encoding="utf-8"), ensure_ascii=False); return
import sys
CF = sys.argv[1] if len(sys.argv) > 1 else "p054/codes_054.txt"
codes = [l.split(",")[0] for l in open(CF, encoding="utf-8") if l[:1].isdigit()]
get({"dataset": "TaiwanStockTradingDate"}, f"{OUT}/TradingDate.json")
for c in codes:
    for ds in ["TaiwanStockPrice", "TaiwanStockDividendResult", "TaiwanStockDividend", "TaiwanStockCapitalReductionReferencePrice"]:
        get({"dataset": ds, "data_id": c, "start_date": START if ds != "TaiwanStockDividend" else "2012-01-01", "end_date": END},
            f"{OUT}/{ds}_{c}.json")
L("完成")
