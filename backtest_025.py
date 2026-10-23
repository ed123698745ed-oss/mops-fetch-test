# 策略025 回測 R04（2026-10-23，Ed 指示「開始進行」；Eve 2026-10-21 對 R03 複審退回：價格比例還原等於把現金以參考價再投資，與策略卡第11、13節不符）
# R04 相對 R03：公司行動改為「固定持股數＋現金／應收權利」逐筆計算，不再使用 before_price/after_price 連乘因子。
#   報酬＝(出場收盤 × 持股倍數 ＋ 持有期間現金權利合計) ÷ 進場開盤價 − 1（多方，進場本金為分母）；放空＝其負值（應負擔股利／配股，初始賣出名目本金為分母）。
#   現金股利／退還現金：入帳於除息（恢復買賣）日，名目金額，不再投資、不折現。配股：持股倍數×(1＋配股率)；減資換股：持股倍數×換發比率。
#   資料：純現金股利＝FinMind TaiwanStockDividendResult 實際「息／除息」欄位 stock_and_cache_dividend；權息混合＝FinMind TaiwanStockDividend 的
#   盈餘配股（面額10元）與盈餘現金股利，並以除權息前價格驗算參考價；陞泰減資＝corporate_actions_025.csv（MOPS 公告）。
#   現金增資認購權（除權但無股票／現金股利）無處置資料 → 列「未解決」，不推估、不納入統計，狀態欄列價格報酬與權值上下界供參考。
# 以下為 R03 說明（保留）：
# 策略025 回測 R03（2026-10-21，Ed 00:54 指示「好修正R03」；R02 為 2026-10-20 依 Eve V01/R01 審查退回意見修正；口徑依策略卡 V01 第 9～14 節）
# R03 相對 R02：
#  a. 跳價檢查改為「與前一有效收盤相隔 n 個市場交易日時，容許 n 日累積漲跌停幅度＋1.5 個百分點」。R02 用單日限制，
#     把中間無成交日的連續漲跌停誤判為公司行動（地心引力 3629、勝昱 4304、中茂 5205 共 6 筆）。
#  b. 已核對的公司行動以 corporate_actions_025.csv 調整（現依 MOPS 公告與官方參考價公式）：陞泰 8072 2017 現金減資，
#     恢復買賣日因子＝停止買賣前收盤 ÷ 恢復買賣參考價（等同除權息因子的處理）。
# 與 R01 的差異：
#  1. 持有天數一律以「市場交易日」計（日曆＝FinMind 加權指數有收盤的日期），不再以個股有效日K計。
#  2. 進場日 E＝公告日期之後第一個市場交易日；E 當日個股無有效開盤（無資料、成交量 0、開盤≤0）→ 列「進場無法成交」，不自行延後。
#  3. 預定出場日＝E 起第 H 個市場交易日；當日個股無有效收盤 → 順延至第一個有有效收盤的市場交易日，記實際持有日數。
#     若在順延期間已終止上市櫃 → 以終止前最後一個有效收盤（最終交易）結算並標記；仍無價 → 列「未解決」，不刪除、不填零。
#     預定出場日晚於資料終點 → 列「未完成（尚未到出場日）」。
#  4. 持有期間（不含進場日）出現無法以除權息解釋的跳價（超過當時漲跌幅限制 1.5 個百分點以上）→ 列「未解決：疑似公司行動未核對」，不納入統計。
#  5. 可成交性：進場日或出場日為「一字價且達漲跌停」者，標記為不可證明成交；理論價格樣本全列，另列可成交樣本。
#  6. 另列：七窗口共同完整樣本、中位數與極端值、年度與個股分布、同股持倉期間不新增部位的敏感度。
import csv, json, collections, datetime as dt
from statistics import median
from bt_stats import summarize   # 共用統計函式 bt_stats 1.0（Drive 原檔，selftest 通過）
HS = [1, 2, 3, 5, 10, 20, 40]
def load(sid, ds="TaiwanStockPrice"):
    try: return json.load(open(f"prices/raw/{ds}_{sid}.json"))["data"]
    except FileNotFoundError: return []
