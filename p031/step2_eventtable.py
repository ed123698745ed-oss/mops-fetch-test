# 031 步驟2：回測事件表。路線 A（主動退出首次確認）、B（同案首次公告接任，僅 B 晚於 A 者另建交易）、比較組（公司更換／輪調／其他／不明）
import pandas as pd
A = pd.read_csv('A_events_pool.csv', dtype=str).fillna(''); C = pd.read_csv('C_events_pool.csv', dtype=str).fillna('')
ov = pd.read_csv('overlap.csv', dtype=str).fillna('').set_index('事件ID')['同期事件'].to_dict()
rows = []
for _, r in A.iterrows():
    base = dict(公司代號=r['公司代號'], 公司名稱=r['公司名稱'], 案件ID=r['事件ID'], A接任狀態=r['A接任狀態'], 股票池=r['股票池'], 後來下市=r['後來下市'])
    rows.append(dict(base, 事件ID=r['事件ID'], 路線='A', S=r['S日期'], 時間=r['S時間'], E=r['E'], 主旨=r['主旨'], 同期事件=ov.get(r['事件ID'], '')))
    if r['B日期']:
        bid = r['事件ID'].replace('A-', 'B-', 1)
        rows.append(dict(base, 事件ID=bid, 路線='B', S=r['B日期'], 時間=r['B時間'], E=r['BE'], 主旨='（同案接任公告）新所：' + r['B新所'], 同期事件=ov.get(bid, '')))
for _, r in C.iterrows():
    rows.append(dict(公司代號=r['公司代號'], 公司名稱=r['公司名稱'], 案件ID='', A接任狀態='', 股票池=r['股票池'], 後來下市=r['後來下市'],
                     事件ID=r['事件ID'], 路線=r['分類'], S=r['S日期'], 時間=r['S時間'], E=r['E'], 主旨=r['主旨'], 同期事件=ov.get(r['事件ID'], '')))
d = pd.DataFrame(rows); d.to_csv('031_事件表.csv', index=False, encoding='utf-8-sig')
print(pd.crosstab(d['路線'], d['股票池']))
