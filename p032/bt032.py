# 032 新藥解盲 回測主程式（Elon）
# 依策略卡 V01 第4–7節＋Ed 2026-10-23 補正：限價依官方規則推算、時段 E-Test、停牌組另列、一期安全性認定、排除醫材
import pandas as pd, numpy as np, json, os, math, sys
sys.path.insert(0, '/home/claude/mops-fetch-test')
from bt_stats import summarize
D = '/home/claude/p032'
HS = [1, 2, 3, 5, 10, 20, 40]
DATA_END = pd.Timestamp('2026-10-22')

# ---------- 交易日曆（以 2330 有成交日為市場交易日） ----------
cal = pd.to_datetime(sorted({r['date'] for r in json.load(open(f'{D}/px/2330.json'))['data']}))
cal = pd.DatetimeIndex(cal)
def next_td(d):            # 嚴格晚於 d 的第一個市場交易日
    i = cal.searchsorted(d, side='right'); return cal[i] if i < len(cal) else None
def prev_td(d):            # 嚴格早於 d 的最後市場交易日
    i = cal.searchsorted(d, side='left') - 1; return cal[i] if i >= 0 else None
def shift_td(d, k):        # d 為交易日，往後第 k 個交易日
    i = cal.get_loc(d) + k; return cal[i] if i < len(cal) else None

# ---------- 升降單位與漲跌停價（官方規則推算） ----------
def tick(p):
    return 0.01 if p < 10 else 0.05 if p < 50 else 0.1 if p < 100 else 0.5 if p < 500 else 1.0 if p < 1000 else 5.0
def limits(ref, d):
    pct = 0.10 if d >= pd.Timestamp('2015-06-01') else 0.07
    up_raw, dn_raw = ref * (1 + pct), ref * (1 - pct)
    t = tick(up_raw); up = math.floor(round(up_raw / t, 6)) * t
    if tick(up) != t: t = tick(up); up = math.floor(round(up_raw / t, 6)) * t
    t = tick(dn_raw); dn = math.ceil(round(dn_raw / t, 6)) * t
    if tick(dn) != t: t = tick(dn); dn = math.ceil(round(dn_raw / t, 6)) * t
    return round(up, 2), round(dn, 2)

# ---------- 個股資料 ----------
L = pd.read_csv('/home/claude/mops-fetch-test/listing/上市櫃期間表.csv', dtype=str).fillna('').set_index('公司代號')
STK = {}
def load(code):
    if code in STK: return STK[code]
    p = pd.DataFrame(json.load(open(f'{D}/px/{code}.json'))['data'])
    p['date'] = pd.to_datetime(p['date']); p = p.set_index('date').sort_index()
    p = p[(p['Trading_Volume'] > 0) & (p['open'] > 0) & (p['close'] > 0) & (p['max'] > 0) & (p['min'] > 0)][['open', 'max', 'min', 'close', 'Trading_Volume']].rename(columns={'max': 'high', 'min': 'low'})
    # 公司行動參考價（除權息、減資）
    ca = {}
    for ds, b, a in [('TaiwanStockDividendResult', 'before_price', 'after_price'),
                     ('TaiwanStockCapitalReductionReferencePrice', 'ClosingPriceonTheLastTradingDay', 'PostReductionReferencePrice'),
                     ('TaiwanStockSplitPrice', 'before_price', 'after_price')]:
        f = f'{D}/ca/{ds}_{code}.json'
        if os.path.exists(f):
            for r in json.load(open(f))['data']:
                try:
                    bb, aa = float(r[b]), float(r[a])
                    if bb > 0 and aa > 0: ca[pd.Timestamp(r['date'])] = (bb, aa)
                except Exception: pass
    first = pd.Timestamp(L.loc[code, '初次上市櫃日'])
    last = pd.Timestamp(L.loc[code, '終止上市櫃日']) if L.loc[code, '終止上市櫃日'] else pd.Timestamp('2099-12-31')
    p = p[(p.index >= first) & (p.index < last)]          # 只用上市櫃期間行情（排除興櫃）
    # 參考價與漲跌停價
    refs, ups, dns = [], [], []
    prev_close = None
    for d, r in p.iterrows():
        ref = ca[d][1] if d in ca else prev_close
        if ref is None: refs.append(np.nan); ups.append(np.nan); dns.append(np.nan)
        else:
            u, dn = limits(ref, d); refs.append(ref); ups.append(u); dns.append(dn)
        prev_close = r['close']
    p['ref'], p['up'], p['dn'] = refs, ups, dns
    # 上市櫃首 5 個交易日無漲跌幅限制
    nolim = p.index[p.index >= first][:5]
    p.loc[p.index.isin(nolim), ['up', 'dn']] = np.nan
    # 推算限價與當日行情矛盾（最高>漲停或最低<跌停）→ 當日限價列未知，不以推算值代替
    bad = (p['high'] > p['up'] + 1e-6) | (p['low'] < p['dn'] - 1e-6)
    p['限價未知'] = bad | p['up'].isna()
    p.loc[bad, ['up', 'dn']] = np.nan
    p['lock_up'] = (p['open'] == p['up']) & (p['high'] == p['up']) & (p['low'] == p['up']) & (p['close'] == p['up'])
    p['lock_dn'] = (p['open'] == p['dn']) & (p['high'] == p['dn']) & (p['low'] == p['dn']) & (p['close'] == p['dn'])
    STK[code] = (p, ca); return STK[code]