IDX = {k: {r["date"]: r for r in load(k)} for k in ("TAIEX", "TPEx")}
CAL = sorted(d for d, r in IDX["TAIEX"].items() if r["close"] > 0)          # 市場交易日曆
CPOS = {d: i for i, d in enumerate(CAL)}; DATA_END = CAL[-1]
PER = {r["公司代號"]: r for r in csv.DictReader(open("listing/上市櫃期間表.csv", encoding="utf-8-sig"))}
E = list(csv.DictReader(open("out/025_事件表.csv", encoding="utf-8-sig")))
OBS = [r for r in csv.DictReader(open("out/025_全候選判讀.csv", encoding="utf-8-sig")) if "土地出售附帶" in r["類別"]]
for r in OBS: r["事件ID"] = f'{r["公司代號"]}_{r["發言日期"]}_{r["發言時間"]}'; r["發動方"] = "公司主動"
def limit(d): return 0.07 if d < "2015-06-01" else 0.10
def iso(s): return f"{s[:4]}-{s[4:6]}-{s[6:]}"
CACHE = {}
def stock(sid):
    if sid not in CACHE:
        px = {x["date"]: x for x in load(sid)}
        div = load(sid, "TaiwanStockDividend")
        ev = {}
        for x in load(sid, "TaiwanStockDividendResult"):
            d, typ, val = x["date"], x["stock_or_cache_dividend"], x["stock_and_cache_dividend"]
            if typ in ("息", "除息"):
                ev[d] = dict(m=1.0, c=val, note=f"現金股利{val}元（FinMind 除息結果）")
                continue
            rows = [y for y in div if d in (y["StockExDividendTradingDate"], y["CashExDividendTradingDate"])]
            if len(rows) != 1: ev[d] = dict(bad=f"{typ}：無法對應唯一股利政策（{len(rows)}筆），無法拆分現金與配股", val=val, bef=x["before_price"], aft=x["after_price"]); continue
            y = rows[0]; st = (y["StockEarningsDistribution"] + y["StockStatutorySurplus"]) / 10.0; ca = y["CashEarningsDistribution"] + y["CashStatutorySurplus"]
            if y["CashIncreaseSubscriptionRate"] > 0:
                ev[d] = dict(bad=f"{typ}：現金增資認購權（每千股{y['CashIncreaseSubscriptionRate']:.4g}股、認購價{y['CashIncreaseSubscriptionpRrice']}），權利處置無資料", val=val, bef=x["before_price"], aft=x["after_price"], st=st, ca=ca); continue
            if abs((x["before_price"] - ca) / (1 + st) - x["after_price"]) > 0.05:
                ev[d] = dict(bad=f"{typ}：股利政策與參考價不符，無法核對", val=val, bef=x["before_price"], aft=x["after_price"]); continue
            ev[d] = dict(m=1 + st, c=ca, note=f"現金股利{ca}元＋配股{st:.4g}股／股（FinMind TaiwanStockDividend；參考價驗算）")
        for c in CA.get(sid, []):
            d = c["恢復買賣日"]; ev[d] = dict(m=1 - float(c["減資比率"]), c=float(c["每股退還現金"]), note=f"{c['類型']}：每原股換{1-float(c['減資比率']):.4g}股、退還現金{c['每股退還現金']}元（MOPS）")
        CACHE[sid] = (px, ev)
    return CACHE[sid]
CA = {}
for c in csv.DictReader(open("corporate_actions_025.csv", encoding="utf-8-sig")): CA.setdefault(c["公司代號"], []).append(c)
def valid(x): return x is not None and x["Trading_Volume"] > 0 and x["open"] > 0 and x["close"] > 0
def prev_valid(px, d):   # 回傳 (前一有效收盤, 相隔市場交易日數)
    i = CPOS[d] - 1
    while i >= 0:
        x = px.get(CAL[i])
        if valid(x): return x["close"], CPOS[d] - i
        i -= 1
    return None, 0
