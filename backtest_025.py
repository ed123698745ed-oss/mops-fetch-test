# 策略025 回測（依 025_判讀規則 第九節預先登記口徑）
import csv, json, math, collections, datetime as dt
from statistics import mean, stdev
HS = [1, 2, 3, 5, 10, 20, 40]; COST = 0.00585
def load(sid, ds="TaiwanStockPrice"):
    try: return json.load(open(f"prices/raw/{ds}_{sid}.json"))["data"]
    except FileNotFoundError: return []
IDX = {k: {r["date"]: r for r in load(k)} for k in ("TAIEX", "TPEx")}
E = list(csv.DictReader(open("out/025_事件表.csv", encoding="utf-8-sig")))
OBS = [r for r in csv.DictReader(open("out/025_全候選判讀.csv", encoding="utf-8-sig")) if "土地出售附帶" in r["類別"]]
for r in OBS: r["事件ID"] = f'{r["公司代號"]}_{r["發言日期"]}_{r["發言時間"]}'; r["發動方"] = "公司主動"
def tcdf(t, df):  # 雙尾 p：Student t（以不完全 beta 函數）
    x = df / (df + t * t)
    def betacf(a, b, x):
        qab, qap, qam = a + b, a + 1, a - 1; c, d = 1.0, 1 - qab * x / qap; d = 1 / d if abs(d) > 1e-30 else 1e30; h = d
        for m in range(1, 300):
            m2 = 2 * m; aa = m * (b - m) * x / ((qam + m2) * (a + m2)); d = 1 + aa * d; d = 1 / d if abs(d) > 1e-30 else 1e30; c = 1 + aa / c if abs(c) > 1e-30 else 1e30; h *= d * c
            aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2)); d = 1 + aa * d; d = 1 / d if abs(d) > 1e-30 else 1e30; c = 1 + aa / c if abs(c) > 1e-30 else 1e30; de = d * c; h *= de
            if abs(de - 1) < 1e-12: break
        return h
    a, b = df / 2, 0.5
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x))
    return bt * betacf(a, b, x) / a if x < (a + 1) / (a + b + 2) else 1 - bt * betacf(b, a, 1 - x) / b
SKIPLIST = []
def trades(evs):
    out, skipped = [], collections.Counter()
    cache = {}
    for r in evs:
        sid = r["公司代號"]
        if sid not in cache:
            px = [x for x in load(sid) if x["close"] > 0]
            dv = {x["date"]: x["before_price"] / x["after_price"] for x in load(sid, "TaiwanStockDividendResult") if x.get("after_price")}
            cache[sid] = (px, dv)
        px, dv = cache[sid]
        ad = dt.datetime.strptime(r["發言日期"], "%Y%m%d").strftime("%Y-%m-%d")
        i = next((k for k, x in enumerate(px) if x["date"] > ad), None)
        if i is None: skipped["無公告後股價"] += 1; SKIPLIST.append((r, "FinMind 無公告日後股價資料")); continue
        en = px[i]
        if en["Trading_Volume"] <= 0 or en["open"] <= 0: skipped["進場日無成交"] += 1; continue
        if (en["date"] > (dt.datetime.strptime(ad, "%Y-%m-%d") + dt.timedelta(days=20)).strftime("%Y-%m-%d")): skipped["公告後20日內無交易(停牌)"] += 1; continue
        anomaly = not (en["min"] <= en["open"] <= en["max"])
        idx = IDX["TPEx" if r["市場別"] == "otc" else "TAIEX"]
        res = {"r": r, "entry": en["date"], "anom": anomaly, "open": en["open"]}
        for H in HS:
            j = i + H - 1
            if j >= len(px): continue
            ex = px[j]; f = 1.0
            for k in range(i + 1, j + 1):
                f *= dv.get(px[k]["date"], 1.0)
            g = ex["close"] * f / en["open"] - 1
            ia, ib = idx.get(en["date"]), idx.get(ex["date"])
            mk = (ib["close"] / ia["open"] - 1) if ia and ib else None
            res[H] = (g, mk, ex["date"], ex["close"], f)
        out.append(res)
    return out, skipped
from bt_stats import summarize   # 共用統計函式 bt_stats 1.0（Drive 原檔，selftest 通過）
def stats(xs, dates, H):
    if len(xs) < 2: return None
    o = summarize(xs, hold_days=[H] * len(xs), cluster=dates, cluster_unit="進場日")
    return dict(o)
def holm(ps):
    idx = sorted(range(len(ps)), key=lambda i: ps[i] if ps[i] == ps[i] else 9); adj = [float("nan")] * len(ps); run = 0; k = len([p for p in ps if p == p])
    for rank, i in enumerate(idx):
        if ps[i] != ps[i]: continue
        run = max(run, min(1, (k - rank) * ps[i])); adj[i] = run
    return adj
T, SK = trades(E); TO, _ = trades(OBS)
def table(ts, label, kind="net"):
    rows = []
    for H in HS:
        xs, ds = [], []
        for t_ in ts:
            if H not in t_: continue
            g, mk = t_[H][0], t_[H][1]
            x = {"gross": g, "excess": (g - mk) if mk is not None else None, "short": -g}[kind]   # 手冊第6節：成本試算非必填，正式結果不扣成本
            if x is None: continue
            xs.append(x); ds.append(t_["entry"])
        s = stats(xs, ds, H)
        if s: s["組"] = label; s["口徑"] = {"gross": "做多", "short": "放空(做多取負)", "excess": "做多超額(減大盤)"}[kind]; s["持有H"] = H; rows.append(s)
    return rows
