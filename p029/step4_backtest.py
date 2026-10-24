# 策略029「重大訊息－資產處分策略」V01／R01 正式回測（Elon，2026-10-22）
# 口徑依策略卡 V01 第 9～17 節及 Ed 2026-10-22 補正：
#  1. 進場日 E＝訊號公告日 S（台灣時間）之後第一個市場交易日（市場日曆＝加權指數有收盤之日）；E 開盤進場。
#     E 個股無有效開盤（無資料／成交量 0／開盤≤0）→ 列「進場無法成交」，不延後。
#  2. 出場：E 起第 H 個市場交易日收盤（H＝1,2,3,5,10,20,40；進場日算第 1 日）；當日無有效收盤 → 順延至第一個有效收盤日，記實際持有日數；
#     順延期間已終止上市櫃 → 以最終交易日收盤結算並標記；預定出場日晚於資料終點 → 未完成。
#  3. 報酬（R03，策略卡第 16 節實際現金流）＝（出場收盤 × 持股數 ＋ 持有期間收到的現金）÷ 進場開盤 − 1；放空＝−報酬（放空者付出同額現金股利，假設成交研究）。
#     持股數與現金依公司行動逐筆計算（進場日之後、出場日當天以前的除權息／減資／分割／面額變更日）：
#     現金股利：每股現金＝除息前收盤 − 除息參考價（FinMind TaiwanStockDividendResult「息」）；股票股利：持股 ×（除權前收盤 ÷ 除權參考價）；
#     含除權者：以 FinMind TaiwanStockDividend 拆成現金股利（盈餘＋公積）、股票股利（盈餘＋公積，元／股 ÷ 面額 10 元）與現金增資認購權，
#     並以參考價公式（前收盤 − 現金 ＋ 認購價 × 認購率）÷（1 ＋ 股票股利率 ＋ 認購率）核對，差 ≤1% 才採用，否則列「除權拆分不符」改用乘數；
#     現金增資認購權假設不認購（不投入新資金，認購權價值不計入報酬）；
#     現金減資：退還股款＝面額 10 元 × 減資比率 k，k＝（減資後參考價 − 減資前收盤）÷（減資後參考價 − 10），持股 ×（1 − k）；彌補虧損減資、分割、面額變更：持股 ×（前收盤 ÷ 參考價）。
#     R01／R02 曾用「前收盤 ÷ 參考價」乘數把現金股利當作再投資（Eve R02 複審 P1），R03 改正。
#  4. 持有期間（不含進場日）出現無法以公司行動解釋的跳價（與前一有效收盤相隔 n 日，超過 n 日累積漲跌停幅度＋1.5 個百分點）→ 列「未解決：疑似公司行動未核對」。
#  5. 進場日或出場日為一字價且達漲跌停 → 標記日線無法證明成交；理論價格樣本全列，另列可成交樣本。
#  6. 利益占市值＝訊號公告明示、可歸屬本公司之處分利益（約當台幣）÷（S 前一市場交易日收盤 × 該日已發行股數）。
#     外幣：公司揭露約當台幣優先；否則以 S 前最近一日台銀即期買賣中價換算（Ed 10/22：粗估）。代子公司公告之金額不換算為母公司利益（策略卡第 9 節）。
import csv, json, gzip, collections, datetime as dt, bisect, os, sys, re
from statistics import median
import pandas as pd
sys.path.insert(0, sys.argv[2])  # repo 路徑（bt_stats 1.0，與 Drive 原檔相同）
from bt_stats import summarize
DATA = sys.argv[1]               # out/p029
DIVDATA = os.environ.get("P029_DIVDATA") or os.path.join(os.path.dirname(DATA.rstrip("/")), "p029div")   # R03：TaiwanStockDividend（現金／股票股利拆分）
CF = {}                          # R03：公司行動現金流事件 {股票: {日期: [(類型, 持股乘數, 每股現金, 說明)]}}
def cashflow(sid, ei, xi):
    """進場日之後到出場日（含）的公司行動：回傳（持股數、每股原始持股累計現金、說明清單）"""
    s, C, notes = 1.0, 0.0, []
    for k in range(ei + 1, xi + 1):
        for typ, m, c, why in CF.get(sid, {}).get(CAL[k], []):
            C += s * c; s *= m; notes.append(f"{CAL[k]}{why}")
    return s, C, notes
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
IDX = {}
for k in ("TAIEX", "TPEx"):
    IDX[k] = {r["date"]: {"open": fl(r["open"]), "close": fl(r["close"])} for r in rcsv(f"{DATA}/_{k}_Price.csv.gz")}