def prev_close(px, d):
    i = CPOS[d] - 1
    while i >= 0:
        x = px.get(CAL[i])
        if valid(x): return x["close"]
        i -= 1
    return None
def locked(px, d):   # 一字價且達漲跌停：日線無法證明成交
    x = px[d]; pc = prev_close(px, d)
    return x["open"] == x["max"] == x["min"] == x["close"] and pc is not None and abs(x["close"] / pc - 1) >= limit(d) - 0.005
def build(evs, tag):
    out, notes = [], []
    for r in evs:
        sid = r["公司代號"]; px, dv = stock(sid); ad = iso(r["發言日期"])
        end = PER.get(sid, {}).get("終止上市櫃日", ""); end = iso(end) if end else ""
        ei = next((i for i, d in enumerate(CAL) if d > ad), None)
        base = {"r": r, "tag": tag, "E": CAL[ei] if ei is not None else "", "H": {}}
        if ei is None: notes.append((r, "全部", "資料終點前無公告後交易日")); continue
        Ed = CAL[ei]; en = px.get(Ed)
        if not valid(en):
            why = "進場日無有效開盤（%s）" % ("無資料" if en is None else f"成交量{en['Trading_Volume']}、開盤{en['open']}")
            notes.append((r, "全部", why + "；依策略卡第11節不延後進場")); base["entry_fail"] = why; out.append(base); continue
        base["open"] = en["open"]; base["entry_lock"] = locked(px, Ed)
        for H in HS:
            xi = ei + H - 1
            if xi >= len(CAL): base["H"][H] = {"status": "未完成（尚未到出場日）", "sched": ""}; continue
            sched = CAL[xi]; j = xi; act = None; status = "正常"
            while j < len(CAL):
                d = CAL[j]
                if end and d >= end: break
                if valid(px.get(d)): act = d; break
                j += 1
            if act is None:
                if end and sched >= end or (end and j < len(CAL) and CAL[j] >= end):
                    last = next((CAL[k] for k in range(min(j, len(CAL)) - 1, ei, -1) if valid(px.get(CAL[k]))), None)
                    if last: act, status = last, f"下市（{end}）前以最終交易日收盤結算"
                    else: base["H"][H] = {"status": f"未解決：{end} 終止上市櫃，持有期間無最終交易價", "sched": sched}; continue
                else:
                    base["H"][H] = {"status": "未完成（順延後仍無有效收盤，資料終點）", "sched": sched}; continue
            elif act != sched:
                status = f"出場順延（預定 {sched} 無有效收盤）"
            # 跳價檢查（不含進場日；除權息日不檢查）
            jump = None
            k0 = CPOS[Ed]
            for k in range(k0 + 1, CPOS[act] + 1):
                d = CAL[k]; x = px.get(d)
                if not valid(x) or d in dv: continue
                pc, n = prev_valid(px, d)   # 中間無成交日時，容許 n 日累積漲跌停幅度
                up = (1 + limit(d)) ** n - 1 + 0.015; dn = 1 - (1 - limit(d)) ** n + 0.015
                if pc and any(v / pc - 1 > up or 1 - v / pc > dn for v in (x["open"], x["close"])):
                    jump = (d, pc, x["open"], x["close"]); break
            if jump:
                base["H"][H] = {"status": f"未解決：{jump[0]} 跳價（前收 {jump[1]} → 開 {jump[2]}／收 {jump[3]}）疑似公司行動未核對", "sched": sched}; continue
            sh, cash, notes_ca, bad = 1.0, 0.0, [], None
            for k in range(k0 + 1, CPOS[act] + 1):
                e = dv.get(CAL[k])
                if not e: continue
                if "bad" in e: bad = (CAL[k], e); break
                cash += sh * e["c"]; sh *= e["m"]; notes_ca.append(f"{CAL[k]} {e['note']}")
            ex = px[act]
            idx = IDX["TPEx" if r["市場別"] == "otc" else "TAIEX"]; ia, ib = idx.get(Ed), idx.get(act)
            mk = (ib["close"] / ia["open"] - 1) if ia and ib else None
            if bad:
                d_, e = bad; pr = ex["close"] / en["open"] - 1; lo = f"價格報酬{pr:+.4%}"; hi = None
                if "val" in e: hi = (ex["close"] + e["val"]) / en["open"] - 1; lo += f"；若除權價差（FinMind 權值{e['val']}元/原股）計為應收則約{hi:+.4%}（僅供界線，未納入）"
                base["H"][H] = {"status": f"未解決：{d_} {e['bad']}。{lo}", "sched": sched,
                                "alt": {"lo": pr, "hi": hi, "hold": CPOS[act] - k0 + 1, "mk": mk, "exit_lock": locked(px, act), "exit": act}}; continue
            g = (ex["close"] * sh + cash) / en["open"] - 1
            base["H"][H] = {"status": status, "sched": sched, "exit": act, "close": ex["close"], "sh": sh, "cash": cash, "ca": "；".join(notes_ca), "ret": g, "mk": mk,
                            "hold": CPOS[act] - k0 + 1, "exit_lock": locked(px, act)}
        out.append(base)
    return out, notes
