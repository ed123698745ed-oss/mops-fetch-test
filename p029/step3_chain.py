# 029 步驟3：串鏈（同公司＋同資產類型＋同標的鍵，鏈首公告起 180 日內；補充公告引用日期可跨鍵串回）→ A／B 訊號
import pandas as pd, re, csv, sys, datetime as dt
REPO = sys.argv[1]
c = pd.read_pickle("c2.pkl")
k = c[c["排除原因"] == ""].copy()
def d8(s): return dt.date(int(s[:4]), int(s[4:6]), int(s[6:]))
def ref_dates(subj):
    out = set()
    for m in re.finditer(r"(\d{2,3})\s*[/／.年]\s*(\d{1,2})\s*[/／.月]\s*(\d{1,2})", subj):
        y = int(m.group(1)) + 1911
        try: out.add(dt.date(y, int(m.group(2)), int(m.group(3))).strftime("%Y%m%d"))
        except ValueError: pass
    return out
chains = []          # 每鏈：dict(公司, 類型, 鍵, 首日, 成員idx)
by_co = {}
cid = {}
for i, r in k.iterrows():
    co = r["公司代號"]; d = r["發言日期"]; lst = by_co.setdefault(co, [])
    target = None
    refs = ref_dates(r["主旨"])
    if refs:   # 補充／更新引用前次公告日期 → 串回該日所屬的鏈（不受 180 日限制）
        for ch in lst:
            if any(chains[j]["日"] in refs for j in []): pass
        for ch in reversed(lst):
            if refs & {k.at[j, "發言日期"] for j in chains[ch]["成員"]}: target = ch; break
    if target is None:
        for ch in reversed(lst):
            C = chains[ch]
            if C["類型"] == r["資產類型"] and C["鍵"] == r["標的鍵"] and (d8(d) - d8(C["首日"])).days <= 180: target = ch; break
    if target is None:
        chains.append({"公司": co, "類型": r["資產類型"], "鍵": r["標的鍵"], "首日": d, "成員": []}); target = len(chains) - 1; lst.append(target)
    chains[target]["成員"].append(i); cid[i] = target
k["鏈ID"] = pd.Series(cid)
k["鏈內序"] = k.groupby("鏈ID").cumcount() + 1
# 上市櫃期間
PER = {r["公司代號"]: r for r in csv.DictReader(open(f"{REPO}/listing/上市櫃期間表.csv", encoding="utf-8-sig"))}
import json
import os
_calf = os.environ.get("P029_CAL")                 # R03：2007～2009 驗證用 FinMind 加權指數（csv.gz）
if _calf:
    import gzip as _gz
    cal = sorted(r["date"].replace("-", "") for r in csv.DictReader(_gz.open(_calf, "rt", encoding="utf-8")) if float(r["close"] or 0) > 0)
else:
    cal = sorted(x["date"].replace("-", "") for x in json.load(open(f"{REPO}/prices/raw/TaiwanStockPrice_TAIEX.json"))["data"] if x["close"] > 0)
import bisect
def next_td(d):
    i = bisect.bisect_right(cal, d); return cal[i] if i < len(cal) else ""
def listed(co, e):
    p = PER.get(co)
    if not p or not e: return False
    return p["初次上市櫃日"] <= e and (not p["終止上市櫃日"] or e < p["終止上市櫃日"])
ev = []
for ch_id, C in enumerate(chains):
    mem = k.loc[C["成員"]]
    first = mem.iloc[0]
    base = {"事件ID": f"D{ch_id:05d}", "公司代號": C["公司"], "公司名稱": first["公司名稱"], "資產類型": C["類型"], "股權細分": first["股權細分"],
            "標的鍵": C["鍵"], "鏈公告數": len(mem), "鏈內公告": "｜".join(f'{x["發言日期"]}-{x["發言時間"]}' for _, x in mem.iterrows()),
            "鏈首主旨": first["主旨"][:120], "鏈首為後續公告": bool(first["後續公告"]), "集團內部標記": first["集團內部"], "歸屬層級": first["歸屬層級"]}
    for route, sel in (("A", mem.iloc[[0]]), ("B", mem[mem["量化損益"]].head(1))):
        if len(sel) == 0: continue
        x = sel.iloc[0]; S = x["發言日期"]; E = next_td(S)
        row = dict(base, 路線=route, 訊號公告日S=S, 公告時間=x["發言時間"], 進場日E=E, 款項=x["款項h16"], 主旨=x["主旨"][:150],
                   原始公告ID=f'{x["公司代號"]}_{x["發言日期"]}_{x["發言時間"]}', 市場別_現值=x["市場別"],
                   損益狀態=x["損益_狀態"], 損益方向=x["損益_方向"], 幣別=x["損益_幣別"], 損益金額_原幣=x["損益_金額"], 區間下限_原幣=x["損益_下限"], 區間上限_原幣=x["損益_上限"],
                   公司揭露約當台幣=x["損益_公司揭露約當台幣"], 預估實際=x["損益_預估實際"], 稅別=x["損益_稅別"], 解析疑義=x["損益_疑義"], FVOCI_不進損益=bool(x["FVOCI_不進損益"]),
                   訊號公告歸屬層級=x["歸屬層級"], 損益欄位原文=(x["損益欄位"] or "")[:200] if isinstance(x["損益欄位"], str) else "", 交易相對人=x["交易相對人"][:150],
                   A與B同公告=(route == "B" and x.name == mem.index[0]))
        # 主樣本資格
        why = ""
        if first["後續公告"]: why = "鏈首為補充／更新等後續公告，無法確認首次（策略卡第7節）"
        elif not E: why = "資料終點前無公告後交易日"
        elif not listed(C["公司"], E): why = "進場日不在上市櫃期間（興櫃／未上市／已下市）"
        row["主樣本排除原因"] = why
        ev.append(row)
E = pd.DataFrame(ev)
E.to_csv("029_事件表_初版.csv", index=False, encoding="utf-8-sig")
k.to_pickle("c3.pkl")
m = E[E["主樣本排除原因"] == ""]
print("鏈數", len(chains)); print(E.groupby("路線")["主樣本排除原因"].value_counts().to_string())
print("主樣本 A", (m["路線"] == "A").sum(), " B", (m["路線"] == "B").sum(), " B與A同公告", m["A與B同公告"].sum(), " B晚於A", ((m["路線"] == "B") & ~m["A與B同公告"]).sum())
print(m[m["路線"] == "A"].groupby(m["訊號公告日S"].str[:4]).size().to_dict())
print(m[m["路線"] == "A"]["資產類型"].value_counts().to_dict(), m[m["路線"] == "A"]["股權細分"].value_counts().to_dict())
print("A 鏈首歸屬", m[m["路線"] == "A"]["歸屬層級"].value_counts().to_dict())
print(m[m["路線"] == "B"]["損益方向"].value_counts().to_dict())
