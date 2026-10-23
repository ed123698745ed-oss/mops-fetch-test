# 產生 032 回測結果／E-Test 附錄 的表格 markdown 片段（Elon）
import pandas as pd, numpy as np
D = '/home/claude/p032'
def pc(x, d=2): return 'N/A' if pd.isna(x) else f'{x*100:.{d}f}%'
def nm(x, d=2): return 'N/A' if pd.isna(x) else f'{x:.{d}f}'
def pv(x): return 'N/A' if pd.isna(x) else ('<0.0001' if x < 1e-4 else f'{x:.4f}')
HDR = '| 組合ID | 方向 | H | 分類 | 樣本數 | 平均報酬 | 平均持有交易日數 | 單筆資金周轉年化(單利) | 勝率 | 賠率R | 凱利 | 半凱利 | 標準差 | t值 | 雙尾p | 聚合單位數 | 聚合p | N/A原因 |\n|' + '---|' * 18 + '\n'
def full(t, idp, extra=None):
    s = HDR
    for _, r in t.iterrows():
        cls = r.get(extra) if extra else r['結果分類']
        cid = f"{idp}-{'L' if r['方向']=='做多' else 'S'}{int(r['H'])}-{cls}"
        s += f"| {cid} | {r['方向']} | {int(r['H'])} | {cls} | {int(r['樣本數'])} | {pc(r['平均報酬'])} | {nm(r['平均持有交易日數'],1)} | {pc(r['單利年化'],1)} | {pc(r['勝率'],1)} | {nm(r['賠率R'])} | {pc(r['凱利'],1)} | {pc(r['半凱利'],1)} | {pc(r['標準差'],1)} | {nm(r['t值'])} | {pv(r['雙尾p'])} | {int(r['聚合單位數']) if not pd.isna(r['聚合單位數']) else 'N/A'} | {pv(r['聚合p'])} | {'' if pd.isna(r['N/A原因']) else r['N/A原因']} |\n"
    return s
def cell(r): return f"n={int(r['樣本數'])} {pc(r['平均報酬'],1)} p={pv(r['聚合p'] if not pd.isna(r['聚合p']) else r['雙尾p'])}"
def grid(t, rowkey, rows, Hs=(1, 3, 10, 20)):
    s = '| 組別 | ' + ' | '.join(f'H{h}' for h in Hs) + ' |\n|' + '---|' * (len(Hs) + 1) + '\n'
    for rv in rows:
        line = f'| {rv} |'
        for h in Hs:
            q = t[(t[rowkey] == rv) & (t['H'] == h)]
            line += f' {cell(q.iloc[0]) if len(q) else "—"} |'
        s += line + '\n'
    return s
CL = ['全部', '達標', '未達標', '無法判定']
order = lambda t: t.assign(_c=t['結果分類'].map({c: i for i, c in enumerate(CL)})).sort_values(['方向', 'H', '_c'])
out = {}
a = pd.read_csv(f'{D}/tab_A_結果分類.csv')
out['A保守'] = full(order(a[a['版本'] == 'A保守']), 'A1')
out['A價格全部'] = full(order(a[(a['版本'] == 'A價格反應')]), 'A2')
b = pd.read_csv(f'{D}/tab_B保守.csv'); b = b[b['結果分類'] == '全部'].sort_values(['鎖板方向', '方向', 'H'])
s = ''
for lk, g in b.groupby('鎖板方向', sort=False):
    g = g.copy(); g['結果分類'] = lk; s += full(g, 'B1' if lk == '連續鎖漲停' else 'B2')
out['B'] = s
bb = pd.read_csv(f'{D}/tab_B保守.csv'); bb = bb[bb['結果分類'] != '全部']
s = ''
for (lk, side), g in bb.groupby(['鎖板方向', '方向']):
    g = g.copy(); g['k'] = g['結果分類']; s += f'\n**{lk}｜{side}**\n\n' + grid(g, 'k', sorted(g['k'].unique()))
