# 076 經營權之爭搶籌碼策略｜快篩（只用樣本內，樣本外封存）
# 資料：elon-bt data-20261105r68（daily_k、corp_actions、calendar）；事件：p1 人工判讀 D／T
# 組合（策略卡）：M＝持有到最後可買進日收盤（訊號早於 60 交易日者延到最後可買進日前第 59 個交易日開盤，持有 60 日）；
#                H5／H10／H20＝訊號進場日起固定持有 H 個交易日（上限最後可買進日）
# 組合（E-Test，D-076-20261108-2056-1）：E1＝訊號進場日開盤進場、不設 60 日上限，持有到最後可買進日收盤
# 報酬：研究預設口徑 V04 固定股數加實得現金；現增除權不認購；除權息未分類（資料不足）或持有期間跳動 → 排除
# 成交（L1）：進場開盤一價鎖漲停、停牌／零量、限幅待查或缺參考價 → 無法成交（排除）；
#             出場日一價鎖跌停或停牌 → 順延至下一個可賣出交易日收盤（標記）
# 超額：同年月（以最後可買進日計）有全面改選、無 S1 訊號的上市櫃公司，同一進出日等權報酬
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/home/claude/w076/code')
from elon_tools import share_return
W = '/home/claude/w076'
IS_END, OOS_START = pd.Timestamp('2021-12-31'), pd.Timestamp('2022-04-11')
CAL = pd.DatetimeIndex(pd.read_parquet(f'{W}/calendar.parquet')['date'].dt.normalize().sort_values())
def idx(d): return CAL.searchsorted(pd.Timestamp(d))

ev = pd.read_csv(f'{W}/out/s1_events_labeled.csv', dtype={'公司代號': str, '發言日期': str, '發言時間': str},
                 parse_dates=['進場日', '最後可買進日', '目標會期'])
ev = ev[ev['可交易'] & ev['判讀'].isin(['D', 'T'])].copy()
ev['樣本'] = ['樣本內' if b <= IS_END else ('樣本外' if e >= OOS_START else '跨越') for e, b in zip(ev['進場日'], ev['最後可買進日'])]
ev = ev[ev['樣本'] == '樣本內'].reset_index(drop=True)          # 快篩只用樣本內
ctl = pd.read_csv(f'{W}/out/control.csv', dtype={'公司代號': str}, parse_dates=['最後可買進日'])
ctl = ctl[ctl['最後可買進日'] <= IS_END]
ev['年月'] = ev['最後可買進日'].dt.to_period('M').astype(str)
need = set(ev['公司代號']) | set(ctl[ctl['年月'].isin(set(ev['年月']))]['公司代號'])

K = pd.read_parquet(f'{W}/daily_k.parquet', filters=[('stock_id', 'in', sorted(need)), ('date', '>=', pd.Timestamp('2007-06-01'))])
K['date'] = K['date'].dt.normalize()
KG = {k: g.set_index('date').sort_index() for k, g in K.groupby('stock_id')}
CA = pd.read_parquet(f'{W}/corp_actions.parquet'); CA = CA[CA['stock_id'].isin(need)]
CAG = {k: g for k, g in CA.groupby('stock_id')}

def actions(sym, a, b):
    """(entry, exit] 間公司行動 → share_return 事件；資料不足回傳 None。"""
    g = CAG.get(sym)
    out = []
    if g is None: return out
    g = g[(g['ex_date'] > a) & (g['ex_date'] <= b)]
    for r in g.itertuples():
        if r.kind == '現金股利': out.append({'date': r.ex_date, 'cash': float(r.cash or 0)})
        elif r.kind == '配股':
            if pd.isna(r.share_ratio): return None
            out.append({'date': r.ex_date, 'cash': float(r.cash or 0) if pd.notna(r.cash) else 0.0, 'stock': float(r.share_ratio) - 1})
        elif r.kind == '減資':
            if pd.isna(r.share_ratio): return None
            out.append({'date': r.ex_date, 'swap': float(r.share_ratio), 'refund': float(r.cash or 0) if pd.notna(r.cash) else 0.0})
        elif r.kind == '現增除權': pass                       # 不認購：固定股數不變
        else: return None                                     # 除權息未分類、面額變更待公告 → 資料不足
    return out

def bar(sym, d):
    g = KG.get(sym)
    if g is None or d not in g.index: return None
    return g.loc[d]

def can_buy_open(b):
    if b is None: return False, '無行情'
    if str(b.get('limit_src') or '').startswith('待查') or b.get('limit_src') == '缺參考價': return False, '資料不足：限幅待查或缺參考價'
    if bool(b.get('no_trade')) or not (b.get('volume', 0) > 0): return False, '停牌或零量'
    if b['open'] == b['high'] == b['low'] == b['close'] and pd.notna(b.get('limit_up')) and b['open'] >= b['limit_up']: return False, '一價鎖漲停，買不到'
    return True, ''

