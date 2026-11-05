# 產生報告用表格（十項＋聚合 p＋回撤三項），顯示精度；全精度見參數全表
import pandas as pd, math, json
R=pd.read_csv('/home/claude/w058/out_fp/stats_fp.csv'); D=pd.read_csv('/home/claude/w058/out_fp/dd_fp.csv')
R['combo']=R['combo／sample'].str.split('｜').str[0]; R['sample']=R['combo／sample'].str.split('｜').str[1]
D['combo_']=D['combo'].str.split('／').str[0]; D['sample']=D['combo'].str.split('／').str[1]
X=R.merge(D[['combo_','sample','最大回撤','最差三次回撤平均','最長回撤期筆數','最長回撤期日曆日','最長回撤期未回復','最長回撤期聚合單位數','需註記','採計回撤段數']],left_on=['combo','sample'],right_on=['combo_','sample'],how='left')
X.drop(columns=['combo_']).to_csv('/home/claude/w058/out_fp/參數全表_V02_R01.csv',index=False,encoding='utf-8-sig')
pct=lambda v: 'N/A' if pd.isna(v) else f'{v*100:.2f}%'
f4=lambda v: 'N/A' if pd.isna(v) else f'{v:.4g}'
def dd(r):
    if pd.isna(r['最長回撤期筆數']): return 'N/A（樣本數<2）'
    if r['最長回撤期筆數']==0: return '無回撤'
    s=f"{int(r['最長回撤期筆數'])}筆（{int(r['最長回撤期日曆日']):,}天"+('，未回復' if r['最長回撤期未回復'] in (True,'True') else '')+'）'
    if r['需註記'] in (True,'True'): s+=f"〔{int(r['最長回撤期聚合單位數'])} 個批次〕"
    return s
def table(combos,samples=('樣本內','樣本外','最新年度'),names=None,agg=True):
    hdr=['組合','期間','①樣本數','②平均報酬','③平均持有交易日','④單利年化','⑤勝率','⑥賠率R','⑦凱利','⑧標準差','⑨t值','⑩雙尾p']+(['聚合p（批次數）'] if agg else [])+['⑪最大回撤','⑫最差三次回撤平均','⑬最長回撤期']
    rows=['|'+'|'.join(hdr)+'|','|'+'|'.join(['---']*len(hdr))+'|']
    for c in combos:
        for s in samples:
            r=X[(X.combo==c)&(X['sample']==s)]
            if not len(r): continue
            r=r.iloc[0]
            na=lambda v,why: f4(v) if not pd.isna(v) else f'N/A（{why}）'
            R_=na(r['賠率R'],'無虧損筆' if r['勝率']==1 else '無獲利筆'); K_=na(r['凱利'],'R 為 N/A')
            ag=[(f"{r['聚合p']:.4g}（{int(r['聚合單位數'])}）" if not pd.isna(r.get('聚合p',float('nan'))) else '不適用（每批一筆）')] if agg else []
            mdd=pct(r['最大回撤']) if not pd.isna(r['最大回撤']) else 'N/A（樣本數<2）'
            w3=pct(r['最差三次回撤平均']) if not pd.isna(r['最差三次回撤平均']) else 'N/A（樣本數<2）'
            if not pd.isna(r.get('採計回撤段數',float('nan'))) and 0<r['採計回撤段數']<3: w3+=f"（僅 {int(r['採計回撤段數'])} 段）"
            cells=[(names or {}).get(c,c),s,str(int(r['樣本數'])),pct(r['平均報酬']),f"{r['平均持有交易日數']:.2f}",pct(r['單利年化']),pct(r['勝率']),R_,K_,pct(r['標準差']),f4(r['t值']),f4(r['雙尾p'])]+ag+[mdd,w3,dd(r)]
            rows.append('|'+'|'.join(cells)+'|')
    return '\n'.join(rows)
N={'TR-M':'TR-M 主組合','TR-Meq':'TR-Meq 已成交子鏈等權（描述）','TR-P':'TR-P 子鏈籃子層','TR-L':'TR-L 多方腿（累庫上游）','TR-S':'TR-S 空方腿（−減速下游報酬）',
   'TR-M留現金':'TR-M 現增敏感度：留現金','TR-M全損':'TR-M 現增敏感度：全損',
   'TO-M':'TO-M 主組合','TO-P':'TO-P 子鏈籃子層','TO-L':'TO-L 多方腿（減速下游）','TO-S':'TO-S 空方腿（−累庫上游報酬）',
   'C-M':'C-M 主組合','C-P':'C-P 子鏈籃子層','C-L':'C-L 多方腿（減速下游）','C-S':'C-S 空方腿（−累庫上游報酬）'}
T={}
T['TRmain']=table(['TR-M'],names=N,agg=False)
T['TRall']=table(['TR-Meq','TR-P','TR-L','TR-S'],names=N)
T['TRseo']=table(['TR-M','TR-M留現金','TR-M全損'],names=N,agg=False)
T['TRsub']=table([f'TR-T{x}' for x in ['1a','1b','2a','2b','2c','3','6','7','8','9']],agg=False)
T['TO']=table(['TO-M','TO-P','TO-L','TO-S'],names=N)
T['TOsub']=table([f'TO-T{x}' for x in ['1a','1b','2a','2b','2c','3','6','7','8','9']],agg=False)
T['C']=table(['C-M','C-P','C-L','C-S'],names=N)
T['Csub']=table([f'C-{x}' for x in ['1a','1b','2a','2b','2c','2d','6','7a','8','9']],agg=False)
json.dump(T,open('/home/claude/w058/out_fp/tables.json','w'),ensure_ascii=False)
print(T['TRmain']); print(T['TRseo']); print(T['TRall'][:1500])
