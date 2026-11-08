# 076 經營權之爭搶籌碼策略｜第 1 段事件盤點（不計算任何報酬）
# 輸入：mops-fetch-test 重訊總表（merged 2007-2026＋data/announcements_20261013_20261031）
#       elon-bt data-20261105r68 listing_periods.parquet、calendar.parquet
# 輸出：meetings.csv、s1_events.csv、control.csv、摘要列印
import pandas as pd, numpy as np, re, glob, sys, os
REPO = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/ext/mops-fetch-test'
W = '/home/claude/w076'
OUT = f'{W}/out'; os.makedirs(OUT, exist_ok=True)

# ---------- 交易日曆（官方交易日；2026-11-04 之後無資料） ----------
cal = pd.read_parquet(f'{W}/calendar.parquet')['date'].dt.normalize().sort_values().reset_index(drop=True)
CAL = pd.DatetimeIndex(cal)
def next_td(d, inclusive=True):
    i = CAL.searchsorted(d, side='left' if inclusive else 'right')
    return CAL[i] if i < len(CAL) else pd.NaT
def last_buy(last_transfer):
    # 最後可買進日 T：T+2 個交易日 <= 最後過戶日（T+2 普通交割）
    j = CAL.searchsorted(last_transfer, side='right') - 1   # 最後過戶日當日或之前最後一個交易日
    return CAL[j - 2] if j - 2 >= 0 else pd.NaT
def td_between(a, b):   # a 到 b 的交易日數（含兩端）
    return int(CAL.searchsorted(b, side='right') - CAL.searchsorted(a, side='left'))

# ---------- 上市櫃身分（官方逐日市場別） ----------
lp = pd.read_parquet(f'{W}/listing_periods.parquet')
lp = lp[lp['market'].isin(['上市', '上櫃'])]
LP = {k: g[['start', 'end']].values for k, g in lp.groupby('stock_id')}
def listed_on(code, d):
    a = LP.get(code)
    if a is None or pd.isna(d): return False
    d = np.datetime64(d)
    return bool(((a[:, 0] <= d) & (a[:, 1] >= d)).any())

# ---------- 重訊 ----------
fs = sorted(glob.glob(f'{REPO}/merged/MOPS每日重大訊息_公告總表_*.csv.gz')) + [f'{REPO}/data/announcements_20261013_20261031.csv.gz']
A = pd.concat([pd.read_csv(f, dtype=str) for f in fs], ignore_index=True)
A = A.drop_duplicates(subset=['公司代號', '發言日期', '發言時間', '主旨'])
A = A[(A['發言日期'] >= '20080101') & (A['發言日期'] <= '20261031')].copy()
A['主旨'] = A['主旨'].fillna(''); A['說明'] = A['說明'].fillna('')
A['公司代號'] = A['公司代號'].str.strip()
print('重訊則數', len(A), A['發言日期'].min(), A['發言日期'].max())

def roc(s):
    m = re.search(r'(\d{2,3})\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})', s or '')
    if not m: return pd.NaT
    y, mo, d = map(int, m.groups())
    try: return pd.Timestamp(y + 1911, mo, d)
    except Exception: return pd.NaT
def field(t, key):
    m = re.search(key + r'[^:：\n]*[:：]\s*([^\n]*)', t); return m.group(1) if m else ''

# ---------- 股東會主檔 ----------
g = A[A['主旨'].str.contains('股東常會|股東臨時會|股東會') & A['說明'].str.contains('停止過戶起始')].copy()
g['會期'] = g['說明'].apply(lambda t: roc(field(t, r'股東(?:常|臨時)?會召開日期')))
g['停過起'] = g['說明'].apply(lambda t: roc(field(t, '停止過戶起始日期')))
g = g.dropna(subset=['會期', '停過起'])
g = g[(g['會期'] - g['停過起']).dt.days.between(10, 75)]          # 排除解析錯誤（常會約 59 日、臨時會約 29 日）
g['類型'] = np.where((g['主旨'] + g['說明']).str.contains('臨時會'), '臨時', '常會')
txt = g['說明'].str.replace(r'選任程序|選舉辦法|選任及|董事選舉辦法|選任方式', '', regex=True)
g['選舉'] = txt.str.contains(r'全面改選|改選|補選|選任|選舉.{0,4}(董事|監察人)|解任')
g['全面改選'] = txt.str.contains('全面改選')
g['自行召集'] = (g['主旨'] + g['說明']).str.contains(r'自行召集|第一七三條|第173條|監察人.{0,6}召集|召集權人')
g['公告日'] = pd.to_datetime(g['發言日期'])
g = g.sort_values('公告日')
M = (g.groupby(['公司代號', '會期'])
       .agg(公司名稱=('公司名稱', 'last'), 類型=('類型', 'last'), 停過起=('停過起', 'last'),
            選舉=('選舉', 'max'), 全面改選=('全面改選', 'max'), 自行召集=('自行召集', 'max'),
            首次公告日=('公告日', 'first'), 最後公告日=('公告日', 'last'), 公告數=('主旨', 'size'))
       .reset_index())