CAL = sorted(d for d, r in IDX["TAIEX"].items() if r["close"] > 0); CPOS = {d: i for i, d in enumerate(CAL)}; DATA_END = CAL[-1]
REPO = sys.argv[2]
PER = {r["公司代號"]: r for r in csv.DictReader(open(f"{REPO}/listing/上市櫃期間表.csv", encoding="utf-8-sig"))}
def iso(s): return f"{s[:4]}-{s[4:6]}-{s[6:]}"
def limit(d): return 0.07 if d < "2015-06-01" else 0.10
PVC = {}
for x in rjson(f"{DATA}/_ParValueChange_all.json"): PVC.setdefault(x.get("stock_id"), []).append(x)
CACHE = {}
def stock(sid):
    if sid in CACHE: return CACHE[sid]
    px = {}
    for r in rcsv(f"{DATA}/{sid}_TaiwanStockPrice.csv.gz"):
        px[r["date"]] = {"open": fl(r["open"]), "max": fl(r["max"]), "min": fl(r["min"]), "close": fl(r["close"]), "vol": fl(r["Trading_Volume"])}
    ca = {}
    def add(d, f, why, ev=None):
        if d and f and f > 0 and abs(f - 1) > 1e-9:
            ca.setdefault(d, []).append((f, why)); CF.setdefault(sid, {}).setdefault(d, []).append(ev or ("share", f, 0.0, why))
    DIVX = {}                                      # 日期 → [現金股利, 股票股利比率, 現增認購比率, 認購價]
    for x in rjson(f"{DIVDATA}/{sid}_TaiwanStockDividend.json"):
        c = fl(x.get("CashEarningsDistribution")) + fl(x.get("CashStatutorySurplus")); st = fl(x.get("StockEarningsDistribution")) + fl(x.get("StockStatutorySurplus"))
        q, p = fl(x.get("CashIncreaseSubscriptionRate")) / 100.0, fl(x.get("CashIncreaseSubscriptionpRrice"))
        cd, sd = x.get("CashExDividendTradingDate"), x.get("StockExDividendTradingDate")
        if cd: DIVX.setdefault(cd, [0.0, 0.0, 0.0, 0.0])[0] += c
        if sd:
            v = DIVX.setdefault(sd, [0.0, 0.0, 0.0, 0.0]); v[1] += st / 10.0
            if q > 0 and p > 0: v[2] += q; v[3] = p
    for x in rjson(f"{DATA}/{sid}_TaiwanStockDividendResult.json"):
        a, b, kind = fl(x.get("before_price")), fl(x.get("after_price")), x.get("stock_or_cache_dividend", "")
        if not (a and b): continue
        if "權" not in kind:                       # 純現金股利：每股現金＝前收盤 − 參考價
            ev = ("cash", 1.0, a - b, "現金股利")
        else:                                       # 含除權：依 TaiwanStockDividend 拆成現金股利、股票股利、現金增資認購權
            c, r, q, p = DIVX.get(x["date"], [None, None, None, None])
            if c is not None and abs((a - c + p * q) / (1 + r + q) / b - 1) <= 0.01:
                why = "除權息（拆分）" + ("；現增除權不認購" if q > 0 else "")
                ev = ("cashshare", 1 + r, c, why)
            else: ev = ("share", a / b, 0.0, "除權拆分不符：改用乘數")
        add(x["date"], a / b, "除權息", ev)
    for x in rjson(f"{DATA}/{sid}_TaiwanStockCapitalReductionReferencePrice.json"):
        a, b = fl(x.get("ClosingPriceonTheLastTradingDay")), fl(x.get("PostReductionReferencePrice"))
        if not (a and b): continue
        why = x.get("ReasonforCapitalReduction", "")
        if why in ("Cash refund", "現金減資") and abs(b - 10) > 1e-9 and 0 < (b - a) / (b - 10) < 1:
            k = (b - a) / (b - 10); ev = ("cashshare", 1 - k, 10 * k, "現金減資（面額退還推算）")
        elif why in ("Cash refund", "現金減資"): ev = ("share", a / b, 0.0, "現金減資推算失敗：改用乘數")
        else: ev = ("share", a / b, 0.0, "減資（彌補虧損）")
        add(x["date"], a / b, "減資", ev)
    for x in rjson(f"{DATA}/{sid}_TaiwanStockSplitPrice.json"):
        a, b = fl(x.get("before_price")), fl(x.get("after_price"))
        if a and b: add(x["date"], a / b, "分割／合併")
    for x in PVC.get(sid, []):
        a, b = fl(x.get("before_close")), fl(x.get("after_ref_close") or x.get("after_ref_open"))
        if a and b: add(x["date"], a / b, "面額變更")
    dv = {d: __import__("math").prod(f for f, _ in v) for d, v in ca.items()}
    sh = {r["date"]: fl(r["NumberOfSharesIssued"]) for r in rcsv(f"{DATA}/{sid}_Shares.csv.gz") if fl(r["NumberOfSharesIssued"]) > 0}
    CACHE[sid] = (px, dv, sorted(sh.items()), ca)
    return CACHE[sid]
