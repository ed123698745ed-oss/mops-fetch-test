# 031「重大訊息－會計師異動策略」V01／R01 正式回測（Elon，2026-10-22）
# 口徑依策略卡 V01 第 9～13 節及 Ed 2026-10-22 補正：
#  1. E＝訊號公告日 S（台灣時間）之後第一個市場交易日（市場日曆＝加權指數有收盤之日），不分盤前盤中盤後；E 開盤進場。
#     E 個股無有效開盤（無資料／成交量 0／開盤≤0）→「進場無法成交」，不延後。
#  2. 出場：E 起第 H 個市場交易日收盤（H＝1,2,3,5,10,20,40；進場日算第 1 日）。當日無有效收盤 → 順延至第一個有效收盤日（記實際持有日數）。
#     順延期間終止上市櫃、或停牌至資料終點仍無有效收盤 →「未結案」：主表排除並列數；敏感度以進場後最後一個有效收盤價結算（Ed 10/22 同意）。
#     預定出場日晚於資料終點 →「未完成」。
#  3. 報酬＝出場收盤 × 持有期間公司行動調整因子 ÷ 進場開盤 − 1（因子＝除權息前收盤÷參考價；減資、分割、面額變更同法）；放空＝−報酬（假設成交研究）。
#  4. 持有期間無法以公司行動解釋的跳價（相隔 n 日超過 n 日累積漲跌停＋1.5 個百分點）→「未解決：疑似公司行動未核對」，不進主表。
#  5. 進場或出場日一字鎖板 → 標記日線無法證明成交；理論價格樣本全列，另列可成交樣本。
#  6. 股票池：E 落在上市櫃期間表的初次上市櫃日～終止上市櫃日之間；期間表無此代號者，E 前 20 個交易日價格皆符合漲跌幅限制且開盤在高低價內，推定上市櫃並標記，否則排除（興櫃）。
import csv, json, gzip, os, sys, bisect, math, pickle
import pandas as pd
DATA, REPO, EVF = sys.argv[1], sys.argv[2], sys.argv[3]
HS = [1, 2, 3, 5, 10, 20, 40]
def rcsv(p):
    if not os.path.exists(p): return []
    with gzip.open(p, "rt", encoding="utf-8") as f: return list(csv.DictReader(f))
def rjson(p):
    if not os.path.exists(p): return []
    return json.load(open(p, encoding="utf-8")).get("data", [])
def fl(x):
    try: return float(x)
    except (TypeError, ValueError): return 0.0
IDX = {k: {r["date"]: {"open": fl(r["open"]), "close": fl(r["close"])} for r in rcsv(f"{DATA}/_{k}_Price.csv.gz")} for k in ("TAIEX", "TPEx")}
CAL = sorted(d for d, r in IDX["TAIEX"].items() if r["close"] > 0); CPOS = {d: i for i, d in enumerate(CAL)}
PER = {r["公司代號"]: r for r in csv.DictReader(open(f"{REPO}/listing/上市櫃期間表.csv", encoding="utf-8-sig"))}
TWSE = {x.get("公司代號") or x.get("Code") for x in json.load(open(f"{REPO}/listing/twse_L.json", encoding="utf-8"))} if os.path.exists(f"{REPO}/listing/twse_L.json") else set()
def iso(s): return f"{s[:4]}-{s[4:6]}-{s[6:]}"
def limit(d): return 0.07 if d < "2015-06-01" else 0.10
SPLIT = {}
for x in rjson(f"{DATA}/_SplitPrice_all.json"): SPLIT.setdefault(x.get("stock_id"), []).append(x)
PVC = {}
for x in rjson(f"{DATA}/_ParValueChange_all.json"): PVC.setdefault(x.get("stock_id"), []).append(x)
CACHE = {}
def stock(sid):
    if sid in CACHE: return CACHE[sid]
    px = {r["date"]: {"open": fl(r["open"]), "max": fl(r["max"]), "min": fl(r["min"]), "close": fl(r["close"]), "vol": fl(r["Trading_Volume"])} for r in rcsv(f"{DATA}/{sid}_TaiwanStockPrice.csv.gz")}
    ca = {}
    def add(d, f, why):
        if d and f and f > 0 and abs(f - 1) > 1e-9: ca.setdefault(d, []).append((f, why))
    for x in rjson(f"{DATA}/{sid}_TaiwanStockDividendResult.json"):
        if fl(x.get("after_price")): add(x["date"], fl(x["before_price"]) / fl(x["after_price"]), "除權息")
    for x in rjson(f"{DATA}/{sid}_TaiwanStockCapitalReductionReferencePrice.json"):
        a, b = fl(x.get("ClosingPriceonTheLastTradingDay")), fl(x.get("PostReductionReferencePrice"))
        if a and b: add(x["date"], a / b, "減資")
    sp = {(x.get("date"), x.get("before_price")) : x for x in rjson(f"{DATA}/{sid}_TaiwanStockSplitPrice.json") + SPLIT.get(sid, [])}
    for x in sp.values():
        a, b = fl(x.get("before_price")), fl(x.get("after_price"))
        if a and b: add(x["date"], a / b, "分割／合併")
    for x in PVC.get(sid, []):
        a, b = fl(x.get("before_close")), fl(x.get("after_ref_close") or x.get("after_ref_open"))
        if a and b: add(x["date"], a / b, "面額變更")
    dv = {d: math.prod(f for f, _ in v) for d, v in ca.items()}
    CACHE[sid] = (px, dv); return CACHE[sid]
