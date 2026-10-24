# 029 V01／R03 原始數據明細打包（在 R03 工作目錄執行；pre2010 子目錄為 2007～2009 獨立驗證）
import pandas as pd, pickle, csv, os, shutil, zipfile, sys
R = "V01_R03"; P = "pkg"; os.makedirs(P, exist_ok=True)
pd.read_csv("029_事件表_初版.csv", dtype=str, keep_default_na=False).to_csv(f"{P}/029_事件表_{R}.csv", index=False, encoding="utf-8-sig")
c = pd.read_pickle("c2.pkl")
cols = ['公司代號','公司名稱','市場別','發言日期','發言時間','款項h16','主旨','標的','資產類型','股權細分','排除原因','集團內部','交易相對人','歸屬層級','後續公告','標的鍵','損益欄位'] + [x for x in c.columns if x.startswith('損益_')] + ['FVOCI_不進損益']
c[cols].to_csv(f"{P}/029_候選公告分類_{R}.csv", index=False, encoding="utf-8-sig")
def trades(T, fn):
    w = csv.writer(open(fn, "w", encoding="utf-8-sig", newline=""))
    w.writerow(['交易編號','事件ID','路線','公司代號','公司名稱','訊號公告日S','公告時間','進場日E','樣本側','損益分組','利益占市值','利益占市值分組','市值與換算說明','稅別組','資產類型','股權細分','持有H','進場價(E開盤)','進場日一字鎖板','消息區間(公告前收盤→E開盤)',
                '理論_預定出場日','理論_實際出場日','理論_出場收盤','理論_持股數(公司行動後)','理論_每股累計現金(股利／減資退還)','理論_公司行動明細','理論_報酬(做多)','理論_持有日數','理論_大盤同期','理論_狀態',
                '可成交做多_出場日','可成交做多_報酬','可成交做多_持有日數','可成交做多_狀態','可成交放空_出場日','可成交放空_報酬','可成交放空_持有日數','可成交放空_狀態','聚合單位標籤(進場日)','進場失敗原因'])
    k = 0
    for t in T:
        r = t['r']
        base = [r['事件ID'], r['路線'], r['公司代號'], r['公司名稱'], r['訊號公告日S'], r['公告時間'], t['E'], t['side'], t['損益分組'], '' if t['利益占市值'] is None else t['利益占市值'], t['市值分組'], t['市值說明'], t['稅別組'], r['資產類型'], r['股權細分']]
        if 'entry_fail' in t:
            k += 1; w.writerow([f'X{k:06d}'] + base + [''] * 4 + [''] * 10 + [''] * 8 + [t['E'], t['entry_fail']]); continue
        for H in [1, 2, 3, 5, 10, 20, 40]:
            h = t['H'][H]; k += 1; L = h.get('long', {}); S = h.get('short', {})
            w.writerow([f'X{k:06d}'] + base + [H, t['open'], t.get('entry_lock', ''), '' if t.get('gap') is None else t['gap'],
                h.get('sched', ''), h.get('exit', ''), h.get('close', ''), h.get('shares', ''), h.get('cash', ''), h.get('ca_notes', ''), h.get('ret', ''), h.get('hold', ''), '' if h.get('mk') is None else h.get('mk'), h['status'],
                L.get('exit', ''), '' if L.get('ret') is None else L['ret'], L.get('hold', ''), L.get('status', ''), S.get('exit', ''), '' if S.get('ret') is None else S['ret'], S.get('hold', ''), S.get('status', ''), t['E'], ''])
    return k
print("逐筆列", trades(pickle.load(open("T029.pkl", "rb")), f"{P}/029_原始數據明細_逐筆交易_{R}.csv"))
for f in [f"029_回測結果_參數全表_{R}.csv", "029_表D_B距A交易日數分布.csv", f"029_ETest1_公告時段_全表_{R}.csv", f"029_ETest1_明細_{R}.csv", f"029_ETest2_開盤漲停濾網_全表_{R}.csv", f"029_ETest2_明細_{R}.csv"]:
    shutil.copy(f, P)
for f in sys.argv[1:]: shutil.copy(f, P)
