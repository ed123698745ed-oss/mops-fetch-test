# 032 報告用補充表與參數全表（Elon）；輸入為 bt032.py 輸出
import pandas as pd, numpy as np, sys, glob
sys.path.insert(0, '/home/claude/mops-fetch-test')
from bt_stats import summarize
D = '/home/claude/p032'
T = pd.read_csv(f'{D}/out_trades.csv', dtype={'公司代號': str, 'cid': str})
T['每試驗一件保留'] = T['每試驗一件保留'].astype(str) == 'True'
T['S日停牌'] = T['S日停牌'].astype(str) == 'True'
T['年度'] = pd.to_datetime(T['進場日']).dt.year
allg = T.copy(); allg['結果分類'] = '全部'
A = pd.concat([T, allg])

def stat(g):
    return summarize(g['報酬'].astype(float).tolist(), hold_days=g['持有交易日數'].astype(int).tolist(),
                     cluster=g['進場日'].astype(str).tolist(), cluster_unit='進場日')
def table(df, by, name):
    out = []
    for keys, g in df.groupby(by, dropna=False):
        out.append(dict(zip(by, keys if isinstance(keys, tuple) else (keys,)), **stat(g)))
    o = pd.DataFrame(out); o.to_csv(f'{D}/tab_{name}.csv', index=False, encoding='utf-8-sig'); return o

# 1. 年度（A保守，全部）
table(T[T['版本'] == 'A保守'], ['方向', 'H', '年度'], 'A保守_年度')
# 2. 排除最大貢獻事件、排除最大貢獻公司（以 |報酬總和| 最大者，依方向×H×分類各自判定）
rows = []
for (side, H, cls), g in A[A['版本'] == 'A保守'].groupby(['方向', 'H', '結果分類']):
    ev = g.groupby('cid')['報酬'].sum(); top_e = ev.abs().idxmax()
    co = g.groupby('公司代號')['報酬'].sum(); top_c = co.abs().idxmax()
    for lab, gg, who in [('排除最大貢獻事件', g[g['cid'] != top_e], top_e), ('排除最大貢獻公司', g[g['公司代號'] != top_c], top_c)]:
        if len(gg) == 0: continue
        name = g.loc[g['cid'] == who, '公司名稱'].iloc[0] if lab.endswith('事件') else g.loc[g['公司代號'] == who, '公司名稱'].iloc[0]
        rows.append(dict(方向=side, H=H, 結果分類=cls, 敏感度=lab, 被排除=f'{who} {name}', **stat(gg)))
pd.DataFrame(rows).to_csv(f'{D}/tab_A保守_排除最大貢獻.csv', index=False, encoding='utf-8-sig')
# 3. 共同完整樣本（A保守：同一事件在 7 個持有期皆有成交者）
ok = T[T['版本'] == 'A保守'].groupby(['cid', '方向'])['H'].nunique()
full = ok[ok == 7].reset_index()[['cid', '方向']]
cc = A[A['版本'] == 'A保守'].merge(full, on=['cid', '方向'])
table(cc, ['方向', 'H', '結果分類'], 'A保守_共同完整樣本')
# 4. 停牌組價格反應（E-Test 2 補充）
table(A[A['版本'] == 'A價格反應'], ['方向', 'H', '結果分類', 'S日停牌'], 'ET2_停牌組_價格反應')
# 5. 公司集中度
ev = pd.read_csv(f'{D}/out_events.csv', dtype={'公司代號': str})
ev.groupby(['公司代號', '公司名稱']).size().sort_values(ascending=False).rename('事件數').reset_index() \
  .to_csv(f'{D}/tab_公司集中度.csv', index=False, encoding='utf-8-sig')
# 6. Holm：A保守主表家族（2方向×7持有期×4分類＝56項，以聚合p）
h = pd.read_csv(f'{D}/tab_A_結果分類.csv'); h = h[h['版本'] == 'A保守'].copy()
p = h['聚合p'].fillna(h['雙尾p']).values; m = len(p); order = np.argsort(p)
adj = np.empty(m); run = 0
for rank, i in enumerate(order):
    run = max(run, min(1.0, (m - rank) * p[i])); adj[i] = run
h['Holm校正p'] = adj; h.to_csv(f'{D}/tab_A保守_Holm.csv', index=False, encoding='utf-8-sig')
# 7. 未完成／排除計數
X = pd.read_csv(f'{D}/out_excluded.csv')
pd.crosstab([X['版本'], X['方向'], X['H']], X['排除原因']).to_csv(f'{D}/tab_排除計數.csv', encoding='utf-8-sig')
# 8. 參數全表（全部 tab_ 表合併）
parts = []
for f in sorted(glob.glob(f'{D}/tab_*.csv')):
    if '參數全表' in f or '排除計數' in f or '公司集中度' in f: continue
    t = pd.read_csv(f); t.insert(0, '表名', f.split('tab_')[1][:-4]); parts.append(t)
P = pd.concat(parts, ignore_index=True)
P.to_csv(f'{D}/032_回測結果_參數全表_V01_R01.csv', index=False, encoding='utf-8-sig')
print('參數全表列數', len(P))
print(h.sort_values('Holm校正p')[['方向', 'H', '結果分類', '樣本數', '平均報酬', '聚合p', 'Holm校正p']].head(8).to_string())