def valid(x): return x is not None and x["vol"] > 0 and x["open"] > 0 and x["close"] > 0
def prev_valid(px, d):
    i = CPOS[d] - 1
    while i >= 0:
        x = px.get(CAL[i])
        if valid(x): return x["close"], CPOS[d] - i
        i -= 1
    return None, 0
def locked(px, d):
    x = px[d]; pc, _ = prev_valid(px, d)
    if not (x["open"] == x["max"] == x["min"] == x["close"] and pc): return ""
    ch = x["close"] / pc - 1
    return "漲停" if ch >= limit(d) - 0.005 else ("跌停" if ch <= -limit(d) + 0.005 else "")
def jump_between(px, dv, i0, i1):
    for k in range(i0 + 1, i1 + 1):
        d = CAL[k]; x = px.get(d)
        if not valid(x) or d in dv: continue
        p0, n = prev_valid(px, d)
        up = (1 + limit(d)) ** n - 1 + 0.015; dn = 1 - (1 - limit(d)) ** n + 0.015
        if p0 and any(v / p0 - 1 > up or 1 - v / p0 > dn for v in (x["open"], x["close"])): return (d, p0, x["open"], x["close"])
    return None
def factor(dv, i0, i1):
    f = 1.0
    for k in range(i0 + 1, i1 + 1): f *= dv.get(CAL[k], 1.0)
    return f
def pool(sid, Ed, px):
    p = PER.get(sid)
    e = Ed.replace("-", "")
    if p:
        if p["初次上市櫃日"] and e < p["初次上市櫃日"]: return "排除：E 未上市櫃（興櫃／公開發行）", ""
        if p["終止上市櫃日"] and e > p["終止上市櫃日"]: return "排除：E 已終止上市櫃", ""
        return "", p["終止上市櫃日"]
    i = CPOS[Ed]; ok = 0
    for k in range(max(0, i - 20), i):
        x = px.get(CAL[k])
        if not valid(x): continue
        p0, n = prev_valid(px, CAL[k])
        if not p0 or not (x["min"] - 1e-9 <= x["open"] <= x["max"] + 1e-9) or abs(x["close"] / p0 - 1) > (1 + limit(CAL[k])) ** n - 1 + 0.005: return "排除：期間表無此代號且價格不符上市櫃漲跌幅（推定興櫃）", ""
        ok += 1
    if ok < 5: return "排除：期間表無此代號且 E 前有效交易日不足（推定非上市櫃）", ""
    last = max((d for d, x in px.items() if valid(x)), default="")
    return "", ("" if last >= CAL[-30] else last.replace("-", ""))