def valid(x): return x is not None and x["vol"] > 0 and x["open"] > 0 and x["close"] > 0
def prev_valid(px, d):
    i = CPOS[d] - 1
    while i >= 0:
        x = px.get(CAL[i])
        if valid(x): return x["close"], CPOS[d] - i, CAL[i]
        i -= 1
    return None, 0, None
def locked(px, d):
    """一字價且達漲跌停：回傳 "漲停"／"跌停"／""（日線無法證明成交的方向）"""
    x = px[d]; pc, _, _ = prev_valid(px, d)
    if not (x["open"] == x["max"] == x["min"] == x["close"] and pc is not None): return ""
    ch = x["close"] / pc - 1
    return "漲停" if ch >= limit(d) - 0.005 else ("跌停" if ch <= -limit(d) + 0.005 else "")
FX = {}
for f in os.listdir(DATA):
    m = re.match(r"_FX_(\w+)\.csv\.gz", f)
    if m:
        rows = []
        for r in rcsv(f"{DATA}/{f}"):
            sb, ss, cb, cs = fl(r["spot_buy"]), fl(r["spot_sell"]), fl(r["cash_buy"]), fl(r["cash_sell"])
            mid = (sb + ss) / 2 if sb > 0 and ss > 0 else ((cb + cs) / 2 if cb > 0 and cs > 0 else 0)
            if mid > 0: rows.append((r["date"], mid))
        FX[m.group(1)] = sorted(rows)
def fx_before(cur, S):  # S＝YYYYMMDD；取 S 之前最近一日
    rows = FX.get(cur) or []
    i = bisect.bisect_left(rows, (iso(S), 0)) - 1
    return (rows[i][1], rows[i][0]) if i >= 0 else (None, None)
# ---------------- 事件 ----------------
EV = pd.read_csv(sys.argv[3], dtype=str, keep_default_na=False)
def chain_side(aS):
    if aS <= "20201031": return "樣本內"
    if aS >= "20210101": return "樣本外"
    return "緩衝期（不列樣本內外）"
A_S = EV[EV["路線"] == "A"].set_index("事件ID")["訊號公告日S"].to_dict()
def twd(r):
    """回傳 (點值, 下限, 上限, 方法說明)，皆為約當新台幣；無法換算回傳 None"""
    cur = r["幣別"] or "TWD"
    if r["公司揭露約當台幣"]:
        v = float(r["公司揭露約當台幣"]); return v, None, None, "公司揭露約當台幣"
    if cur == "TWD": rate, rd, how = 1.0, "", "新台幣"
    else:
        rate, rd = fx_before(cur, r["訊號公告日S"]); how = f"{cur}×{rate}（台銀即期中價 {rd}，粗估）" if rate else ""
        if not rate: return None, None, None, f"{cur} 無訊號前匯率"
    pt = float(r["損益金額_原幣"]) * rate if r["損益金額_原幣"] else None
    lo = float(r["區間下限_原幣"]) * rate if r["區間下限_原幣"] else None
    hi = float(r["區間上限_原幣"]) * rate if r["區間上限_原幣"] else None
    return pt, lo, hi, how
