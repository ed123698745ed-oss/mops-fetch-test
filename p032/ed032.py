# 032 Ed 2026-10-23 決定與 Elon 覆核的事件表修改（已於當日以互動方式執行一次，此檔為紀錄；勿重跑 merge032.py 覆蓋）
import pandas as pd
D = '/home/claude/p032'
E = pd.read_csv(f'{D}/event_review_v1.csv', dtype=str).fillna('')
# (1) 興櫃期間事件：亞獅康 S157 E日2017-05-22 早於掛牌首日 2017-06-01 → 排除；同鏈 S158 一併排除
E.loc[E.cid == 'S157', ['事件判定', 'Elon覆核']] = ['排除', 'E日2017-05-22早於掛牌首日2017-06-01（興櫃期間）；同鏈S158一併排除']
E.loc[E.cid == 'S158', '事件判定'] = '排除'
# (2) Ed：一期試驗主要指標為安全性、公告稱安全性良好 → 達標（merge032 規則外另三筆人工確認）
for c in ['C051', 'C101', 'S358']:
    E.loc[E.cid == c, ['結果分類', '旗_安全性描述認定']] = ['達標', '安全性描述認定']
# (3) Ed：醫材試驗排除
for c in ['S327', 'S495', 'C195']:
    E.loc[E.cid == c, ['事件判定', 'Elon覆核']] = ['排除', 'Ed 2026-10-23 同意排除醫材試驗']
E.to_csv(f'{D}/event_review_v1.csv', index=False, encoding='utf-8-sig')