out['B分類'] = s
ph = pd.read_csv(f'{D}/tab_A_期別.csv'); ph = ph[ph['版本'] == 'A保守']
s = ''
for side in ['做多', '放空']:
    g = ph[ph['方向'] == side].copy(); g['k'] = g['期別組'] + '｜' + g['結果分類']
    s += f'\n**{side}**\n\n' + grid(g, 'k', sorted(g['k'].unique()))
out['期別'] = s
s = ''
for f, key, title in [('A保守_指標性質', '指標性質', '指標性質'), ('A保守_結果階段', '結果階段', '結果階段')]:
    t = pd.read_csv(f'{D}/tab_{f}.csv')
    for side in ['做多', '放空']:
        g = t[t['方向'] == side]; s += f'\n**{title}｜{side}**\n\n' + grid(g, key, sorted(g[key].dropna().unique()))
out['性質階段'] = s
# 敏感度
s = ''
one = pd.read_csv(f'{D}/tab_A保守_每試驗一件.csv'); cc = pd.read_csv(f'{D}/tab_A保守_共同完整樣本.csv')
ex = pd.read_csv(f'{D}/tab_A保守_排除最大貢獻.csv')
for side in ['做多', '放空']:
    rows = []
    for nmx, t in [('主表', a[a['版本'] == 'A保守']), ('每試驗只算一件', one), ('共同完整樣本', cc)]:
        for c in ['全部', '達標']:
            q = t[(t['方向'] == side) & (t['結果分類'] == c)].copy(); q['k'] = f'{nmx}｜{c}'; rows.append(q)
    for lab in ['排除最大貢獻事件', '排除最大貢獻公司']:
        for c in ['全部', '達標']:
            q = ex[(ex['方向'] == side) & (ex['結果分類'] == c) & (ex['敏感度'] == lab)].copy(); q['k'] = f'{lab}｜{c}'; rows.append(q)
    g = pd.concat(rows); s += f'\n**{side}**\n\n' + grid(g, 'k', list(dict.fromkeys(g['k'])))
out['敏感度'] = s
ex2 = ex[(ex['結果分類'].isin(['全部', '達標'])) & (ex['H'].isin([1, 3, 10]))][['方向', 'H', '結果分類', '敏感度', '被排除']]
out['被排除清單'] = '| 方向 | H | 分類 | 敏感度 | 被排除 |\n|---|---|---|---|---|\n' + ''.join(f"| {r.方向} | {r.H} | {r.結果分類} | {r.敏感度} | {r.被排除} |\n" for r in ex2.itertuples())
# 期間切分＋最新年度
pe = pd.read_csv(f'{D}/tab_A保守_期間切分.csv'); yr = pd.read_csv(f'{D}/tab_A保守_年度.csv')
s = ''
for side in ['做多', '放空']:
    rows = []
    for c in ['全部', '達標', '未達標', '無法判定']:
        for per in ['2010–2020', '2021–2026']:
            q = pe[(pe['方向'] == side) & (pe['結果分類'] == c) & (pe['期間'] == per)].copy(); q['k'] = f'{c}｜{per}'; rows.append(q)
    q = yr[(yr['方向'] == side) & (yr['年度'] == 2026)].copy(); q['k'] = '全部｜最新年度2026'; rows.append(q)
    g = pd.concat(rows); s += f'\n**{side}**\n\n' + grid(g, 'k', list(dict.fromkeys(g['k'])))
out['期間'] = s
# 年度（全部，H1、H10）
s = '| 年度 | 做多H1 | 做多H10 | 放空H1 | 放空H10 |\n|---|---|---|---|---|\n'
for y in sorted(yr['年度'].unique()):
    line = f'| {y} |'
    for side, h in [('做多', 1), ('做多', 10), ('放空', 1), ('放空', 10)]:
        q = yr[(yr['年度'] == y) & (yr['方向'] == side) & (yr['H'] == h)]
        line += f' {cell(q.iloc[0]) if len(q) else "—"} |'
    s += line + '\n'
