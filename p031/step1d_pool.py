# 031 步驟1d：進場日 E（S 之後第一個市場交易日）、公告時段、股票池（依上市櫃期間表判斷公告後進場日是否在上市櫃期間）
import json, pandas as pd, bisect, sys
REPO = sys.argv[1] if len(sys.argv) > 1 else '/root/mops-fetch-test'
cal = sorted(x['date'] for x in json.load(open('taiex.json'))['data'] if x['close'] > 0)   # FinMind TAIEX 日線＝市場日曆
per = pd.read_csv(f'{REPO}/listing/上市櫃期間表.csv', dtype=str, encoding='utf-8-sig').fillna('').set_index('公司代號')
def E(d):
    iso = f'{d[:4]}-{d[4:6]}-{d[6:]}'; i = bisect.bisect_right(cal, iso); return cal[i] if i < len(cal) else ''
def sess(t):
    t = int(t); return '盤前' if t < 90000 else ('盤中' if t < 133000 else '盤後')
for f, tag in [('A_events.csv', 'A'), ('C_events.csv', 'C')]:
    d = pd.read_csv(f, dtype=str).fillna('')
    d['E'] = d['S日期'].map(E); d['時段'] = d['S時間'].map(sess)
    def inper(r):
        if r['公司代號'] not in per.index: return '期間表無此代號'
        p = per.loc[r['公司代號']]; e = r['E'].replace('-', '')
        if not e: return '資料終點後'
        if p['初次上市櫃日'] and e < p['初次上市櫃日']: return '未上市櫃(興櫃/公開發行)'
        if p['終止上市櫃日'] and e > p['終止上市櫃日']: return '已終止上市櫃'
        return '上市櫃期間'
    d['股票池'] = d.apply(inper, axis=1)
    if tag == 'A':
        d['BE'] = d['B日期'].map(lambda x: E(x) if x else ''); d['B時段'] = d['B時間'].map(lambda x: sess(x) if x else '')
    d['後來下市'] = d['公司代號'].map(lambda c: per.loc[c, '終止上市櫃日'] if c in per.index else '')
    d.to_csv(f.replace('.csv', '_pool.csv'), index=False, encoding='utf-8-sig')
    print(tag, d['股票池'].value_counts().to_dict())