def factor(ca, d0, d1):     # (d0, d1] 之間除權息／減資的價格還原因子（乘在出場價上）
    f = 1.0
    for d, (b, a) in ca.items():
        if d0 < d <= d1: f *= b / a
    return f

def exit_trade(p, ca, entry_day, entry_px, H, side, conservative):
    tgt = shift_td(entry_day, H - 1)
    if tgt is None or tgt > DATA_END: return None, '未完成（期末未滿持有期）'
    d = tgt; note = ''
    while True:
        if d is None or d > DATA_END: return None, '未結案（延後出場超出資料期末）'
        if d in p.index:
            r = p.loc[d]
            bad = conservative and ((side == 'L' and r['close'] == r['dn']) or (side == 'S' and r['close'] == r['up']))
            if not bad: break
            note = '出場延後：不利方向收在漲跌停'
        else:
            note = note or '出場延後：預定出場日停牌／無成交'
        d = next_td(d)
    xp = p.loc[d, 'close'] * factor(ca, entry_day, d)
    ret = xp / entry_px - 1 if side == 'L' else 1 - xp / entry_px
    hold = cal.get_loc(d) - cal.get_loc(entry_day) + 1
    return dict(出場日=d.date(), 出場價=p.loc[d, 'close'], 還原因子=factor(ca, entry_day, d), 報酬=ret, 持有交易日數=hold, 出場備註=note), ''

def trade(p, ca, entry_day, H, side, px_type, conservative):
    if entry_day is None or entry_day > DATA_END: return None, '未完成（進場日超出資料期末）'
    if entry_day not in p.index: return None, '進場日停牌／無成交'
    r = p.loc[entry_day]
    if pd.isna(r['up']) and conservative: return None, '進場日限價未知（上市櫃首5日，或推算限價與當日行情矛盾）'
    epx = r[px_type]
    if conservative:
        if side == 'L' and epx == r['up']: return None, '做多進場價在漲停，日線無法證實成交'
        if side == 'S' and epx == r['dn']: return None, '放空進場價在跌停，日線無法證實成交'
    x, why = exit_trade(p, ca, entry_day, epx, H, side, conservative)
    if x is None: return None, why
    x.update(進場日=entry_day.date(), 進場價=epx); return x, ''

# ---------- 事件 ----------
E = pd.read_csv(f'{D}/event_review_v1.csv', dtype=str).fillna('')
EV = E[E['事件判定'] == '主事件'].copy()
INV = pd.read_csv(f'{D}/inventory_v1.csv', dtype=str).set_index('cid')
def phase(x):
    if '混合' in x or 'II/III' in x: return '混合II/III'
    for k in ['一期', '二期', '三期']:
        if k in x: return k
    return '其他/不明'
