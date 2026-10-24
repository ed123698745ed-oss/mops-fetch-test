# 029 統計：表A（A路線）、表B（B路線）、表C（B晚於A）、表D（共同案件配對）＋敏感度、Holm、樣本內外與最新年度
import pickle, csv, collections, sys
from statistics import median
sys.path.insert(0, sys.argv[1]); from bt_stats import summarize
T = pickle.load(open("T029.pkl", "rb"))
HS = [1, 2, 3, 5, 10, 20, 40]
def done(t, H): h = t["H"].get(H); return h is not None and "ret" in h
KINDS = {"做多": lambda h: h["ret"], "放空(假設成交)": lambda h: -h["ret"], "做多超額(減大盤,對照)": lambda h: (h["ret"] - h["mk"]) if h["mk"] is not None else None}
def tradable(kind):
    # 可成交口徑的進場條件：做多進場日（E）不是一字漲停；放空進場日不是一字跌停（出場鎖板改為順延，見 table 的 trade 參數）
    if kind.startswith("放空"): return lambda t, h: t.get("entry_lock") != "跌停"
    return lambda t, h: t.get("entry_lock") != "漲停"
def dedup(ts):
    # 同一股票、同一進場日的多個事件為同一筆交易（報酬路徑完全相同），只計一筆：保留公告時間最早者
    seen, out = set(), []
    for t in sorted(ts, key=lambda t: (t["r"]["訊號公告日S"], t["r"]["公告時間"], t["r"]["事件ID"])):
        k = (t["r"]["公司代號"], t["E"])
        if k in seen: continue
        seen.add(k); out.append(t)
    return out
def table(ts, kind, H, extra=None, cl="E", raw=False, trade=False):
    xs, hd, ds = [], [], []
    for t in (ts if raw else dedup(ts)):
        if not done(t, H): continue
        h = t["H"][H]
        if extra and not extra(t, h): continue
        if trade:   # 可成交口徑：進場鎖板取消（由 extra 處理）；出場鎖板順延（用 long／short 子結果）
            side = h.get("short" if kind.startswith("放空") else "long")
            if not side or side.get("ret") is None: continue
            if kind.startswith("做多超額"):
                x = side["ret"] - side["mk"] if side.get("mk") is not None else None
            else: x = side["ret"]
            hold = side["hold"]
        else:
            x = KINDS[kind](h); hold = h["hold"]
        if x is None: continue
        xs.append(x); hd.append(hold); ds.append(t["E"] if cl == "E" else t["r"]["公司代號"])
    if len(xs) < 2: return None
    s = dict(summarize(xs, hold_days=hd, cluster=ds, cluster_unit="進場日" if cl == "E" else "批次"))
    s.update(口徑=kind, 持有H=H, 中位數=median(xs), 最小值=min(xs), 最大值=max(xs))
    return s
def holm(ps):
    idx = sorted(range(len(ps)), key=lambda i: ps[i] if ps[i] == ps[i] else 9); adj = [float("nan")] * len(ps); run = 0; k = len([p for p in ps if p == p])
    for rank, i in enumerate(idx):
        if ps[i] != ps[i]: continue
        run = max(run, min(1, (k - rank) * ps[i])); adj[i] = run
    return adj
def nonoverlap(ts, H):
    keep, last = set(), {}
    for t in sorted(ts, key=lambda t: (t["r"]["訊號公告日S"], t["r"]["公告時間"])):
        if not done(t, H): continue
        sid = t["r"]["公司代號"]
        if sid in last and t["E"] <= last[sid]: continue
        keep.add(id(t)); last[sid] = t["H"][H]["exit"]
    return keep
ROUTES = {
    "表A｜A路線（首次具體處分公告）": lambda t: t["r"]["路線"] == "A",
    "表B｜B路線（首次量化處分損益）": lambda t: t["r"]["路線"] == "B",
    "表C｜B晚於A（B路線中金額晚於首次公告揭露者）": lambda t: t["r"]["路線"] == "B" and t["r"]["A與B同公告"] != "True",
}
LAYERS = [
    ("第一層：全體", lambda t: "全體"),
    ("第二層：損益方向", lambda t: t["損益分組"]),
    ("第三層：利益占市值（稅前含推定）", lambda t: t["市值分組"] if t["損益分組"] == "明確利益" and t["稅別組"] != "稅後" else None),
    ("第三層補充：利益占市值（稅後）", lambda t: t["市值分組"] if t["損益分組"] == "明確利益" and t["稅別組"] == "稅後" else None),
    ("資產類型", lambda t: t["r"]["資產類型"]),
    ("股權細分（描述）", lambda t: t["r"]["股權細分"] or None),
    ("補充：預估／實際", lambda t: t["r"]["預估實際"] if t["損益分組"] in ("明確利益", "明確損失", "零") else None),
]
SAMPLES = [("全期", lambda t: True), ("樣本內(≤2020-10)", lambda t: t["side"] == "樣本內"), ("樣本外(≥2021)", lambda t: t["side"] == "樣本外"),
           ("最新年度(2026)", lambda t: t["r"]["訊號公告日S"][:4] == "2026")]
