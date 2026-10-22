# 031 步驟1b：依公司填答（第9欄發起方、第8欄原因）以固定規則分類：主動退出／公司更換／輪調／其他／不明；排除子公司單獨變更；補入3則非制式首次確認公告
import pandas as pd, re
s=pd.read_pickle('struct.pkl').fillna('')
def nf(x): return re.sub(r'[\s()（）「」、,，.。:：\'"]|聯合|會計師事務所|會計事務所|事務所|會計師務所|会計師','',x or '')[:6]
ROUT=r'退休|過世|逝世|停止辦理|合併|加入.{0,15}事務所|組織變更|核准準則|人數不符|內部輪調|輪調機制|輪調法規|年事已高|退夥|新設事務所|更名'
ROT=r'輪調|輪替|輪換|內部調整|內部職務|職務調|業務調整|內部工作|工作調整|內部人事|內部人員|調整簽證會計師|內部輪|自我輪調'
AUD=r'(會計師|事務所).{0,30}(終止|中止|不再|辭)|接受.{0,4}委任|終止接受|來函|函知|發函|發文|主動通知'
COM=r'(本公司|由公司|^公司|係公司|公司主動|公司決定|董事會決議)(主動)?.{0,6}(終止|不再繼續委任|不再委任|更換|決定)|^由?本?公司|^(主動)?終止委任|^不再(繼續)?委任|採購法|委任屆滿|合約屆滿'
BOTH=r'協議|合意|合議|協商|雙方'
def cls(r):
    sub = bool(re.search(r'代.{0,30}公司.{0,8}公告|代子公司|代.{0,10}子公司|子公司.{0,20}(更換|變更)', r['主旨']))
    o,n=nf(r['oldfirm']),nf(r['newfirm'])
    same = o!='' and o==n
    f9,f8=r['f9'],r['f8']
    aud = bool(re.search(AUD,f9)) or (bool(re.search(r'主動終止',f9)) and bool(re.search(AUD,f8)) and not re.search(r'公司',f9))
    com = bool(re.search(COM,f9)) and not re.search(r'接受|來函|函知|發函|接獲',f9)
    if re.search(BOTH,f9): return sub,same,'其他'
    if same:
        if com and not re.search(ROT,f9+f8): return sub,same,'公司更換'
        return sub,same,'輪調'
    if re.search(ROUT,f9+f8): return sub,same,'其他'
    if aud and com: return sub,same,'不明'
    if aud: return sub,same,'主動退出'
    if com: return sub,same,'公司更換'
    if re.search(ROT,f9+f8): return sub,same,'其他'
    return sub,same,'不明'
r=s.apply(lambda x: pd.Series(cls(x),index=['子公司','同所','分類']),axis=1)
s=pd.concat([s,r],axis=1)
# 加入非結構化首次確認
ns=pd.read_pickle('nonstruct.pkl')
add=[]
for c,dt in [('9967','20120817'),('9961','20160719'),('2724','20170805')]:
    x=ns[(ns['公司代號']==c)&(ns['發言日期']==dt)].iloc[0].copy()
    x['子公司']=False; x['同所']=False; x['分類']='主動退出'; x['oldfirm']={'9967':'安侯建業','9961':'勤業眾信','2724':'德昌'}[c]; x['newfirm']=''; x['f9']='(非制式公告)'+x['主旨']; x['f8']=''
    add.append(x)
s=pd.concat([s,pd.DataFrame(add)],ignore_index=True)
s['ts']=s['發言日期']+s['發言時間'].str.zfill(6)
s=s.sort_values(['公司代號','ts']).reset_index(drop=True)
s.to_pickle('cls2.pkl')
print(pd.crosstab(s['分類'],s['子公司']))