EV['期別組'] = EV['期別'].map(phase)
EV['時段'] = EV['cid'].map(INV['時段']); EV['S日停牌'] = EV['cid'].map(INV['S日停牌'])
# 跨公司同試驗（同一試驗同一次結果，不同股票）
CROSS = {'C017':'G1','S104':'G1','S306':'G2','S304':'G2','C120':'G3','S394':'G3','C131':'G4','C132':'G4',
         'C155':'G5','C156':'G5','C176':'G6','C177':'G6','S478':'G7','S479':'G7','C215':'G8','C216':'G8'}
EV['跨公司組'] = EV['cid'].map(CROSS).fillna('')
# 跨公司組內保留「主要研發公司」標記（敏感度：每試驗只算一件）
PRIMARY = {'S104','S304','S394','C131','C155','C177','S478','C215'}
EV['每試驗一件保留'] = EV.apply(lambda r: (r['跨公司組'] == '') or (r['cid'] in PRIMARY), axis=1)

rows, excl, desc = [], [], []
for _, e in EV.iterrows():
    code = e['公司代號']; p, ca = load(code)
    S = pd.Timestamp(e['發言日期']); Eday = next_td(S); T = prev_td(S)
    base = dict(cid=e['cid'], 公司代號=code, 公司名稱=e['公司名稱'], S=S.date(), 發言時間=e['發言時間'].zfill(6), 時段=e['時段'],
                S日停牌=e['S日停牌'], 結果分類=e['結果分類'], 期別組=e['期別組'], 指標性質=e['指標性質'], 結果階段=e['結果階段'],
                跨公司組=e['跨公司組'], 每試驗一件保留=e['每試驗一件保留'], E=Eday.date() if Eday is not None else '')
    # 事前20日（嚴格早於S的最後市場交易日T；個股收盤取T以前最後成交）
    pre = np.nan
    if T is not None:
        pt = p[p.index <= T]
        if len(pt) >= 21:
            t0, t20 = pt.index[-1], pt.index[-21]
            pre = pt['close'].iloc[-1] * factor(ca, t20, t0) / pt['close'].iloc[-21] - 1
    base['事前20日報酬'] = pre
    base['事前20日組'] = '缺值' if pd.isna(pre) else ('正' if pre > 1e-9 else '負' if pre < -1e-9 else '零')
    # 開盤跳空（E開盤 vs 參考價：一般為前收，除權息日為除權參考價）
    gap = np.nan
    if Eday in p.index and not pd.isna(p.loc[Eday, 'ref']): gap = p.loc[Eday, 'open'] / p.loc[Eday, 'ref'] - 1
    base['E開盤跳空'] = gap
    base['跳空組'] = '不明' if pd.isna(gap) else ('上' if gap > 1e-9 else '下' if gap < -1e-9 else '平')
    if Eday in p.index:
        r = p.loc[Eday]; base['E開盤位置'] = '開漲停' if r['open'] == r['up'] else '開跌停' if r['open'] == r['dn'] else '一般'
        base['E整日鎖板'] = '鎖漲停' if r['lock_up'] else '鎖跌停' if r['lock_dn'] else ''
    desc.append(base)

    # ---- A：E 開盤進場 ----
    for side in ['L', 'S']:
        for H in HS:
            for ver, cons in [('A價格反應', False), ('A保守', True)]:
                x, why = trade(p, ca, Eday, H, side, 'open', cons)
                k = dict(base, 版本=ver, 方向='做多' if side == 'L' else '放空', H=H)
                if x: rows.append(dict(k, **x))
                else: excl.append(dict(k, 排除原因=why))
    # ---- B：鎖板後開板，隔日開盤 ----
    if Eday in p.index:
        lim20 = shift_td(S if S in cal else prev_td(S), 20)   # S 後第 20 個市場交易日
        for lockdir in ['lock_up', 'lock_dn']:
            if not p.loc[Eday, lockdir]: continue
            d = Eday; Dd = None
            while d is not None and d <= min(lim20, DATA_END):
                if d in p.index and not p.loc[d, lockdir]: Dd = d; break
                d = next_td(d)
            for side in ['L', 'S']:
                for H in HS:
                    k = dict(base, 版本='B保守', 鎖板方向='連續鎖漲停' if lockdir == 'lock_up' else '連續鎖跌停',
                             方向='做多' if side == 'L' else '放空', H=H, 開板日D=Dd.date() if Dd is not None else '')
                    if Dd is None: excl.append(dict(k, 排除原因='S後20個交易日內未開板（無訊號）')); continue
                    x, why = trade(p, ca, next_td(Dd), H, side, 'open', True)
                    if x: rows.append(dict(k, **x))
                    else: excl.append(dict(k, 排除原因=why))
    # ---- E-Test 1：時段（盤前→S日開盤；盤中→S日收盤） ----
    if e['時段'] in ('盤前', '盤中') and S in p.index:
        pt = 'open' if e['時段'] == '盤前' else 'close'
        for side in ['L', 'S']:
            for H in HS:
                for ver, cons in [('ET1價格反應', False), ('ET1保守', True)]:
                    x, why = trade(p, ca, S, H, side, pt, cons)
                    k = dict(base, 版本=ver, 方向='做多' if side == 'L' else '放空', H=H)
                    if x: rows.append(dict(k, **x))
                    else: excl.append(dict(k, 排除原因=why))

