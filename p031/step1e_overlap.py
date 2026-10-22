# 031 步驟1e：同期其他事件標記（看報酬前固定）：同公司於 S 前後 30 個日曆日內的重大訊息，主旨含下列關鍵字者標記類別；只標記、不排除
import pandas as pd, glob, sys, re, datetime as dt
REPO = sys.argv[1] if len(sys.argv) > 1 else '/root/mops-fetch-test'
KW = {'檢調': r'檢調|搜索|約談|調查局|檢察', '財報延遲': r'未於規定期限|延後.{0,6}申報|展延.{0,10}財務報告|未能如期',
      '停牌／交易方法': r'停止買賣|全額交割|變更交易方法|分盤交易|處置', '重整／退票': r'重整|破產|跳票|退票|存款不足',
      '非無保留意見': r'非無保留|無法表示意見|保留意見|否定意見|繼續經營.{0,10}重大不確定'}
ev = []
for f, tag in [('A_events_pool.csv', 'A'), ('C_events_pool.csv', 'C')]:
    d = pd.read_csv(f, dtype=str).fillna(''); d = d[d['股票池'] == '上市櫃期間']
    for _, r in d.iterrows():
        ev.append((r['事件ID'], r['公司代號'], r['S日期']))
        if tag == 'A' and r['B日期']: ev.append((r['事件ID'].replace('A-', 'B-', 1), r['公司代號'], r['B日期']))
codes = {c for _, c, _ in ev}
rows = []
for f in sorted(glob.glob(f'{REPO}/merged/MOPS每日重大訊息_公告總表_20*.csv.gz')):
    d = pd.read_csv(f, dtype=str, usecols=['公司代號', '發言日期', '主旨']).fillna('')
    rows.append(d[d['公司代號'].isin(codes)])
m = pd.concat(rows); m['dd'] = pd.to_datetime(m['發言日期'], format='%Y%m%d', errors='coerce')
g = dict(tuple(m.groupby('公司代號')))
out = []
for eid, c, s in ev:
    S = dt.datetime.strptime(s, '%Y%m%d'); x = g.get(c)
    tags = set()
    if x is not None:
        w = x[(x['dd'] >= S - dt.timedelta(days=30)) & (x['dd'] <= S + dt.timedelta(days=30))]
        for t in w['主旨']:
            if '會計師' in t and ('變更' in t or '更換' in t): continue
            for k, p in KW.items():
                if re.search(p, t): tags.add(k)
    out.append({'事件ID': eid, '同期事件': '、'.join(sorted(tags))})
pd.DataFrame(out).to_csv('overlap.csv', index=False, encoding='utf-8-sig'); print(len(out))