def mktcap(sid, S):
    px, dv, sh, _ = stock(sid)
    i = bisect.bisect_left(CAL, iso(S)) - 1       # S 前一市場交易日
    if i < 0: return None, "無前一交易日"
    d = CAL[i]; x = px.get(d)
    if not valid(x): return None, f"{d} 無有效收盤"
    j = bisect.bisect_right(sh, (d, float("inf"))) - 1
    if j < 0: return None, "無已發行股數資料"
    if (dt.date.fromisoformat(d) - dt.date.fromisoformat(sh[j][0])).days > 10: return None, f"股數資料落後（{sh[j][0]}）"
    return x["close"] * sh[j][1], f"{d} 收盤 {x['close']} × 股數 {int(sh[j][1])}（{sh[j][0]}）"
def size_grp(v):
    return "<1%" if v < 0.01 else ("1%～未滿5%" if v < 0.05 else "≥5%")
def classify(r):
    st, d = r["損益狀態"], r["損益方向"]
    if st in ("單一數值", "區間", "零"):
        if d == "利益": g = "明確利益"
        elif d == "損失": g = "明確損失"
        elif d == "零": g = "零"
        else: g = "方向不明"
    else: g = "未知（未量化）"
    size, sizeinfo, ratio = "無法比較", "", None
    if g == "明確利益":
        if r["訊號公告歸屬層級"] != "本公司": sizeinfo = "代子公司公告，不換算母公司利益"
        else:
            pt, lo, hi, how = twd(r); mc, mcinfo = mktcap(r["公司代號"], r["訊號公告日S"])
            if mc is None: sizeinfo = "市值無法計算：" + mcinfo
            elif pt is not None: ratio = pt / mc; size = size_grp(ratio); sizeinfo = f"{how}；{mcinfo}"
            elif lo is not None and hi is not None:
                a, b = size_grp(lo / mc), size_grp(hi / mc)
                size = a if a == b else "金額分組不明（區間跨組）"; sizeinfo = f"區間 {lo:.0f}～{hi:.0f}；{how}；{mcinfo}"
            else: sizeinfo = "金額無法換算：" + how
    tax = "稅後" if r["稅別"] == "稅後" else "稅前（含推定）"
    return g, size, sizeinfo, ratio, tax