def layer(ts, key):
    g = collections.defaultdict(list)
    for t_ in ts: g[key(t_["r"])].append(t_)
    return g
IS = [t for t in T if t["r"]["發言日期"] <= "20210630"]; OOS = [t for t in T if t["r"]["發言日期"] >= "20210901"]
def ctype(r): return {"商業合約": "商業合約", "技術與產品授權": "技術與產品授權"}.get(r["類別"], "工程發包" if r["類別"].startswith("工程") else "租賃出租方")
LAYERS = [("全體", lambda r: "全體"), ("終止時點", lambda r: r["終止時點"]), ("合約類型", ctype), ("發動方", lambda r: r["發動方"])]
allrows = []
for sample, ts in [("全期", T), ("樣本內", IS), ("樣本外", OOS)]:
    for lname, key in LAYERS:
        fam = []
        for gname, gts in sorted(layer(ts, key).items()):
            for kind in ("gross", "short", "excess"):
                for s in table(gts, gname, kind): s["樣本"] = sample; s["層"] = lname; fam.append(s)
        for kind in ("gross", "short"):
            sub = [s for s in fam if s["口徑"] == {"gross": "做多", "short": "放空(做多取負)"}[kind] and not (lname != "全體" and s["組"] == "不明")]
            for s, a in zip(sub, holm([s["聚合p"] if s["聚合p"] is not None else float("nan") for s in sub])): s["Holm_聚合p"] = a
        allrows += fam
for kind in ("gross", "excess"):
    for s in table(TO, "遠雄觀察組", kind): s["樣本"] = "全期"; s["層"] = "觀察組"; allrows.append(s)
cols = ["樣本", "層", "組", "口徑", "持有H", "樣本數", "平均報酬", "平均持有交易日數", "單利年化", "勝率", "賠率R", "凱利", "半凱利", "標準差", "t值", "雙尾p", "聚合單位", "聚合單位數", "單位最大筆數", "聚合t", "聚合p", "Holm_聚合p", "N/A原因", "bt_stats版本"]
w = csv.writer(open("out/025_回測結果_R01.csv", "w", encoding="utf-8-sig", newline="")); w.writerow(cols)
for s in allrows: w.writerow([s.get(c, "") if not isinstance(s.get(c), float) else round(s[c], 6) for c in cols])
tw = csv.writer(open("out/025_交易明細_R01.csv", "w", encoding="utf-8-sig", newline=""))
tw.writerow(["事件ID", "公司代號", "公司名稱", "公告日", "進場日", "開盤異常"] + [f"H{H}_報酬" for H in HS] + [f"H{H}_大盤" for H in HS] + ["類別", "終止時點", "發動方"])
for t_ in T + TO:
    r = t_["r"]; tw.writerow([r["事件ID"], r["公司代號"], r["公司名稱"], r["發言日期"], t_["entry"], int(t_["anom"])] + [round(t_[H][0], 6) if H in t_ else "" for H in HS] + [round(t_[H][1], 6) if H in t_ and t_[H][1] is not None else "" for H in HS] + [r["類別"], r["終止時點"], r["發動方"]])
print("事件", len(E), "可交易", len(T), "剔除", dict(SK), "開盤異常", sum(t["anom"] for t in T), "樣本內", len(IS), "樣本外", len(OOS))

# 原始數據明細（長格式：一列一筆交易＝事件×持有期）
def ctype2(r): return ctype(r) if r in E else "觀察組(遠雄)"
dw = csv.writer(open("out/025_原始數據明細_V01_R01.csv", "w", encoding="utf-8-sig", newline=""))
dw.writerow(["交易編號", "參數組(持有H)", "事件ID", "公司代號", "公司名稱", "市場別(現況)", "公告日", "公告時間", "進場日", "進場價(開盤)", "出場日", "出場價(收盤)",
             "除權息調整因子", "報酬(小數)", "大盤同期報酬", "超額報酬", "持有交易日數", "聚合單位標籤(進場日)", "樣本內外", "合約類型", "終止時點", "發動方", "開盤異常", "排除原因"])
k = 0
for t_ in T + TO:
    r = t_["r"]; grp = "觀察組(遠雄)" if t_ in TO else ("樣本內" if r["發言日期"] <= "20210630" else ("樣本外" if r["發言日期"] >= "20210901" else "緩衝期"))
    for H in HS:
        k += 1
        if H not in t_:
            dw.writerow([f"T{k:05d}", H, r["事件ID"], r["公司代號"], r["公司名稱"], r["市場別"], r["發言日期"], r["發言時間"], t_["entry"], t_["open"], "", "", "", "", "", "", "", t_["entry"], grp, r["類別"], r["終止時點"], r["發動方"], int(t_["anom"]), "持有期超出資料終點(下市或資料截止)"]); continue
        g, mk, xd, xc, f = t_[H]
        dw.writerow([f"T{k:05d}", H, r["事件ID"], r["公司代號"], r["公司名稱"], r["市場別"], r["發言日期"], r["發言時間"], t_["entry"], t_["open"], xd, xc, round(f, 6), round(g, 6),
                     "" if mk is None else round(mk, 6), "" if mk is None else round(g - mk, 6), H, t_["entry"], grp, r["類別"], r["終止時點"], r["發動方"], int(t_["anom"]), ""])
for r, why in SKIPLIST:
    k += 1; dw.writerow([f"T{k:05d}", "全部", r["事件ID"], r["公司代號"], r["公司名稱"], r["市場別"], r["發言日期"], r["發言時間"]] + [""] * 15 + [why])
print("明細列數", k)
