# 031 步驟1a：解析制式公告第1～10欄（舊／新事務所、會計師、第8欄原因、第9欄發起方說明）
import pandas as pd, re
a=pd.read_csv('univ.csv.gz',dtype=str).fillna('')
def fld(s,n):
    m=re.search(rf'(?:^|\n){n}\.[^:：]*?[:：](.*?)(?=\n{n+1}\.|\Z)',s,re.S)
    return re.sub(r'\s+','',m.group(1)).strip() if m else None
st=a['說明'].str.contains('舊會計師事務所名稱')
s=a[st].copy()
for n,c in [(1,'f1'),(2,'oldfirm'),(3,'old1'),(4,'old2'),(5,'newfirm'),(6,'new1'),(7,'new2'),(8,'f8'),(9,'f9'),(10,'f10')]:
    s[c]=s['說明'].map(lambda x: fld(x,n))
s.to_pickle('struct.pkl')
ns=a[~st]
t=ns['主旨']+ns['說明']
ns=ns[t.str.contains('簽證會計師|查核會計師|會計師事務所')&t.str.contains('終止委任|不再接受委任|不再繼續接受委任|終止查核|終止簽證|辭任|請辭')]
ns.to_pickle('nonstruct.pkl')
print(len(s),'structured;',len(ns),'nonstruct candidates')
print(s['f9'].isna().sum(),'f9 missing')
print(s['f9'].value_counts().head(50).to_string())