def main():
    global T
    T = []
    for _, r in EV[EV["主樣本排除原因"] == ""].iterrows():
        sid = r["公司代號"]; px, dv, sh, ca = stock(sid); Ed = iso(r["進場日E"])
        g, size, sizeinfo, ratio, tax = classify(r)
        base = {"r": r, "E": Ed, "H": {}, "side": chain_side(A_S.get(r["事件ID"], r["訊號公告日S"])), "損益分組": g, "市值分組": size, "市值說明": sizeinfo, "利益占市值": ratio, "稅別組": tax, "Ei": CPOS.get(Ed)}
        # 公告前收盤 → 進場開盤 跳空（描述用）
        t = r["公告時間"].zfill(6); S = iso(r["訊號公告日S"])
        if S in CPOS and t >= "133000": pre_d = S
        else:
            i = bisect.bisect_left(CAL, S) - 1; pre_d = CAL[i] if i >= 0 else None
        end = PER.get(sid, {}).get("終止上市櫃日", ""); end = iso(end) if end else ""
        if Ed not in CPOS: base["entry_fail"] = "進場日不在市場日曆"; T.append(base); continue
        en = px.get(Ed)
        if not valid(en):
            base["entry_fail"] = "進場日無有效開盤（%s）" % ("無資料" if en is None else f"成交量{en['vol']:.0f}、開盤{en['open']}"); T.append(base); continue
        pc = px.get(pre_d) if pre_d else None
        base["gap"] = (en["open"] / pc["close"] - 1) if valid(pc) else None
        if base["gap"] is not None and pre_d and CPOS[Ed] - CPOS[pre_d] >= 1:
            f = 1.0
            for k in range(CPOS[pre_d] + 1, CPOS[Ed] + 1): f *= dv.get(CAL[k], 1.0)
            base["gap"] = en["open"] * f / pc["close"] - 1
        base["open"] = en["open"]; base["entry_lock"] = locked(px, Ed)
        base["open_outside"] = not (en["min"] - 1e-9 <= en["open"] <= en["max"] + 1e-9)
        ei = CPOS[Ed]
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
                if end and (sched >= end or (j < len(CAL) and CAL[j] >= end)):
                    last = next((CAL[k] for k in range(min(j, len(CAL)) - 1, ei, -1) if valid(px.get(CAL[k]))), None)
                    if last: act, status = last, f"下市（{end}）前以最終交易日收盤結算"
                    else: base["H"][H] = {"status": f"未解決：{end} 終止上市櫃，持有期間無最終交易價", "sched": sched}; continue
                else:
                    base["H"][H] = {"status": "未完成（順延後仍無有效收盤，資料終點）", "sched": sched}; continue
            elif act != sched: status = f"出場順延（預定 {sched} 無有效收盤）"
            jump = None
            for k in range(ei + 1, CPOS[act] + 1):
                d = CAL[k]; x = px.get(d)
                if not valid(x) or d in dv: continue
                p0, n, _ = prev_valid(px, d)
                up = (1 + limit(d)) ** n - 1 + 0.015; dn = 1 - (1 - limit(d)) ** n + 0.015
                if p0 and any(v / p0 - 1 > up or 1 - v / p0 > dn for v in (x["open"], x["close"])): jump = (d, p0, x["open"], x["close"]); break
            if jump: base["H"][H] = {"status": f"未解決：{jump[0]} 跳價（前收 {jump[1]} → 開 {jump[2]}／收 {jump[3]}）疑似公司行動未核對", "sched": sched}; continue
            f = 1.0
            for k in range(ei + 1, CPOS[act] + 1): f *= dv.get(CAL[k], 1.0)
            sh_, cash_, ca_notes = cashflow(sid, ei, CPOS[act])
            ex = px[act]; g_ = (ex["close"] * sh_ + cash_) / en["open"] - 1
            mk_ = IDX["TPEx" if r["市場別_現值"] == "otc" else "TAIEX"]
            ia, ib = mk_.get(Ed), mk_.get(act)
            h = {"status": status, "sched": sched, "exit": act, "close": ex["close"], "f": f, "shares": sh_, "cash": cash_, "ca_notes": "；".join(ca_notes), "ret": g_,
                 "mk": (ib["close"] / ia["open"] - 1) if ia and ib and ia["open"] > 0 else None, "hold": CPOS[act] - ei + 1, "exit_lock": locked(px, act)}
            # 可成交口徑：出場日為一字鎖板且方向不利（多方遇一字跌停、空方遇一字漲停）→ 順延至第一個非該鎖板的有效收盤日
            for side, block in (("long", "跌停"), ("short", "漲停")):
                a2 = act; note = ""
                if locked(px, a2) == block:
                    k = CPOS[a2] + 1; a2 = None
                    while k < len(CAL):
                        d = CAL[k]
                        if end and d >= end: break
                        x = px.get(d)
                        if valid(x) and locked(px, d) != block: a2 = d; break
                        k += 1
                    note = f"出場日一字{block}，順延至 {a2}" if a2 else f"出場日一字{block}，順延後無可成交日"
                if a2 is None: h[side] = {"status": note, "ret": None}; continue
                bad = None
                for k in range(CPOS[act] + 1, CPOS[a2] + 1):
                    d = CAL[k]; x = px.get(d)
                    if not valid(x) or d in dv: continue
                    p0, n, _ = prev_valid(px, d)
                    up = (1 + limit(d)) ** n - 1 + 0.015; dn = 1 - (1 - limit(d)) ** n + 0.015
                    if p0 and any(v / p0 - 1 > up or 1 - v / p0 > dn for v in (x["open"], x["close"])): bad = d; break
                if bad: h[side] = {"status": f"順延期間 {bad} 跳價未解決", "ret": None}; continue
                s2, c2, n2 = cashflow(sid, ei, CPOS[a2])
                g2 = (px[a2]["close"] * s2 + c2) / en["open"] - 1; ib2 = mk_.get(a2)
                h[side] = {"status": note or status, "exit": a2, "ret": g2 if side == "long" else -g2, "hold": CPOS[a2] - ei + 1, "shares": s2, "cash": c2, "ca_notes": "；".join(n2),
                           "mk": ((ib2["close"] / ia["open"] - 1) if ia and ib2 and ia["open"] > 0 else None)}
            base["H"][H] = h
        T.append(base)

    import pickle; pickle.dump(T, open("T029.pkl", "wb"))
    print("交易事件", len(T), "進場失敗", sum("entry_fail" in t for t in T), "開盤落在高低外", sum(bool(t.get("open_outside")) for t in T))
if __name__ == "__main__": main()
