# 031 步驟0：從 MOPS 每日重大訊息公告總表（2010～2026）撈出會計師異動相關公告
# 範圍＝款項h16=7（變更簽證會計師）或說明含制式欄位「舊會計師事務所名稱」，另收主旨／說明提及會計師終止委任等文字者供非制式公告核對
import pandas as pd, glob, sys
REPO = sys.argv[1] if len(sys.argv) > 1 else '/root/mops-fetch-test'
out = []
for f in sorted(glob.glob(f'{REPO}/merged/MOPS每日重大訊息_公告總表_20*.csv.gz')):
    d = pd.read_csv(f, dtype=str).fillna('')
    t = d['主旨'] + '\n' + d['說明']
    m = (d['款項h16'] == '7') | d['說明'].str.contains('舊會計師事務所名稱') | (t.str.contains('會計師') & t.str.contains('終止委任|不再接受委任|不再繼續接受委任|辭任|請辭|終止查核|終止簽證'))
    out.append(d[m])
a = pd.concat(out).drop_duplicates(subset=['公司代號', '發言日期', '發言時間', '主旨'])
a.to_csv('univ.csv.gz', index=False); print('universe', len(a))