out['年度'] = s
# 事前20日、跳空
pre = pd.read_csv(f'{D}/tab_A保守_事前20日.csv'); gp = pd.read_csv(f'{D}/tab_A價格反應_跳空描述.csv')
s = ''
for side in ['做多', '放空']:
    g = pre[(pre['方向'] == side) & (pre['結果分類'].isin(['全部', '達標', '未達標']))].copy(); g['k'] = g['結果分類'] + '｜事前' + g['事前20日組']
    s += f'\n**事前20日漲跌（A保守）｜{side}**\n\n' + grid(g, 'k', list(dict.fromkeys(g.sort_values(['結果分類', '事前20日組'])['k'])))
for side in ['做多']:
    g = gp[(gp['方向'] == side) & (gp['結果分類'].isin(['全部', '達標', '未達標']))].copy(); g['k'] = g['結果分類'] + '｜跳空' + g['跳空組']
    s += f'\n**E開盤跳空（A價格反應，僅描述）｜{side}（放空為鏡像）**\n\n' + grid(g, 'k', list(dict.fromkeys(g.sort_values(['結果分類', '跳空組'])['k'])))
out['事前跳空'] = s
h = pd.read_csv(f'{D}/tab_A保守_Holm.csv').sort_values('Holm校正p')
h = h[h['Holm校正p'] < 0.2]
out['Holm'] = '| 方向 | H | 分類 | 樣本數 | 平均報酬 | 聚合p | Holm校正p |\n|---|---|---|---|---|---|---|\n' + ''.join(
    f"| {r.方向} | {r.H} | {r.結果分類} | {r.樣本數} | {pc(r.平均報酬)} | {pv(r.聚合p)} | {pv(r.Holm校正p)} |\n" for r in h.itertuples())
co = pd.read_csv(f'{D}/tab_公司集中度.csv', dtype={'公司代號': str}).head(8)
out['集中度'] = '| 公司 | 事件數 |\n|---|---|\n' + ''.join(f'| {r.公司代號} {r.公司名稱} | {r.事件數} |\n' for r in co.itertuples())
# E-Test
e1 = pd.read_csv(f'{D}/tab_ET1_時段.csv')
s = ''
for ver in ['ET1保守', 'ET1價格反應']:
    g = e1[(e1['版本'] == ver) & (e1['結果分類'] == '全部')].copy(); g['結果分類'] = g['時段']
    s += f'\n**{ver}｜全部**\n\n' + full(g.sort_values(['時段', '方向', 'H']), 'E1' if ver == 'ET1保守' else 'E1P')
g = e1[(e1['版本'] == 'ET1保守') & (e1['結果分類'] != '全部')].copy();
for side in ['做多', '放空']:
    q = g[g['方向'] == side].copy(); q['k'] = q['時段'] + '｜' + q['結果分類']
    s += f'\n**ET1保守 依結果分類｜{side}**\n\n' + grid(q, 'k', sorted(q['k'].unique()), Hs=(1, 3, 10))
ep = pd.read_csv(f'{D}/tab_ET1_期間切分.csv'); q = ep[(ep['版本'] == 'ET1保守') & (ep['結果分類'] == '全部')].copy(); q['k'] = q['方向'] + '｜' + q['期間']
s += '\n**ET1保守 樣本內外參考切分（全部）**\n\n' + grid(q, 'k', sorted(q['k'].unique()), Hs=(1, 3, 10))
out['ET1'] = s
s = ''
for f, ver in [('ET2_停牌組', 'A保守'), ('ET2_停牌組_價格反應', 'A價格反應')]:
    t = pd.read_csv(f'{D}/tab_{f}.csv'); t = t[t['S日停牌'] == True].copy()
    t['結果分類'] = t['結果分類'] + '·停牌'
    s += f'\n**停牌組｜{ver}**\n\n' + full(t.sort_values(['方向', 'H', '結果分類']), 'E2' if ver == 'A保守' else 'E2P')
out['ET2'] = s
pe2 = pd.read_csv(f'{D}/ET2_停牌組逐筆.csv')
out['ET2逐筆'] = pe2.to_markdown(index=False)
import json; json.dump(out, open(f'{D}/md_parts.json', 'w'), ensure_ascii=False)
print({k: len(v) for k, v in out.items()})
