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
rows = []
for f in sorted(glob.glob(f"{src}/cand_*.csv")):
    for r in csv.DictReader(open(f, encoding="utf-8-sig")):
        c = classify(r["主旨"], r["說明"]); r.update(c); r["判讀來源"] = "規則" + RULE_VERSION
        o = ov.get((r["公司代號"], r["發言日期"], r["發言時間"]))
        if o:
            r["判讀"], r["類別"] = o["覆寫判讀"], o["覆寫類別"]
            if o["覆寫合約類型"]: r["合約類型"] = o["覆寫合約類型"]
            r["規則備註"] = o["理由"]; r["判讀來源"] = "人工覆寫"
        rows.append(r)
rows.sort(key=lambda r: (r["公司代號"], r["發言日期"], r["發言時間"]))
# 事件ID：同公司，補充/更正/變更字樣，或 60 日內主旨相同 → 沿用首次公告ID
SUP = re.compile(r"補充|更正|再次|變更")
first = {}; last_seen = {}
def d(s): return datetime.strptime(s, "%Y%m%d")
for r in rows:
    if not r["判讀"].startswith("符合"): r["事件ID"] = ""; continue
    key = r["公司代號"]; ns = norm(r["主旨"]); ns2 = SUP.sub("", ns)
    eid = f'{r["公司代號"]}_{r["發言日期"]}_{r["發言時間"]}'
    prev = last_seen.get((key, ns2))
    if prev and (d(r["發言日期"]) - d(prev[1])).days <= 60:
        eid = prev[0]; r["規則備註"] = (r["規則備註"] + "；" if r["規則備註"] else "") + "後續補充，沿用首次事件ID"; r["是否首次"] = "否"
    else:
        r["是否首次"] = "是"
    last_seen[(key, ns2)] = (eid, r["發言日期"]); r["事件ID"] = eid
cols = ["事件ID","是否首次","公司代號","公司名稱","市場別","發言日期","發言時間","主旨","判讀","類別","合約類型","終止時點","公司角色","規則備註","判讀來源"]
hdr = rows[0].keys()
w = csv.writer(open(f"{src}/025_全候選判讀.csv", "w", encoding="utf-8-sig", newline=""))
w.writerow(["規則版本"] + [c for c in hdr]); [w.writerow([RULE_VERSION] + list(r.values())) for r in rows]
ev = [r for r in rows if r["判讀"].startswith("符合") and r.get("是否首次") == "是"]
w = csv.writer(open(f"{src}/025_事件表.csv", "w", encoding="utf-8-sig", newline=""))
w.writerow(["規則版本"] + [c for c in cols if c in hdr or c in ("事件ID","是否首次")])
[w.writerow([RULE_VERSION] + [r.get(c, "") for c in cols if c in hdr or c in ("事件ID","是否首次")]) for r in ev]
print("候選", len(rows), "｜事件(首次)", len(ev), "｜補充", sum(1 for r in rows if r.get("是否首次") == "否"))
print("判讀", collections.Counter(r["判讀"] for r in rows))
print("事件 類別", collections.Counter(r["類別"] for r in ev))
print("事件 終止時點", collections.Counter(r["終止時點"] for r in ev))
print("事件 年", sorted(collections.Counter(r["發言日期"][:4] for r in ev).items()))