T_ = pd.DataFrame(rows); X = pd.DataFrame(excl); DS = pd.DataFrame(desc)
T_.to_csv(f'{D}/out_trades.csv', index=False, encoding='utf-8-sig')
X.to_csv(f'{D}/out_excluded.csv', index=False, encoding='utf-8-sig')
DS.to_csv(f'{D}/out_events.csv', index=False, encoding='utf-8-sig')

# ---------- 統計 ----------
def stat(df):
    if len(df) == 0: return None
    s = summarize(df['報酬'].astype(float).tolist(), hold_days=df['持有交易日數'].astype(int).tolist(),
                  cluster=df['進場日'].astype(str).tolist(), cluster_unit='進場日')
    return s
def table(df, by, name):
    out = []
    for keys, g in df.groupby(by, dropna=False):
        s = stat(g)
        if s is None: continue
        out.append(dict(zip(by, keys if isinstance(keys, tuple) else (keys,)), **s))
    o = pd.DataFrame(out); o.to_csv(f'{D}/tab_{name}.csv', index=False, encoding='utf-8-sig'); return o
T_['期間'] = np.where(pd.to_datetime(T_['進場日']) < pd.Timestamp('2021-01-01'), '2010–2020', '2021–2026')
T_['年度'] = pd.to_datetime(T_['進場日']).dt.year
allg = T_.copy(); allg['結果分類'] = '全部'
A = pd.concat([T_, allg])
table(A[A['版本'].str.startswith('A')], ['版本', '方向', 'H', '結果分類'], 'A_結果分類')
table(T_[T_['版本'].str.startswith('A')], ['版本', '方向', 'H', '期別組', '結果分類'], 'A_期別')
table(A[A['版本'] == 'A保守'], ['方向', 'H', '結果分類', '期間'], 'A保守_期間切分')
table(T_[(T_['版本'] == 'A保守')], ['方向', 'H', '指標性質'], 'A保守_指標性質')
table(T_[(T_['版本'] == 'A保守')], ['方向', 'H', '結果階段'], 'A保守_結果階段')
table(A[(A['版本'] == 'A保守') & A['每試驗一件保留']], ['方向', 'H', '結果分類'], 'A保守_每試驗一件')
table(A[(A['版本'] == 'A保守')], ['方向', 'H', '結果分類', '事前20日組'], 'A保守_事前20日')
table(A[(A['版本'] == 'A價格反應')], ['方向', 'H', '結果分類', '跳空組'], 'A價格反應_跳空描述')
table(A[(A['版本'] == 'A保守')], ['方向', 'H', '結果分類', 'S日停牌'], 'ET2_停牌組')
if (T_['版本'] == 'B保守').any():
    table(A[A['版本'] == 'B保守'], ['鎖板方向', '方向', 'H', '結果分類'], 'B保守')
table(A[A['版本'].str.startswith('ET1')], ['版本', '方向', 'H', '結果分類', '時段'], 'ET1_時段')
table(A[A['版本'].str.startswith('ET1')], ['版本', '方向', 'H', '結果分類', '期間'], 'ET1_期間切分')
print('trades', len(T_), 'excluded', len(X)); print(X['排除原因'].value_counts())
