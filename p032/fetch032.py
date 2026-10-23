# 032 價格與公司行動資料下載（Elon，2026-10-23 執行；FinMind v4 匿名額度，無金鑰）
# 輸出：px/{代號}.json（TaiwanStockPrice，含 2330 作為市場交易日曆）
#       ca/{資料集}_{代號}.json（TaiwanStockDividendResult、TaiwanStockCapitalReductionReferencePrice、TaiwanStockSplitPrice）
import pandas as pd, json, urllib.request, urllib.parse, time, os
D = '/home/claude/p032'; API = 'https://api.finmindtrade.com/api/v4/data?'
E = pd.read_csv(f'{D}/event_review_v1.csv', dtype=str).fillna('')
codes = sorted(set(E[E['事件判定'].isin(['主事件', '候選-非解盲停試'])]['公司代號']))
def get(ds, code, start, path):
    if os.path.exists(path): return
    q = urllib.parse.urlencode({'dataset': ds, 'data_id': code, 'start_date': start, 'end_date': '2026-10-23'})
    for _ in range(6):
        try:
            d = json.load(urllib.request.urlopen(API + q, timeout=90))
            if d.get('status') == 200: json.dump(d, open(path, 'w')); return
        except Exception: pass
        time.sleep(70)   # 402 額度上限時等待後重試
os.makedirs(f'{D}/px', exist_ok=True); os.makedirs(f'{D}/ca', exist_ok=True)
for c in codes + ['2330']:
    get('TaiwanStockPrice', c, '2009-10-01', f'{D}/px/{c}.json')
for ds in ['TaiwanStockDividendResult', 'TaiwanStockCapitalReductionReferencePrice', 'TaiwanStockSplitPrice']:
    for c in codes:
        get(ds, c, '2009-01-01', f'{D}/ca/{ds}_{c}.json')
