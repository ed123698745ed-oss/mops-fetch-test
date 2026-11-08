# 076 快篩：事件時間軸（描述性，只用樣本內）與 D1 回落段（描述性）
# 第 0 日＝訊號進場日；每日報酬＝收盤對收盤含息（固定股數加實得現金，同口徑 V04）；
# 超額＝個股日報酬－同年月對照組等權日報酬；公司行動資料不足或跳動日視為缺值不計
import sys, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager
sys.path.insert(0, '/home/claude/w076/code')
W = '/home/claude/w076'
for f in font_manager.findSystemFonts():
    if 'NotoSansCJK-Regular' in f: font_manager.fontManager.addfont(f)
plt.rcParams['font.family'] = 'Noto Sans CJK TC'
CAL = pd.DatetimeIndex(pd.read_parquet(f'{W}/calendar.parquet')['date'].dt.normalize().sort_values())
T = pd.read_pickle(f'{W}/out/qs_trades.pkl')
ev = T[T['combo'].str.endswith('|H5')][['group', 'symbol', 'signal_time', 'last_buy', 'meeting', 'ym']].copy()
ev['day0'] = T[T['combo'].str.endswith('|H5')]['entry_date'].values
ctl = pd.read_csv(f'{W}/out/control.csv', dtype={'公司代號': str}, parse_dates=['最後可買進日'])
need = set(ev['symbol']) | set(ctl[ctl['年月'].isin(set(ev['ym']))]['公司代號'])
K = pd.read_parquet(f'{W}/daily_k.parquet', filters=[('stock_id', 'in', sorted(need)), ('date', '>=', pd.Timestamp('2007-01-01'))],
                    columns=['stock_id', 'date', 'close', 'volume', 'no_trade', 'jump_flag'])
K['date'] = K['date'].dt.normalize()
CA = pd.read_parquet(f'{W}/corp_actions.parquet'); CA = CA[CA['stock_id'].isin(need)]
def daily_ret(sym):
    g = K[K['stock_id'] == sym].set_index('date').sort_index()
    g = g[(~g['no_trade'].fillna(False)) & (g['volume'] > 0)]
    mult = pd.Series(1.0, index=g.index); cash = pd.Series(0.0, index=g.index); bad = pd.Series(False, index=g.index)
    for r in CA[CA['stock_id'] == sym].itertuples():
        d = r.ex_date
        if d not in g.index: continue
        if r.kind == '現金股利': cash[d] += float(r.cash or 0)
        elif r.kind == '配股' and pd.notna(r.share_ratio): mult[d] *= float(r.share_ratio); cash[d] += float(r.cash or 0) if pd.notna(r.cash) else 0
        elif r.kind == '減資' and pd.notna(r.share_ratio): cash[d] += float(r.cash or 0) if pd.notna(r.cash) else 0; mult[d] *= float(r.share_ratio)
        elif r.kind == '現增除權': pass
        else: bad[d] = True
    rr = (g['close'] * mult + cash) / g['close'].shift() - 1
    rr[bad | g['jump_flag'].fillna(False)] = np.nan
    return rr.reindex(CAL)            # 停牌日為 NaN
R = {s: daily_ret(s) for s in need}
ctlm = {}
for ym in set(ev['ym']):
    L = [R[c] for c in ctl[ctl['年月'] == ym]['公司代號'].unique() if c in R]
    ctlm[ym] = pd.concat(L, axis=1).mean(axis=1) if L else pd.Series(np.nan, index=CAL)   # 同年月無對照組：該事件超額全為缺值
rel = np.arange(-60, 61)
rows = []
for e in ev.itertuples():
    i0 = CAL.searchsorted(e.day0)
    idxs = [i0 + k for k in rel]
    if idxs[0] < 0 or idxs[-1] >= len(CAL): continue
    d = CAL[idxs]
    ex = (R[e.symbol].loc[d].values - ctlm[e.ym].loc[d].values)
    rows.append({'group': e.group, 'ex': ex,
                 'lb': CAL.searchsorted(pd.Timestamp(e.last_buy)) - i0, 'mt': CAL.searchsorted(pd.Timestamp(e.meeting)) - i0})
out = {}
fig, ax = plt.subplots(figsize=(9, 4.8), dpi=150)
for g, col in (('D', '#2a78d6'), ('T', '#eb6834')):
    m = np.array([r['ex'] for r in rows if r['group'] == g])
    avg = np.nanmean(m, axis=0)   # 第 -1 日累積歸零
    car = np.nancumsum(avg); car = car - car[59]
    lb = np.median([r['lb'] for r in rows if r['group'] == g]); mt = np.median([r['mt'] for r in rows if r['group'] == g])
    out[g] = {'n': len(m), 'car': car, 'lb_med': lb, 'mt_med': mt}
    lab = '經營權爭議（D）' if g == 'D' else '被第三方公開收購（T）'
    ax.plot(rel, car * 100, color=col, lw=2, label=f'{lab}，n={len(m)}')
    ax.axvline(lb, color=col, lw=1, ls='--'); ax.text(lb, ax.get_ylim()[1] if False else 0, '', color=col)
ax.axvline(0, color='#888', lw=1)
ax.axhline(0, color='#bbb', lw=0.8)
ax.set_xlabel('相對訊號進場日的交易日（第 0 日＝訊號後第一個可進場日）')
ax.set_ylabel('平均累積超額報酬（%，減同年月對照組）')
ax.set_title('076 事件時間軸（樣本內，描述性；虛線＝最後可買進日中位數）', fontsize=11)
ax.legend(frameon=False, loc='upper left'); ax.grid(axis='y', color='#eee'); [s.set_visible(False) for s in (ax.spines['top'], ax.spines['right'])]
fig.tight_layout(); fig.savefig(f'{W}/out/076_事件時間軸_樣本內.png')
tab = pd.DataFrame({g: [out[g]['car'][60 + k] for k in (-60, -20, -5, -1, 0, 5, 20, 40, 60)] for g in out},
                   index=[f'第{k}日' for k in (-60, -20, -5, -1, 0, 5, 20, 40, 60)])
print('n', {g: out[g]['n'] for g in out}, '最後可買進日中位數', {g: out[g]['lb_med'] for g in out}, '會期中位數', {g: out[g]['mt_med'] for g in out})
print((tab * 100).round(2).to_string())
pd.to_pickle({'tab': tab, 'meta': {g: {k: v for k, v in out[g].items() if k != 'car'} for g in out}}, f'{W}/out/qs_timeline.pkl')
