# 032 候選公告擷取（Elon，2026-10-23）：重現 cand_listed.csv（關鍵字候選）與 cand_supp.csv（補撈候選）
# 輸入：mops-fetch-test/merged/MOPS每日重大訊息_公告總表_YYYY.csv.gz、listing/上市櫃期間表.csv
import pandas as pd, glob, re
R = '/home/claude/mops-fetch-test'; D = '/home/claude/p032'
d = pd.concat([pd.read_csv(f, dtype=str) for f in sorted(glob.glob(f'{R}/merged/MOPS*_20*.csv.gz'))], ignore_index=True).fillna('')
d = d.drop_duplicates(['公司代號', '發言日期', '發言時間', '主旨'])
L = pd.read_csv(f'{R}/listing/上市櫃期間表.csv', dtype=str).fillna('').set_index('公司代號')

# 第一層：主旨或說明含解盲類詞（寬篩）
subj0 = d['主旨'].str.contains(r'解盲|主要(?:療效|評估|試驗)?指標|topline|top-line|期中分析|臨床試驗.*(?:結果|報告)|試驗結果|統計(?:上)?顯著|期別.*結果|人體臨床.*結果', case=False, regex=True)
body0 = (d['主旨'] + ' ' + d['說明']).str.contains(r'解盲|主要(?:療效|評估)?指標|topline|期中分析', case=False, regex=True)
c = d[subj0 | body0].copy()
c['主旨c'] = c['主旨'].str.replace(r'\s+', '', regex=True)
S = c['主旨c']
subj = S.str.contains(r'解盲|期中分析|期間分析|topline|top-line|主要.{0,6}指標|統計.{0,2}顯著|顯著有效|療效數據|試驗.{0,12}(?:結果|數據|報告)|(?:結果|數據).{0,4}(?:達|佳|顯著|正向|成功|未)', case=False, regex=True)
noise = S.str.contains(r'申請|核准|同意|獲准|許可|收案|受試者|啟動|審查|IND|NDA|BLA|藥證|授權|簽署|專利|變更|撤回|首例|首位|入組', regex=True)
def field(t):
    m = re.search(r'含期中分析\)?結果[:：]?(.{0,400})', t, re.S); return m.group(1) if m else ''
tight = c['說明'].map(field).str.contains(r'解盲|topline|主要.{0,8}指標.{0,40}(?:達|顯著|未)|期中分析結果', case=False, regex=True)
sel = c[subj | (tight & ~noise)].copy()
def in_list(code, day):
    if code not in L.index: return False
    a, b = L.loc[code, '初次上市櫃日'], L.loc[code, '終止上市櫃日']
    return day >= a and (b == '' or day < b)
sel = sel[[in_list(a, b) for a, b in zip(sel['公司代號'], sel['發言日期'])]].sort_values(['發言日期', '發言時間']).reset_index(drop=True)
sel['cid'] = ['C%03d' % (i + 1) for i in range(len(sel))]

# 第二層補撈：上市櫃期間、說明提到臨床試驗、主旨為記者會／進度／澄清／達標類，且不在第一層者
dl = d[[in_list(a, b) for a, b in zip(d['公司代號'], d['發言日期'])]].copy()
dl['主旨c'] = dl['主旨'].str.replace(r'\s+', '', regex=True)
body = dl['說明'].str.contains(r'臨床試驗|人體試驗|臨床研究|clinical', case=False, regex=True)
subj2 = dl['主旨c'].str.contains(r'記者會|研發進度|達標|臨床.{0,20}(?:成功|成果|結果|數據|報告|完成|有效|安全)|試驗.{0,10}(?:完成|成功|達|有效)|媒體|澄清|說明會|注意交易|異常', regex=True)
key = set(zip(sel['公司代號'], sel['發言日期'], sel['發言時間']))
x = dl[body & subj2]
x = x[[k not in key for k in zip(x['公司代號'], x['發言日期'], x['發言時間'])]]
x = x[~x['主旨c'].str.contains('IFRS|國際會計準則')].sort_values(['發言日期', '發言時間']).reset_index(drop=True)
x['cid'] = ['S%03d' % (i + 1) for i in range(len(x))]
print('第一層候選（上市櫃期間）', len(sel), '｜補撈候選', len(x))
if __name__ == '__main__':
    o1 = pd.read_csv(f'{D}/cand_listed.csv', dtype=str); o2 = pd.read_csv(f'{D}/cand_supp.csv', dtype=str)
    print('與交付檔一致：', len(o1) == len(sel) and (o1['cid'].tolist() == sel['cid'].tolist()) and (o1['發言時間'].tolist() == sel['發言時間'].tolist()),
          len(o2) == len(x) and (o2['發言時間'].tolist() == x['發言時間'].tolist()))