EV = pd.read_csv(EVF, dtype=str, keep_default_na=False)
T = []
for _, r in EV.iterrows():
    sid = r["公司代號"]; Ed = r["E"]; t = {"r": r.to_dict(), "E": Ed, "H": {}}
    if not Ed or Ed not in CPOS: t["excl"] = "E 不在市場日曆／資料終點後"; T.append(t); continue
    px, dv = stock(sid)
    why, end = pool(sid, Ed, px)
    t["推定上市櫃"] = sid not in PER
    if why: t["excl"] = why; T.append(t); continue
    end = iso(end) if end else ""
    en = px.get(Ed)
    if not valid(en):
        t["entry_fail"] = "進場日無有效開盤（%s）" % ("無資料／停牌" if en is None else f"成交量{en['vol']:.0f}、開盤{en['open']}"); T.append(t); continue
    t["open"] = en["open"]; t["entry_lock"] = locked(px, Ed); t["open_outside"] = not (en["min"] - 1e-9 <= en["open"] <= en["max"] + 1e-9)
    # 公告前最後收盤 → 進場開盤 跳空（描述用）
    S = iso(r["S"]); pre = S if (S in CPOS and r["時間"].zfill(6) >= "133000") else (CAL[bisect.bisect_left(CAL, S) - 1] if bisect.bisect_left(CAL, S) > 0 else None)
    pc = px.get(pre) if pre else None
    t["gap"] = (en["open"] * factor(dv, CPOS[pre], CPOS[Ed]) / pc["close"] - 1) if (pre and valid(pc)) else None
    mk = IDX["TAIEX" if (sid in TWSE or PER.get(sid, {}).get("終止日來源", "") == "證交所終止上市清單") else "TPEx"]   # 大盤對照（描述用）
    ei = CPOS[Ed]
    for H in HS:
        xi = ei + H - 1
        if xi >= len(CAL): t["H"][H] = {"status": "未完成（預定出場日晚於資料終點）"}; continue
        sched = CAL[xi]; act = None; j = xi
        while j < len(CAL):
            d = CAL[j]
            if end and d > end: break
            if valid(px.get(d)): act = d; break
            j += 1
        h = {"sched": sched}
        if act is None:
            last = next((CAL[k] for k in range(min(j, len(CAL)) - 1, ei - 1, -1) if valid(px.get(CAL[k]))), None)
            h["status"] = "未結案：" + (f"{end} 終止上市櫃前無可成交日" if end and j < len(CAL) else "停牌至資料終點仍無有效收盤")
            if last:
                jp = jump_between(px, dv, ei, CPOS[last])
                if not jp:
                    g = px[last]["close"] * factor(dv, ei, CPOS[last]) / en["open"] - 1
                    h["sens"] = {"exit": last, "ret": g, "hold": CPOS[last] - ei + 1}
            t["H"][H] = h; continue
        jp = jump_between(px, dv, ei, CPOS[act])
        if jp: h["status"] = f"未解決：{jp[0]} 跳價（前收 {jp[1]}→開 {jp[2]}／收 {jp[3]}）疑似公司行動未核對"; t["H"][H] = h; continue
        g = px[act]["close"] * factor(dv, ei, CPOS[act]) / en["open"] - 1
        ia, ib = mk.get(Ed), mk.get(act)
        h.update(status=("正常" if act == sched else f"出場順延（預定 {sched} 無有效收盤）"), exit=act, close=px[act]["close"], f=factor(dv, ei, CPOS[act]), ret=g,
                 hold=CPOS[act] - ei + 1, exit_lock=locked(px, act), mk=((ib["close"] / ia["open"] - 1) if ia and ib and ia["open"] > 0 else None))
        h["sens"] = {"exit": act, "ret": g, "hold": h["hold"]}
        # 可成交口徑：出場日一字鎖板且方向不利 → 順延至第一個非該鎖板的有效收盤日
        for side, block in (("long", "跌停"), ("short", "漲停")):
            a2 = act; note = ""
            if locked(px, a2) == block:
                k = CPOS[a2] + 1; a2 = None
                while k < len(CAL):
                    d = CAL[k]
                    if end and d > end: break
                    if valid(px.get(d)) and locked(px, d) != block: a2 = d; break
                    k += 1
                note = f"出場日一字{block}，順延至 {a2}" if a2 else f"出場日一字{block}，順延後無可成交日"
            if a2 is None or jump_between(px, dv, CPOS[act], CPOS[a2]): h[side] = {"status": note or "順延期間跳價未解決", "ret": None}; continue
            g2 = px[a2]["close"] * factor(dv, ei, CPOS[a2]) / en["open"] - 1
            h[side] = {"status": note or h["status"], "exit": a2, "ret": g2 if side == "long" else -g2, "hold": CPOS[a2] - ei + 1}
        t["H"][H] = h
    T.append(t)
pickle.dump(T, open("T031.pkl", "wb"))
c = lambda f: sum(1 for t in T if f(t))
print("事件", len(T), "排除", c(lambda t: "excl" in t), "進場失敗", c(lambda t: "entry_fail" in t), "開盤在高低外", c(lambda t: t.get("open_outside")))