T, NOTES = build(E, "主樣本"); TO, _ = build(OBS, "觀察組(遠雄)")
def done(t, H): h = t["H"].get(H); return h is not None and "ret" in h
def holm(ps):
    idx = sorted(range(len(ps)), key=lambda i: ps[i] if ps[i] == ps[i] else 9); adj = [float("nan")] * len(ps); run = 0; k = len([p for p in ps if p == p])
    for rank, i in enumerate(idx):
        if ps[i] != ps[i]: continue
        run = max(run, min(1, (k - rank) * ps[i])); adj[i] = run
    return adj
def table(ts, label, kind, H, extra=None):
    xs, hd, ds = [], [], []
    for t in ts:
        if not done(t, H): continue
        h = t["H"][H]
        if extra and not extra(t, h): continue
        x = {"做多": h["ret"], "放空(做多取負)": -h["ret"], "做多超額(減大盤)": (h["ret"] - h["mk"]) if h["mk"] is not None else None}[kind]
        if x is None: continue
        xs.append(x); hd.append(h["hold"]); ds.append(t["E"])
    if len(xs) < 2: return None
    s = dict(summarize(xs, hold_days=hd, cluster=ds, cluster_unit="進場日"))
    s.update(組=label, 口徑=kind, 持有H=H, 中位數=median(xs), 最小值=min(xs), 最大值=max(xs),
             第5百分位=sorted(xs)[max(0, int(len(xs) * 0.05) - 1)] if len(xs) >= 20 else None)
    return s
def ctype(r): return {"商業合約": "商業合約", "技術與產品授權": "技術與產品授權"}.get(r["類別"], "工程發包" if r["類別"].startswith("工程") else "租賃出租方")
LAYERS = [("全體", lambda r: "全體"), ("終止時點", lambda r: r["終止時點"]), ("合約類型", ctype), ("發動方", lambda r: r["發動方"])]
SAMPLES = [("全期", lambda r: True), ("樣本內", lambda r: r["發言日期"] <= "20210630"), ("樣本外", lambda r: r["發言日期"] >= "20210901")]
TRADABLE = lambda t, h: not t.get("entry_lock") and not h.get("exit_lock")
COMMON = {id(t) for t in T if all(done(t, H) for H in HS)}
def nonoverlap(ts, H):   # 同股持倉期間不新增部位：依公告順序，同股前一筆的實際出場日之前（含）進場者略過
    keep, last = set(), {}
    for t in sorted(ts, key=lambda t: (t["r"]["發言日期"], int(t["r"]["發言時間"] or 0))):
        if not done(t, H): continue
        sid = t["r"]["公司代號"]
        if sid in last and t["E"] <= last[sid]: continue
        keep.add(id(t)); last[sid] = t["H"][H]["exit"]
    return keep
