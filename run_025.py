# 策略025 判讀執行器：候選 CSV → 規則 R1 → 覆寫表 → 事件表(含事件ID/補充鏈) → 統計
# 用法：python3 run_025.py [out/cand_*.csv 所在目錄=out] ；每日上線追蹤時，對當日新抓公告跑同一流程，
#       判讀=符合* 者即為觸發名單，判讀=待人工者需人工判讀後追加到 overrides_025.csv。
import csv, glob, re, sys, collections
from datetime import datetime
from rules_025 import classify, norm, RULE_VERSION
src = sys.argv[1] if len(sys.argv) > 1 else "out"
ov = {}
for r in csv.DictReader(open("overrides_025.csv", encoding="utf-8-sig")):
    ov[(r["公司代號"], r["發言日期"], r["發言時間"])] = r
# 事件表 R2（2026-10-19）：候選改由重訊總表「全部市場別」直接篩選，股票池改用上市櫃期間表判斷，
# 不再看「市場別」欄位（該欄是公司現況，會誤收興櫃期間、漏掉已下市公司）。判讀規則仍為 R1。
EVENT_TABLE_VERSION = "R2"
import gzip
from rules_025 import is_candidate
PER = {r["公司代號"]: r for r in csv.DictReader(open("listing/上市櫃期間表.csv", encoding="utf-8-sig"))}
def pool_status(code, d):
    p = PER.get(code)
    if not p: return "未上市櫃(興櫃/公開發行)"
    if d < p["初次上市櫃日"]: return "未上市櫃(興櫃/公開發行)"
    if p["終止上市櫃日"] and d >= p["終止上市櫃日"]: return "已下市後"
    return "上市櫃期間"
rows = []; seen = set()
for f in sorted(glob.glob("merged/MOPS每日重大訊息_公告總表_20*.csv.gz")):
    for r in csv.DictReader(gzip.open(f, "rt", encoding="utf-8-sig")):
        k = (r["公司代號"], r["發言日期"], r["發言時間"], r["主旨"])
        if k in seen or not is_candidate(r["主旨"], r["說明"]): continue
        seen.add(k)
        r["上市櫃狀態"] = pool_status(r["公司代號"], r["發言日期"])
        c = classify(r["主旨"], r["說明"]); r.update(c); r["判讀來源"] = "規則" + RULE_VERSION
        o = ov.get((r["公司代號"], r["發言日期"], r["發言時間"]))
        if o:
            r["判讀"], r["類別"] = o["覆寫判讀"], o["覆寫類別"]
            if o["覆寫合約類型"]: r["合約類型"] = o["覆寫合約類型"]
            r["規則備註"] = o["理由"]; r["判讀來源"] = "人工覆寫"
        rows.append(r)
rows.sort(key=lambda r: (r["公司代號"], r["發言日期"], int(r["發言時間"] or 0)))   # 時間未補零，須轉整數排序
# 事件ID：同公司，補充/更正/變更字樣，或 60 日內主旨相同 → 沿用首次公告ID
SUP = re.compile(r"補充|更正|再次|變更")
first = {}; last_seen = {}; last_any = {}
def d(s): return datetime.strptime(s, "%Y%m%d")
for r in rows:
    if not r["判讀"].startswith("符合") or r["上市櫃狀態"] != "上市櫃期間": r["事件ID"] = ""; r["是否首次"] = ""; continue
    key = r["公司代號"]; ns = norm(r["主旨"]); ns2 = SUP.sub("", ns)
    eid = f'{r["公司代號"]}_{r["發言日期"]}_{r["發言時間"]}'
    prev = last_seen.get((key, ns2))
    if not (prev and (d(r["發言日期"]) - d(prev[1])).days <= 60):
        near = last_any.get(key)   # 同公司 5 日內另一則終止公告（母子公司同時公告、同案拆多則）視為同一事件
        prev = near if (near and (d(r["發言日期"]) - d(near[1])).days <= 5) else None
    if prev:
        eid = prev[0]; r["規則備註"] = (r["規則備註"] + "；" if r["規則備註"] else "") + "後續補充或同案，沿用首次事件ID"; r["是否首次"] = "否"
    else:
        r["是否首次"] = "是"
    last_seen[(key, ns2)] = (eid, r["發言日期"]); r["事件ID"] = eid
    if r["是否首次"] == "是": last_any[key] = (eid, r["發言日期"])
cols = ["事件ID","是否首次","公司代號","公司名稱","市場別","上市櫃狀態","發言日期","發言時間","主旨","判讀","類別","合約類型","終止時點","公司角色","規則備註","判讀來源"]
hdr = rows[0].keys()
w = csv.writer(open(f"{src}/025_全候選判讀.csv", "w", encoding="utf-8-sig", newline=""))
hdr = list(dict.fromkeys(list(hdr) + ["事件ID","是否首次"]))
w.writerow(["規則版本","事件表版本"] + hdr); [w.writerow([RULE_VERSION, EVENT_TABLE_VERSION] + [r.get(c, "") for c in hdr]) for r in rows]
ev = [r for r in rows if r["判讀"].startswith("符合") and r.get("是否首次") == "是"]
w = csv.writer(open(f"{src}/025_事件表.csv", "w", encoding="utf-8-sig", newline=""))
w.writerow(["規則版本","事件表版本"] + cols)
[w.writerow([RULE_VERSION, EVENT_TABLE_VERSION] + [r.get(c, "") for c in cols]) for r in ev]
print("候選", len(rows), "｜事件(首次)", len(ev), "｜補充", sum(1 for r in rows if r.get("是否首次") == "否"))
print("判讀", collections.Counter(r["判讀"] for r in rows))
print("上市櫃狀態×判讀", collections.Counter((r["上市櫃狀態"], r["判讀"][:2]) for r in rows))
print("事件 類別", collections.Counter(r["類別"] for r in ev))
print("事件 終止時點", collections.Counter(r["終止時點"] for r in ev))
print("事件 年", sorted(collections.Counter(r["發言日期"][:4] for r in ev).items()))
