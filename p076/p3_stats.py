# 076 快篩統計：bt_stats v1.2 十項統計＋回撤三項（樣本內）；含息報酬與對照組超額分表
import sys, pandas as pd, numpy as np
sys.path.insert(0, '/home/claude/w076/code')
from elon_tools import load_bt_stats, ten_table, dd_table, to_markdown, dd_markdown, selfcheck, print_check
W = '/home/claude/w076'
bt = load_bt_stats(f'{W}/共用統計函式_bt_stats_v1.2.py')
T = pd.read_pickle(f'{W}/out/qs_trades.pkl')
T['excluded_reason'] = T['excluded_reason'].where(T['excluded_reason'].notna(), None)
order = ['D|M', 'D|H5', 'D|H10', 'D|H20', 'T|M', 'T|H5', 'T|H10', 'T|H20', 'D|E1', 'T|E1']
out = {}
for name, et in [('策略卡', False), ('E-Test', True)]:
    t = T[T['is_etest'] == et].copy()
    raw = ten_table(t, bt, by=('combo',), cluster_unit='進場日')
    x = t.copy()
    x.loc[x['excess'].isna() & x['excluded_reason'].isna(), 'excluded_reason'] = '同年月無對照組'
    x['ret'] = x['excess']
    exc = ten_table(x, bt, by=('combo',), cluster_unit='進場日')
    dd = dd_table(t, bt, by=('combo',))
    for tb in (raw, exc, dd):
        tb['_o'] = tb['combo'].map({c: i for i, c in enumerate(order)}); tb.sort_values('_o', inplace=True); tb.drop(columns='_o', inplace=True)
    out[name] = (raw, exc, dd, t, x)
    print(f'===== {name}：含息報酬'); print(to_markdown(raw.drop(columns=['bt_stats版本'])))
    print(f'===== {name}：減對照組超額'); print(to_markdown(exc.drop(columns=['bt_stats版本'])))
    print(f'===== {name}：回撤三項（含息報酬）'); print(dd_markdown(dd))
    cal = list(pd.read_parquet(f'{W}/calendar.parquet')['date'])
    res = selfcheck(t, bt, reported=raw, reported_dd=dd, by=('combo',), cluster_unit='進場日', quick=True,
                    calendar=cal, split=('2021-12-31', '2022-04-11'), etest=et)
    print_check(res)
pd.to_pickle(out, f'{W}/out/qs_stats.pkl')