rows = []
for sname, sf in SAMPLES:
    ts0 = [t for t in T if sf(t["r"])]
    for lname, key in LAYERS:
        fam = []
        groups = collections.defaultdict(list)
        for t in ts0: groups[key(t["r"])].append(t)
        for g, gts in sorted(groups.items()):
            for kind in ("做多", "放空(做多取負)", "做多超額(減大盤)"):
                for H in HS:
                    s = table(gts, g, kind, H)
                    if s: s.update(樣本=sname, 層=lname, 子樣本="理論價格（全部完成）"); fam.append(s)
                    if sname == "全期":
                        for sub, ex in (("可成交樣本", TRADABLE), ("七窗口共同完整樣本", lambda t, h: id(t) in COMMON)):
                            s2 = table(gts, g, kind, H, ex)
                            if s2: s2.update(樣本=sname, 層=lname, 子樣本=sub); rows.append(s2)
                        no = nonoverlap(gts, H)
                        s3 = table(gts, g, kind, H, lambda t, h: id(t) in no)
                        if s3: s3.update(樣本=sname, 層=lname, 子樣本="同股不新增部位"); rows.append(s3)
        for kind in ("做多", "放空(做多取負)"):
            sub = [s for s in fam if s["口徑"] == kind and not (lname != "全體" and s["組"] == "不明")]
            for s, a in zip(sub, holm([s["聚合p"] if s["聚合p"] is not None else float("nan") for s in sub])): s["Holm_聚合p"] = a
        rows += fam
for kind in ("做多", "做多超額(減大盤)"):
    for H in HS:
        s = table(TO, "遠雄觀察組", kind, H)
        if s: s.update(樣本="全期", 層="觀察組", 子樣本="理論價格（全部完成）"); rows.append(s)
cols = ["樣本", "層", "組", "子樣本", "口徑", "持有H", "樣本數", "平均報酬", "平均持有交易日數", "單利年化", "勝率", "賠率R", "凱利", "半凱利", "標準差", "t值", "雙尾p",
        "聚合單位", "聚合單位數", "單位最大筆數", "聚合t", "聚合p", "Holm_聚合p", "中位數", "第5百分位", "最小值", "最大值", "N/A原因", "bt_stats版本"]
w = csv.writer(open("out/025_回測結果_參數全表_V01_R04.csv", "w", encoding="utf-8-sig", newline="")); w.writerow(cols)
for s in rows: w.writerow(["" if s.get(c) is None else s.get(c) for c in cols])
# 敏感度：現金增資認購權列（匯僑 2904 2022-08-23，主表列未解決）以兩種口徑納入的界線（全期、做多、理論價格；不改主表）
import copy
def with_alt(key):
    out = []
    for t in T:
        t2 = dict(t); t2["H"] = {}
        for H, h in t["H"].items():
            a = h.get("alt")
            if a and a.get(key) is not None: h2 = dict(h); h2.update(ret=a[key], mk=a["mk"], hold=a["hold"], exit_lock=a["exit_lock"], exit=a["exit"]); t2["H"][H] = h2
            else: t2["H"][H] = h
        out.append(t2)
    return out
sens_rows = []
for conv, key in (("納入：價格報酬（認購權不計值）", "lo"), ("納入：除權價差計為應收（FinMind 權值）", "hi")):
    TT = with_alt(key)
    for lname, kf in (("全體", lambda r: True), ("到期不續約", lambda r: r["終止時點"] == "到期不續約"), ("租賃出租方", lambda r: ctype(r) == "租賃出租方"), ("對方發動", lambda r: r["發動方"] == "對方發動")):
        for H in HS:
            s_ = table([t for t in TT if kf(t["r"])], lname, "做多", H)
            if s_: s_.update(樣本="全期", 層="敏感度", 子樣本=conv); sens_rows.append(s_)