def can_sell_close(b):
    if b is None: return False
    if bool(b.get('no_trade')) or not (b.get('volume', 0) > 0): return False
    if str(b.get('limit_src') or '').startswith('待查') or b.get('limit_src') == '缺參考價': return False
    if b['open'] == b['high'] == b['low'] == b['close'] and pd.notna(b.get('limit_down')) and b['close'] <= b['limit_down']: return False
    return True

def trade(sym, ent_d, ext_d, jump_check=True):
    """回傳 dict（ret 等）或排除原因字串。"""
    b = bar(sym, ent_d)
    ok, why = can_buy_open(b)
    if not ok: return why
    i = idx(ext_d); delay = 0
    while True:
        if i >= len(CAL): return '出場順延超出資料'
        bx = bar(sym, CAL[i])
        if can_sell_close(bx): break
        i += 1; delay += 1
        if delay > 60: return '出場順延超過 60 交易日'
    xd = CAL[i]
    g = KG[sym]
    if jump_check:
        w = g.loc[(g.index > ent_d) & (g.index <= xd)]
        if w['jump_flag'].fillna(False).any(): return '持有期間跳動查無公司行動'
    evs = actions(sym, ent_d, xd)
    if evs is None: return '持有期間公司行動資料不足'
    r = share_return(ent_d, float(b['open']), xd, float(bx['close']), evs)
    return {'entry_date': ent_d, 'entry_px': float(b['open']), 'exit_date': xd, 'exit_px': float(bx['close']),
            'ret': r, 'hold_days': int(i - idx(ent_d) + 1), 'exit_delay': delay}

COMBOS = [('M', False), ('H5', False), ('H10', False), ('H20', False), ('E1', True)]
rows = []
for k, e in ev.iterrows():
    sig_i, lb_i = idx(e['進場日']), idx(e['最後可買進日'])
    for combo, is_et in COMBOS:
        if combo == 'M':  ei, xi = max(sig_i, lb_i - 59), lb_i
        elif combo == 'E1': ei, xi = sig_i, lb_i
        else:
            H = int(combo[1:]); ei, xi = sig_i, min(sig_i + H - 1, lb_i)
        ent_d, ext_d = CAL[ei], CAL[xi]
        t = trade(e['公司代號'], ent_d, ext_d)
        hh = '09:00' if str(e['發言時間']).zfill(6) < '090000' else None
        info = f"{e['發言日期'][:4]}-{e['發言日期'][4:6]}-{e['發言日期'][6:]} {str(e['發言時間']).zfill(6)[:2]}:{str(e['發言時間']).zfill(6)[2:4]}"
        row = {'trade_id': f"{combo}-{e['公司代號']}-{e['發言日期']}", 'combo': f"{e['判讀']}|{combo}", 'group': e['判讀'],
               'is_etest': is_et, 'symbol': e['公司代號'], 'name': e['公司名稱'], 'signal_time': info,
               'info_time': info, 'entry_time': f"{ent_d.date()} 09:00", 'last_buy': e['最後可買進日'].date(),
               'meeting': e['目標會期'].date(), 'cluster': str(ent_d.date()), 'sample': '樣本內', 'ym': e['年月']}
        if isinstance(t, str):
            row.update({'entry_date': ent_d, 'exit_date': ext_d, 'entry_px': np.nan, 'exit_px': np.nan, 'ret': np.nan,
                        'hold_days': xi - ei + 1, 'exit_delay': 0, 'excluded_reason': t})
        else:
            row.update(t); row['excluded_reason'] = None
            # 對照組：同年月、同一進出日
            cs = ctl[(ctl['年月'] == e['年月']) & (ctl['公司代號'] != e['公司代號'])]['公司代號'].unique()
            cr = []
            for c in cs:
                tc = trade(c, ent_d, t['exit_date'])
                if isinstance(tc, dict) and tc['exit_date'] == t['exit_date']: cr.append(tc['ret'])
            row['ctl_n'] = len(cr); row['ctl_ret'] = float(np.mean(cr)) if cr else np.nan
            row['excess'] = row['ret'] - row['ctl_ret'] if cr else np.nan
        rows.append(row)
T = pd.DataFrame(rows)
T.to_pickle(f'{W}/out/qs_trades.pkl')
print(T.groupby('combo').agg(n=('trade_id', 'size'), 納入=('ret', 'count'), 有對照=('excess', 'count')).to_string())
print(T[T['excluded_reason'].notna()].groupby(['combo', 'excluded_reason']).size().to_string())
