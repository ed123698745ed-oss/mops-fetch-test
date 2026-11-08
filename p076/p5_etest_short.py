# 076 E-Test E2（D-076-20261108-2252-1）：股東會後放空，只用樣本內
# 進場：目標股東會日之後第一個交易日開盤放空；回補：持有 H 個交易日（含首尾）收盤
# 空方報酬＝−share_return（固定股數加實得現金：空方需支付現金股利、配股增加回補股數）
# L1：進場日一價鎖跌停或停牌／零量／限幅待查 → 賣不到，排除；回補日一價鎖漲停或停牌 → 順延到可買進日收盤
# L2（融券資格、停券）資料層沒有 → 未驗證；另計 2013-09-23 前「開盤低於前收」的平盤下放空限制筆數
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/home/claude/w076/code')
from elon_tools import share_return
W = '/home/claude/w076'
IS_END, OOS_START = pd.Timestamp('2021-12-31'), pd.Timestamp('2022-04-11')
CAL = pd.DatetimeIndex(pd.read_parquet(f'{W}/calendar.parquet')['date'].dt.normalize().sort_values())
idx = lambda d: CAL.searchsorted(pd.Timestamp(d))
ev = pd.read_csv(f'{W}/out/s1_events_labeled.csv', dtype={'公司代號': str, '發言日期': str, '發言時間': str},
                 parse_dates=['進場日', '最後可買進日', '目標會期'])
ev = ev[ev['可交易'] & ev['判讀'].isin(['D', 'T'])].copy()
ev['樣本'] = ['樣本內' if b <= IS_END else ('樣本外' if e >= OOS_START else '跨越') for e, b in zip(ev['進場日'], ev['最後可買進日'])]
ev = ev[ev['樣本'] == '樣本內'].reset_index(drop=True)
ctl = pd.read_csv(f'{W}/out/control.csv', dtype={'公司代號': str}, parse_dates=['最後可買進日', '會期'])
ctl = ctl[ctl['最後可買進日'] <= IS_END]
ev['年月'] = ev['最後可買進日'].dt.to_period('M').astype(str)
need = set(ev['公司代號']) | set(ctl[ctl['年月'].isin(set(ev['年月']))]['公司代號'])
K = pd.read_parquet(f'{W}/daily_k.parquet', filters=[('stock_id', 'in', sorted(need)), ('date', '>=', pd.Timestamp('2007-06-01'))])
K['date'] = K['date'].dt.normalize()
KG = {k: g.set_index('date').sort_index() for k, g in K.groupby('stock_id')}
CA = pd.read_parquet(f'{W}/corp_actions.parquet'); CAG = {k: g for k, g in CA[CA['stock_id'].isin(need)].groupby('stock_id')}

def actions(sym, a, b):
    g = CAG.get(sym); out = []
    if g is None: return out
    for r in g[(g['ex_date'] > a) & (g['ex_date'] <= b)].itertuples():
        if r.kind == '現金股利': out.append({'date': r.ex_date, 'cash': float(r.cash or 0)})
        elif r.kind == '配股' and pd.notna(r.share_ratio): out.append({'date': r.ex_date, 'cash': float(r.cash) if pd.notna(r.cash) else 0.0, 'stock': float(r.share_ratio) - 1})
        elif r.kind == '減資' and pd.notna(r.share_ratio): out.append({'date': r.ex_date, 'swap': float(r.share_ratio), 'refund': float(r.cash) if pd.notna(r.cash) else 0.0})
        elif r.kind == '現增除權': pass
        else: return None
    return out
def bar(sym, d):
    g = KG.get(sym); return None if g is None or d not in g.index else g.loc[d]
def bad_limit(b): return str(b.get('limit_src') or '').startswith('待查') or b.get('limit_src') == '缺參考價'
def one_price(b): return b['open'] == b['high'] == b['low'] == b['close']

def short_trade(sym, ent_d, ext_d):
    b = bar(sym, ent_d)
    if b is None: return '無行情'
    if bad_limit(b): return '資料不足：限幅待查或缺參考價'
    if bool(b.get('no_trade')) or not (b.get('volume', 0) > 0): return '停牌或零量'
    if one_price(b) and pd.notna(b.get('limit_down')) and b['open'] <= b['limit_down']: return '一價鎖跌停，賣不到'
    i = idx(ext_d); delay = 0
    while True:
        if i >= len(CAL): return '回補順延超出資料'
        bx = bar(sym, CAL[i])
        if bx is not None and not bad_limit(bx) and not bool(bx.get('no_trade')) and bx.get('volume', 0) > 0 and not (one_price(bx) and pd.notna(bx.get('limit_up')) and bx['close'] >= bx['limit_up']):
            break
        i += 1; delay += 1
        if delay > 60: return '回補順延超過 60 交易日'
    xd = CAL[i]; g = KG[sym]
    if g.loc[(g.index > ent_d) & (g.index <= xd), 'jump_flag'].fillna(False).any(): return '持有期間跳動查無公司行動'
    evs = actions(sym, ent_d, xd)
    if evs is None: return '持有期間公司行動資料不足'
    r = -share_return(ent_d, float(b['open']), xd, float(bx['close']), evs)
    downtick = bool(ent_d < pd.Timestamp('2013-09-23') and pd.notna(b.get('prev_close')) and b['open'] < b['prev_close'])
    return {'entry_date': ent_d, 'entry_px': float(b['open']), 'exit_date': xd, 'exit_px': float(bx['close']), 'ret': r,
            'hold_days': int(i - idx(ent_d) + 1), 'exit_delay': delay, 'downtick_flag': downtick}

rows = []
for _, e in ev.iterrows():
    ei = CAL.searchsorted(e['目標會期'], side='right')          # 股東會日之後第一個交易日
    for H in (5, 10, 20, 60):
        ent_d, ext_d = CAL[ei], CAL[ei + H - 1]
        t = short_trade(e['公司代號'], ent_d, ext_d)
        info = f"{e['目標會期'].date()} 13:30"
        row = {'trade_id': f"E2H{H}-{e['公司代號']}-{e['發言日期']}", 'combo': f"{e['判讀']}|E2-H{H}", 'group': e['判讀'], 'is_etest': True,
               'symbol': e['公司代號'], 'name': e['公司名稱'], 'meeting': e['目標會期'].date(), 'info_time': info,
               'entry_time': f"{ent_d.date()} 09:00", 'cluster': str(ent_d.date()), 'sample': '樣本內'}
        if isinstance(t, str):
            row.update({'entry_date': ent_d, 'exit_date': ext_d, 'entry_px': np.nan, 'exit_px': np.nan, 'ret': np.nan, 'hold_days': H, 'excluded_reason': t})
        else:
            row.update(t); row['excluded_reason'] = None
            cr = []
            for c in ctl[(ctl['年月'] == e['年月']) & (ctl['公司代號'] != e['公司代號'])]['公司代號'].unique():
                tc = short_trade(c, ent_d, t['exit_date'])
                if isinstance(tc, dict) and tc['exit_date'] == t['exit_date']: cr.append(tc['ret'])
            row['ctl_n'] = len(cr); row['excess'] = row['ret'] - float(np.mean(cr)) if cr else np.nan
        rows.append(row)
T = pd.DataFrame(rows)
T.to_pickle(f'{W}/out/qs_etest_short.pkl')
print(T.groupby('combo').agg(n=('trade_id', 'size'), 納入=('ret', 'count'), 有對照=('excess', 'count'), 平盤下限制=('downtick_flag', 'sum')).to_string())
print(T[T['excluded_reason'].notna()].groupby('excluded_reason').size().to_string())