w = csv.writer(open("out/025_敏感度_匯僑現增認購權_V01_R04.csv", "w", encoding="utf-8-sig", newline="")); w.writerow(cols)
for s_ in sens_rows: w.writerow(["" if s_.get(c) is None else s_.get(c) for c in cols])
# 年度與個股分布（全期、做多、H10／H20，理論價格）
w = csv.writer(open("out/025_分布_年度個股_V01_R04.csv", "w", encoding="utf-8-sig", newline=""))
w.writerow(["分類", "鍵", "持有H", "樣本數", "平均報酬", "中位數", "合計報酬貢獻"])
for H in (10, 20):
    for kname, kf in (("年度", lambda t: t["r"]["發言日期"][:4]), ("個股", lambda t: f'{t["r"]["公司代號"]} {t["r"]["公司名稱"]}')):
        g = collections.defaultdict(list)
        for t in T:
            if done(t, H): g[kf(t)].append(t["H"][H]["ret"])
        for k, v in sorted(g.items()): w.writerow([kname, k, H, len(v), sum(v) / len(v), median(v), sum(v)])
# 原始數據明細（一列一筆：事件 × 持有期）
dw = csv.writer(open("out/025_原始數據明細_V01_R04.csv", "w", encoding="utf-8-sig", newline=""))
dw.writerow(["交易編號", "持有H", "事件ID", "公司代號", "公司名稱", "公告日", "公告時間", "進場日E", "進場價(開盤)", "預定出場日", "實際出場日", "出場價(收盤)",
             "實際持有市場交易日數", "持股倍數", "現金權利(每原股)", "公司行動明細", "報酬(小數)", "大盤同期報酬", "超額報酬", "聚合單位標籤(進場日)", "樣本內外", "合約類型", "終止時點", "發動方",
             "進場一字鎖板", "出場一字鎖板", "七窗口皆完成", "狀態／排除原因"])
k = 0
for t in T + TO:
    r = t["r"]; grp = t["tag"] if t["tag"] != "主樣本" else ("樣本內" if r["發言日期"] <= "20210630" else ("樣本外" if r["發言日期"] >= "20210901" else "緩衝期"))
    for H in HS:
        k += 1; base = [f"T{k:05d}", H, r["事件ID"], r["公司代號"], r["公司名稱"], r["發言日期"], r["發言時間"], t["E"]]
        if "entry_fail" in t:
            dw.writerow(base + [""] * 11 + [t["E"], grp, r["類別"], r["終止時點"], r["發動方"], "", "", 0, t["entry_fail"] + "，不延後進場"]); continue
        h = t["H"][H]
        if "ret" not in h:
            dw.writerow(base + [t["open"], h["sched"]] + [""] * 9 + [t["E"], grp, r["類別"], r["終止時點"], r["發動方"], int(t["entry_lock"]), "", int(id(t) in COMMON), h["status"]]); continue
        dw.writerow(base + [t["open"], h["sched"], h["exit"], h["close"], h["hold"], h["sh"], h["cash"], h["ca"], h["ret"], "" if h["mk"] is None else h["mk"], "" if h["mk"] is None else h["ret"] - h["mk"],
                    t["E"], grp, r["類別"], r["終止時點"], r["發動方"], int(t["entry_lock"]), int(h["exit_lock"]), int(id(t) in COMMON), h["status"]])
st = collections.Counter()
for t in T:
    if "entry_fail" in t: st["進場無法成交"] += 1; continue
    for H in HS: st[t["H"][H]["status"].split("：")[0].split("（")[0]] += 1
print("事件", len(E), "｜進場無法成交", sum("entry_fail" in t for t in T), "｜進場鎖板", sum(bool(t.get("entry_lock")) for t in T), "｜七窗口完成", len(COMMON))
print("交易狀態", dict(st)); print("明細列", k)