M['最後過戶日'] = M['停過起'] - pd.Timedelta(days=1)
M['最後可買進日'] = M['最後過戶日'].apply(last_buy)
M['上市櫃'] = [listed_on(c, d) for c, d in zip(M['公司代號'], M['最後可買進日'])]
M.to_csv(f'{OUT}/meetings.csv', index=False, encoding='utf-8-sig')
print('股東會', len(M), '上市櫃', M['上市櫃'].sum(), '有選舉', (M['選舉'] & M['上市櫃']).sum())

# ---------- S1 重訊訊號 ----------
s = A['主旨'].str.replace(r'\s+', '', regex=True); b = A['說明']
# v2（2026-11-08，抽樣 40 則誤判約 40% 後收緊）：
#  - 經營權須與「本公司」相連，排除場館／特許「經營權」；澄清須指向本公司
#  - 公開收購限主旨同時含「公開收購」，排除上市審議委員會、投資審議委員會、可轉債收購
#  - 自行召集看主旨（排除候選人表單欄位「其他召集權人決定結果」的制式字樣）
#  - 委託書排除公司自己的股東會公告／更正
own = r'(?:本公司|公司派|經營團隊|現任董事會)'
ctl = r'(?:經營權|市場派|董監改選|改選董事|解任董事|委託書|爭奪)'
near = own + r'.{0,25}' + ctl + '|' + ctl + r'.{0,25}' + own
notop = r'取得.{0,10}經營權|經營權.{0,6}(?:契約|招標|標案|移轉予本公司)|營運權'
rule = {
 'R1經營權': s.str.contains('經營權') & ~s.str.contains('承諾事項|私募|經營權異動且營業範圍') & ~(s + b).str.contains(notop),
 'R2澄清涉經營權': s.str.contains('澄清|說明') & b.str.contains(near) & ~b.str.contains(notop),
 'R3市場派': (s + b).str.contains('市場派') & b.str.contains(near),
 'R4委託書': s.str.contains('委託書') & ~s.str.contains('召開|更正|調整|補充'),
 'R5自行召集': s.str.contains(r'自行召集|第一七三條|第173條|少數股東.{0,10}召集|監察人.{0,6}召集|召集權人.{0,10}召集|召集.{0,10}股東臨時會') & ~s.str.contains(r'董事會.{0,8}召集|董事會決議|代.{0,12}子公司|代子公司|子公司'),
 'R6被公開收購': s.str.contains('公開收購') & s.str.contains('本公司') & ~s.str.contains('注意交易|轉換公司債|可轉債|本公司擬公開收購|本公司公開收購|子公司公開收購|決議通過公開收購|決議.{0,6}公開收購|代.{0,12}子公司|代子公司'),
 'R7候選人或假處分': (s + b).str.contains(r'(?:董事|獨立董事)候選人.{0,30}(?:不予列入|爭議|訴訟|假處分|撤銷)|假處分.{0,30}本公司.{0,10}股東(?:常|臨時)?會|本公司.{0,10}股東(?:常|臨時)?會.{0,30}假處分'),
}
R = pd.DataFrame(rule)
E = A[R.any(axis=1)].copy()
E['規則'] = R[R.any(axis=1)].apply(lambda r: '|'.join(k for k, v in r.items() if v), axis=1)
E['收購類型'] = np.where(~E['規則'].str.contains('R6'), '', np.where((E['主旨']+E['說明']).str.contains(r'事先並不知情|事前並不知情|未事先|非合意|未經本公司|敵意|競爭公開收購'), '非合意', '其他（含友善／關係企業）'))
E['關係企業收購'] = E['規則'].str.contains('R6') & E['說明'].str.contains(r'母公司|子公司|關係人|關係企業|具控制力|實質控制')
E['公告時點'] = pd.to_datetime(E['發言日期'] + E['發言時間'].fillna('235959').str.zfill(6), format='%Y%m%d%H%M%S', errors='coerce')
# 進場：09:00 前公告→當日開盤；其餘（含盤中、盤後、查無時間）→次一交易日開盤
d0 = pd.to_datetime(E['發言日期'])
pre = E['發言時間'].fillna('999999').str.zfill(6) < '090000'
E['進場日'] = [next_td(d, True) if p else next_td(d, False) for d, p in zip(d0, pre)]