rows = []
for rname, rf in ROUTES.items():
    T0 = [t for t in T if rf(t)]
    c = collections.Counter(t["E"] for t in dedup([t for t in T0 if "open" in t]))
    print(rname, "去重後交易", sum(c.values()), "進場日數", len(c), "單日最多", max(c.values()) if c else 0, "去重刪除", sum(1 for t in T0 if "open" in t) - sum(c.values()))
    common = {id(t) for t in T0 if all(done(t, H) for H in HS)}
    for sname, sf in SAMPLES:
        ts0 = [t for t in T0 if sf(t)]
        for lname, key in LAYERS:
            groups = collections.defaultdict(list)
            for t in ts0:
                k = key(t)
                if k is not None: groups[k].append(t)
            fam = []
            for g, gts in sorted(groups.items()):
                for kind in KINDS:
                    for H in HS:
                        s = table(gts, kind, H, tradable(kind), trade=True)
                        if s: s.update(表=rname, 樣本=sname, 層=lname, 組=g, 子樣本="可成交（正式）"); fam.append(s)
                        s0 = table(gts, kind, H)
                        if s0: s0.update(表=rname, 樣本=sname, 層=lname, 組=g, 子樣本="理論價格（含鎖板）"); rows.append(s0)
                        if sname == "全期" and kind != "做多超額(減大盤,對照)":
                            for sub, ex in (("七窗口共同完整樣本", lambda t, h: id(t) in common), ):
                                s2 = table(gts, kind, H, lambda t, h, tr=tradable(kind): ex(t, h) and tr(t, h), trade=True)
                                if s2: s2.update(表=rname, 樣本=sname, 層=lname, 組=g, 子樣本=sub); rows.append(s2)
                            no = nonoverlap(gts, H)
                            s3 = table(gts, kind, H, lambda t, h, tr=tradable(kind): id(t) in no and tr(t, h), trade=True)
                            if s3: s3.update(表=rname, 樣本=sname, 層=lname, 組=g, 子樣本="同股持倉中不新增部位"); rows.append(s3)
                            s5 = table(gts, kind, H, tradable(kind), raw=True, trade=True)
                            if s5: s5.update(表=rname, 樣本=sname, 層=lname, 組=g, 子樣本="未去重（同股同日多事件各計一筆）"); rows.append(s5)
                            if lname == "第一層：全體":
                                s4 = table(gts, kind, H, tradable(kind), cl="co", trade=True)
                                if s4: s4.update(表=rname, 樣本=sname, 層=lname, 組=g, 子樣本="公司聚合敏感度（批次＝同一公司）"); rows.append(s4)
            for kind in ("做多", "放空(假設成交)"):
                sub = [s for s in fam if s["口徑"] == kind]
                for s, a in zip(sub, holm([s["聚合p"] if s["聚合p"] is not None else float("nan") for s in sub])): s["Holm_聚合p(層內)"] = a
            rows += fam
# 表D：同案 A 與 B（B 晚於 A）配對
A = {t["r"]["事件ID"]: t for t in T if t["r"]["路線"] == "A"}
pairs = [(A[t["r"]["事件ID"]], t) for t in T if t["r"]["路線"] == "B" and t["r"]["A與B同公告"] != "True" and t["r"]["事件ID"] in A]
D = []
CPOS_ = None
for H in HS:
    pa = [(a, b) for a, b in pairs if done(a, H) and done(b, H)]
    for nm, sel in (("A報酬", lambda a, b: a["H"][H]["ret"]), ("B報酬", lambda a, b: b["H"][H]["ret"]), ("配對差(B−A)", lambda a, b: b["H"][H]["ret"] - a["H"][H]["ret"])):
        xs = [sel(a, b) for a, b in pa]
        if len(xs) < 2: continue
        s = dict(summarize(xs, hold_days=[(a if nm == "A報酬" else b)["H"][H]["hold"] for a, b in pa] if nm != "配對差(B−A)" else None,
                           cluster=[b["E"] for a, b in pa], cluster_unit="進場日"))
        s.update(表="表D｜共同案件（同時有A與B且B晚於A）", 樣本="全期", 層="配對", 組=nm, 口徑="做多", 持有H=H, 子樣本="同案共同完整", 中位數=median(xs), 最小值=min(xs), 最大值=max(xs))
        if nm == "配對差(B−A)": s["N/A原因"] = (s.get("N/A原因") or "") + "；配對差只看平均、t、p，勝率／R／凱利／年化不具交易意義"
        D.append(s)
rows += D
cols = ["表", "樣本", "層", "組", "子樣本", "口徑", "持有H", "樣本數", "平均報酬", "平均持有交易日數", "單利年化", "勝率", "賠率R", "凱利", "半凱利", "標準差", "t值", "雙尾p",
        "聚合單位", "聚合單位數", "單位最大筆數", "聚合t", "聚合p", "Holm_聚合p(層內)", "中位數", "最小值", "最大值", "N/A原因", "bt_stats版本"]
with open("029_回測結果_參數全表_V01_R03.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f); w.writerow(cols)
    for s in rows: w.writerow(["" if s.get(c) is None else s.get(c) for c in cols])
# B 距 A 交易日數分布（以進場日在市場日曆的位置差計）
gd = sorted(b["Ei"] - a["Ei"] for a, b in pairs if a.get("Ei") is not None and b.get("Ei") is not None)
bins = [(1, 5), (6, 20), (21, 60), (61, 120), (121, 10**6)]
with open("029_表D_B距A交易日數分布.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f); w.writerow(["B距A交易日數", "案件數"])
    for lo, hi in bins: w.writerow([f"{lo}～{hi if hi < 10**6 else ''}", sum(lo <= x <= hi for x in gd)])
    w.writerow(["中位數", median(gd) if gd else ""]); w.writerow(["0（同日進場）", sum(x == 0 for x in gd)])
print("rows", len(rows), "pairs", len(pairs), "gap median", median(gd) if gd else None)
