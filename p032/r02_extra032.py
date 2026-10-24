# 032 R02 補充（Elon，2026-10-24）：依 Eve R01 審查與 Ed 2026-10-24 11:51 單次例外
# (1) 持有期間遇除權息／減資／分割／現增（還原因子≠1）之交易全部剔除的敏感度
# (2) ET2 停牌組樣本外切分（2010–2020／2021–2026）
import pandas as pd, numpy as np, sys
sys.path.insert(0, '/home/claude/mops-fetch-test'); from bt_stats import summarize
D = '/home/claude/p032'
T = pd.read_csv(f'{D}/out_trades.csv', dtype={'公司代號': str})
T['跨公司行動'] = T['還原因子'].sub(1).abs() > 1e-12
def st(g): return summarize(g['報酬'].tolist(), hold_days=g['持有交易日數'].astype(int).tolist(), cluster=g['進場日'].astype(str).tolist(), cluster_unit='進場日')
allg = T.copy(); allg['結果分類'] = '全部'; A = pd.concat([T, allg])
rows = [dict(版本=v, 方向=s, H=H, 結果分類=c, **st(g)) for (v, s, H, c), g in A[A['版本'].isin(['A保守', 'A價格反應']) & ~A['跨公司行動']].groupby(['版本', '方向', 'H', '結果分類'])]
pd.DataFrame(rows).to_csv(f'{D}/tab_A_排除公司行動.csv', index=False, encoding='utf-8-sig')
h = T[T['S日停牌'].astype(str) == 'True'].copy()
h['期間'] = np.where(pd.to_datetime(h['進場日']) < pd.Timestamp('2021-01-01'), '2010–2020', '2021–2026')
rows = [dict(版本=v, 方向=s, 期間=p, H=H, **st(g)) for (v, s, p, H), g in h[h['版本'].isin(['A價格反應', 'A保守'])].groupby(['版本', '方向', '期間', 'H'])]
pd.DataFrame(rows).to_csv(f'{D}/tab_ET2_停牌組_期間切分.csv', index=False, encoding='utf-8-sig')
print('剔除筆數', int(T['跨公司行動'].sum()), '事件數', T[T['跨公司行動']]['cid'].nunique())