# 對應目標股東會：訊號日之後、停止過戶起日在 365 日內、有選舉／解任議案的最近一次股東會
Mg = M[M['選舉']].sort_values('停過起')
MG = {k: v for k, v in Mg.groupby('公司代號')}
def target(code, d):
    # 先看訊號是否落在某次有選舉股東會的「停止過戶起日～會期」之間（已來不及過戶，列不可交易）；
    # 否則取之後 365 日內最近一次有選舉的股東會
    m = MG.get(code)
    if m is None: return None
    w = m[(m['停過起'] <= d) & (m['會期'] >= d)]
    if not w.empty: return w.iloc[-1]
    m = m[(m['停過起'] > d) & (m['停過起'] <= d + pd.Timedelta(days=365))]
    return None if m.empty else m.iloc[0]
rows = []
for _, r in E.iterrows():
    t = target(r['公司代號'], pd.Timestamp(r['發言日期']))
    rows.append({'目標會期': t['會期'] if t is not None else pd.NaT,
                 '目標類型': t['類型'] if t is not None else '',
                 '最後可買進日': t['最後可買進日'] if t is not None else pd.NaT,
                 '股東會首次公告日': t['首次公告日'] if t is not None else pd.NaT})
E = pd.concat([E.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
E['上市櫃'] = [listed_on(c, d) for c, d in zip(E['公司代號'], E['進場日'])]
E['可交易'] = E['最後可買進日'].notna() & (E['進場日'] <= E['最後可買進日'])
E['距最後可買進日_交易日'] = [td_between(a, b) if (pd.notna(a) and pd.notna(b) and a <= b) else np.nan
                        for a, b in zip(E['進場日'], E['最後可買進日'])]
E['股東會已公告'] = E['股東會首次公告日'].notna() & (E['股東會首次公告日'] <= pd.to_datetime(E['發言日期']))
E.to_csv(f'{OUT}/s1_announcements.csv', index=False, encoding='utf-8-sig')

# 去重：同公司同一目標股東會只取第一則（另保留 180 日去重於無目標會者）
ev = E[E['目標會期'].notna()].sort_values('公告時點').groupby(['公司代號', '目標會期'], as_index=False).first()
ev['年'] = pd.to_datetime(ev['發言日期']).dt.year
ev.to_csv(f'{OUT}/s1_events.csv', index=False, encoding='utf-8-sig')
print('S1 公告', len(E), '有目標會', E['目標會期'].notna().sum(), '事件(去重)', len(ev))
print('事件：上市櫃', ev['上市櫃'].sum(), '上市櫃且可交易', (ev['上市櫃'] & ev['可交易']).sum())

# ---------- 對照組：有全面改選、該股東會沒有任何 S1 訊號的上市櫃公司 ----------
sig = set(zip(ev['公司代號'], ev['目標會期']))
Ctl = M[M['全面改選'] & M['上市櫃']].copy()
Ctl['有訊號'] = [(c, d) in sig for c, d in zip(Ctl['公司代號'], Ctl['會期'])]
Ctl = Ctl[~Ctl['有訊號']]
Ctl['年月'] = Ctl['最後可買進日'].dt.to_period('M').astype(str)
Ctl.to_csv(f'{OUT}/control.csv', index=False, encoding='utf-8-sig')
print('對照組股東會', len(Ctl))
