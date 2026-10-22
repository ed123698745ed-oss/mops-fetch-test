# 031 統計：表A（主動退出）、表B（同案接任，B 晚於 A）、表C（A→B 間隔）、表D（共同案件配對）、表E（比較組）＋敏感度、Holm
# 十項統計、半凱利、聚合 p 一律呼叫共用統計函式 bt_stats 1.0
import pickle, csv, sys, collections
from statistics import median
import numpy as np
from scipy import stats as sst
sys.path.insert(0, sys.argv[1]); from bt_stats import summarize
T = pickle.load(open("T031.pkl", "rb"))
HS = [1, 2, 3, 5, 10, 20, 40]
OUT = []
def ok(t): return "excl" not in t and "entry_fail" not in t
def pick(t, H, mode, side):
    """mode: main（理論價格、已結案）／trade（可成交）／sens（含未結案以最後有效收盤結算）；回傳 (報酬, 持有日) 或 None"""
    h = t["H"].get(H)
    if not h: return None
    if mode == "main":
        if "ret" not in h: return None
        x, hd = h["ret"], h["hold"]
        return (x if side == "做多" else -x, hd)
    if mode == "trade":
        if "ret" not in h: return None
        if side == "做多" and t.get("entry_lock") == "漲停": return None
        if side == "放空" and t.get("entry_lock") == "跌停": return None
        s = h.get("long" if side == "做多" else "short")
        if not s or s.get("ret") is None: return None
        return (s["ret"], s["hold"])
    if mode == "sens":
        s = h.get("sens")
        if not s: return None
        return (s["ret"] if side == "做多" else -s["ret"], s["hold"])
def row(name, ts, H, side, mode="main", cl="E"):
    xs, hd, cs = [], [], []
    for t in ts:
        v = pick(t, H, mode, side)
        if v is None: continue
        xs.append(v[0]); hd.append(v[1]); cs.append(t["E"] if cl == "E" else t["r"]["公司代號"])
    rec = {"表": name, "口徑": {"main": "主表（理論價格、已結案）", "trade": "可成交", "sens": "敏感度：未結案以最後有效收盤結算"}[mode], "方向": side, "H": H, "完整出場樣本": len(xs)}
    rec["未結案"] = sum(1 for t in ts if t["H"].get(H, {}).get("status", "").startswith("未結案"))
    rec["未完成"] = sum(1 for t in ts if t["H"].get(H, {}).get("status", "").startswith("未完成"))
    rec["未解決跳價"] = sum(1 for t in ts if t["H"].get(H, {}).get("status", "").startswith("未解決"))
    if len(xs) >= 1:
        s = dict(summarize(xs, hold_days=hd, cluster=cs, cluster_unit="進場日" if cl == "E" else "批次"))
        rec.update(s); rec.update(中位數=median(xs), 最小值=min(xs), 最大值=max(xs))
    OUT.append(rec); return rec
by = collections.defaultdict(list)
for t in T:
    if ok(t): by[t["r"]["路線"]].append(t)
A, B = by["A"], by["B"]
for side in ("做多", "放空"):
    for H in HS:
        for mode in ("main", "trade", "sens"):
            row("表A｜全體主動退出", A, H, side, mode)
        for g in ("明確尚未委任", "未說明"):
            row(f"表A｜接任狀態：{g}", [t for t in A if t["r"]["A接任狀態"] == g], H, side)
        row("表A｜敏感度：公司聚合（同公司事件先平均）", A, H, side, cl="C")
        row("表A｜敏感度：無同期其他事件", [t for t in A if not t["r"]["同期事件"]], H, side)
        row("表A｜敏感度：有同期其他事件", [t for t in A if t["r"]["同期事件"]], H, side)
        for mode in ("main", "trade", "sens"):
            row("表B｜同案接任（B 晚於 A）", B, H, side, mode)
        for g in ("公司更換", "輪調", "其他", "不明"):
            row(f"表E｜比較組：{g}", by[g], H, side)
# 排除最大貢獻個案（主表、做多）
for H in HS:
    xs = [(pick(t, H, "main", "做多") or (None,))[0] for t in A]; idx = [i for i, x in enumerate(xs) if x is not None]
    if len(idx) > 2:
        m = max(idx, key=lambda i: abs(xs[i]))
        row(f"表A｜敏感度：排除絕對報酬最大一筆（{A[m]['r']['事件ID']}）", [t for i, t in enumerate(A) if i != m], H, "做多")
# 同股已有持倉不新增：A 與 B 合併時間序，B 進場時同案 A 持倉未出場者不新增
for H in HS:
    keep = []
    aexit = {t["r"]["案件ID"]: t["H"].get(H, {}).get("exit") or t["H"].get(H, {}).get("sens", {}).get("exit") for t in A}
    for t in B:
        ax = aexit.get(t["r"]["案件ID"])
        if ax and t["E"] <= ax: continue
        keep.append(t)
    row("表B｜敏感度：同股 A 持倉未出場者不新增", keep, H, "做多")
# 表D：共同案件配對（A、B 皆有完整出場）
D = []
bmap = {t["r"]["案件ID"]: t for t in B}
for H in HS:
    pa, pb = [], []
    for t in A:
        b = bmap.get(t["r"]["案件ID"])
        if not b: continue
        x, y = pick(t, H, "main", "做多"), pick(b, H, "main", "做多")
        if x and y: pa.append(x[0]); pb.append(y[0])
    if len(pa) >= 2:
        d = np.array(pa) - np.array(pb); tt = sst.ttest_1samp(d, 0)
        D.append({"H": H, "配對案件數": len(pa), "A平均": np.mean(pa), "B平均": np.mean(pb), "差額平均(A−B)": d.mean(), "差額中位數": float(np.median(d)), "配對t": tt.statistic, "配對雙尾p": tt.pvalue})
    else: D.append({"H": H, "配對案件數": len(pa)})
# 表C：A→B 交易日間隔
CAL = sorted({t["E"] for t in T if t.get("E")})
gaps = []
for t in A:
    b = bmap.get(t["r"]["案件ID"])
    if b: gaps.append((t["r"]["案件ID"], t["E"], b["E"]))
# 跨窗口共同完整樣本（A 做多，主表）
common = [t for t in A if all(pick(t, H, "main", "做多") for H in HS)]
for H in HS: row(f"表A｜跨窗口共同完整樣本（{len(common)}筆）", common, H, "做多")
# Holm（表A／表B 主表與接任分組，做多＋放空）
fam = [r for r in OUT if r["口徑"].startswith("主表") and (r["表"].startswith("表A｜全體") or r["表"].startswith("表A｜接任") or r["表"].startswith("表B｜同案")) and isinstance(r.get("雙尾p"), float)]
def pv(r): return r["聚合p"] if isinstance(r.get("聚合p"), float) else r["雙尾p"]
ps = sorted(((pv(r), i) for i, r in enumerate(fam)))
m = len(ps); prev = 0
for k, (p, i) in enumerate(ps):
    adj = min(1.0, max(prev, (m - k) * p)); prev = adj; fam[i]["Holm校正p"] = adj
pickle.dump({"OUT": OUT, "D": D, "gaps": gaps}, open("S031.pkl", "wb"))
keys = []
for r in OUT:
    for k in r:
        if k not in keys: keys.append(k)
with open("031_回測結果_參數全表_V01_R01.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, keys); w.writeheader(); w.writerows(OUT)
print(len(OUT), "列；Holm 家族", m)
