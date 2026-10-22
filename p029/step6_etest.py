# 029 E-Test（不構成正式結論）
# E-Test-1（Ed 2026-10-22 同意比照 024／026／027）：依公告時段提前進場
#   盤前（S 為交易日且公告時間 < 09:00）：S 當日開盤進場，第 S+(H−1) 交易日收盤出場；持有 H 日。
#   盤中（S 為交易日且 09:00 ≤ 公告時間 < 13:25）：S 當日收盤進場，S 後第 H 個交易日收盤出場；持有 H+1 日（含進場日）。
#   盤後（13:25 後）、非交易日公告：與正式版相同，列正式版對照。
# E-Test-2（2026-10-22 告知 Ed 後執行）：利益占市值分組 × 「進場日 E 開盤是否在漲停價」；E 開盤進場，多空皆列，H＝1、2、3、5。
#   開在漲停價＝E 開盤 ÷ 參考價（前一有效收盤 ÷ 當日除權息因子）− 1 ≥ 當時漲幅限制 − 0.5 個百分點；開盤當下即可觀察。
# 可成交口徑同正式版：多方進場一字漲停／空方進場一字跌停 → 取消；出場遇不利一字鎖板 → 順延至第一個非該鎖板之有效收盤。
import sys, collections, csv
from statistics import median
import step4_backtest as B  # 需以 step4 相同參數執行：DATA REPO 事件表
from bt_stats import summarize
EV = B.EV[B.EV["主樣本排除原因"] == ""]
A_S = B.EV[B.EV["路線"] == "A"].set_index("事件ID")["訊號公告日S"].to_dict()
def slot(r):
    S = B.iso(r["訊號公告日S"]); t = r["公告時間"].zfill(6)
    if S not in B.CPOS: return "非交易日公告"
    if t < "090000": return "盤前"
    if t < "132500": return "盤中"
    return "盤後"
def run(sid, ei, field, H, extra, side):
    """回傳 dict(ret, hold, entry, exit, note) 或 (None, 原因)"""
    px, dv, _, _ = B.stock(sid); Ed = B.CAL[ei]; en = px.get(Ed)
    if not B.valid(en): return None, "進場日無有效價"
    lk = B.locked(px, Ed)
    if side == "long" and lk == "漲停": return None, "做多進場日一字漲停（取消）"
    if side == "short" and lk == "跌停": return None, "放空進場日一字跌停（取消）"
    block = "跌停" if side == "long" else "漲停"
    xi = ei + H - 1 + extra
    if xi >= len(B.CAL): return None, "未完成"
    end = B.PER.get(sid, {}).get("終止上市櫃日", ""); end = B.iso(end) if end else ""
    j = xi; act = None; note = ""
    while j < len(B.CAL):
        d = B.CAL[j]
        if end and d >= end: break
        x = px.get(d)
        if B.valid(x):
            if B.locked(px, d) == block: note = f"出場遇一字{block}順延"
            else: act = d; break
        j += 1
    if act is None and end and j < len(B.CAL) and B.CAL[j] >= end:   # 順延期間已終止上市櫃：以最終交易日收盤結算（同正式版）
        act = next((B.CAL[k] for k in range(j - 1, ei, -1) if B.valid(px.get(B.CAL[k]))), None)
        if act is not None and B.locked(px, act) == block: return None, f"下市前最終交易日一字{block}，無可成交價"
        note = f"下市（{end}）前以最終交易日收盤結算"
    if act is None: return None, "出場無可成交價"
    for k in range(ei + 1, B.CPOS[act] + 1):
        d = B.CAL[k]; x = px.get(d)
        if not B.valid(x) or d in dv: continue
        p0, n, _ = B.prev_valid(px, d)
        up = (1 + B.limit(d)) ** n - 1 + 0.015; dn = 1 - (1 - B.limit(d)) ** n + 0.015
        if p0 and any(v / p0 - 1 > up or 1 - v / p0 > dn for v in (x["open"], x["close"])): return None, "跳價未解決"
    f = 1.0
    for k in range(ei + 1, B.CPOS[act] + 1): f *= dv.get(B.CAL[k], 1.0)
    g = px[act]["close"] * f / en[field] - 1
    return {"ret": g if side == "long" else -g, "hold": B.CPOS[act] - ei + 1, "entry": Ed, "exit": act, "note": note}, ""
def open_at_limit_up(sid, ei):
    px, dv, _, _ = B.stock(sid); Ed = B.CAL[ei]; en = px.get(Ed)
    pc, n, pd_ = B.prev_valid(px, Ed)
    if not B.valid(en) or not pc: return None
    ref = pc / dv.get(Ed, 1.0)
    return en["open"] / ref - 1 >= B.limit(Ed) - 0.005
# ---------- 明細 ----------
T = {}
import pickle
for t in pickle.load(open("T029.pkl", "rb")): T[(t["r"]["事件ID"], t["r"]["路線"])] = t
D1, D2 = [], []
for _, r in EV.iterrows():
    sid = r["公司代號"]; side_ = B.chain_side(A_S.get(r["事件ID"], r["訊號公告日S"])); S = B.iso(r["訊號公告日S"])
    t = T.get((r["事件ID"], r["路線"]))
    Ei = B.CPOS.get(B.iso(r["進場日E"]))
    sl = slot(r)
    for H in (1, 2, 3, 5, 10, 20, 40):
        for side in ("long", "short"):
            if sl == "盤前": res, why = run(sid, B.CPOS[S], "open", H, 0, side); ver = "E-Test-1：S 開盤進場"
            elif sl == "盤中": res, why = run(sid, B.CPOS[S], "close", H, 1, side); ver = "E-Test-1：S 收盤進場"
            else: res, why = None, "同正式版"; ver = "同正式版"
            frm, why2 = run(sid, Ei, "open", H, 0, side) if Ei is not None else (None, "無E")
            D1.append({"事件ID": r["事件ID"], "路線": r["路線"], "公司代號": sid, "S": r["訊號公告日S"], "公告時間": r["公告時間"], "時段": sl, "樣本側": side_,
                       "H": H, "方向": "做多" if side == "long" else "放空(假設成交)", "E-Test版本": ver,
                       "E-Test進場日": res["entry"] if res else "", "E-Test出場日": res["exit"] if res else "", "E-Test報酬": res["ret"] if res else "",
                       "E-Test持有日數": res["hold"] if res else "", "E-Test備註／未計原因": (res["note"] if res else why),
                       "正式版進場日": frm["entry"] if frm else "", "正式版報酬(對照)": frm["ret"] if frm else "", "正式版持有日數": frm["hold"] if frm else "",
                       "正式版備註／未計原因": (frm["note"] if frm else why2)})
            if H in (1, 2, 3, 5) and t is not None and Ei is not None:
                ol = open_at_limit_up(sid, Ei)
                D2.append({"事件ID": r["事件ID"], "路線": r["路線"], "公司代號": sid, "S": r["訊號公告日S"], "樣本側": side_, "H": H,
                           "方向": "做多" if side == "long" else "放空(假設成交)", "利益占市值分組": t["市值分組"] if t["損益分組"] == "明確利益" and t["稅別組"] != "稅後" else ("（非明確利益或稅後）"),
                           "E開盤在漲停價": "" if ol is None else ("是" if ol else "否"), "進場日E": frm["entry"] if frm else "",
                           "出場日": frm["exit"] if frm else "", "報酬": frm["ret"] if frm else "", "持有日數": frm["hold"] if frm else "", "備註／未計原因": frm["note"] if frm else why2})
def dedup(rows, key_e):
    seen, out = set(), []
    for d in sorted(rows, key=lambda d: (d["S"], d.get("公告時間", ""), d["事件ID"])):
        k = (d["公司代號"], d[key_e])
        if k in seen: continue
        seen.add(k); out.append(d)
    return out
def stat(xs, hd, ds, **kw):
    if len(xs) < 2: return None
    s = dict(summarize(xs, hold_days=hd, cluster=ds, cluster_unit="進場日")); s.update(kw); s["中位數"] = median(xs); return s
SAMP = [("全期", lambda d: True), ("樣本內(≤2020-10)", lambda d: d["樣本側"] == "樣本內"), ("樣本外(≥2021)", lambda d: d["樣本側"] == "樣本外"), ("最新年度(2026)", lambda d: d["S"][:4] == "2026")]
out1 = []
for route in ("A", "B"):
    for sl in ("盤前", "盤中", "盤後", "非交易日公告"):
        for sname, sf in SAMP:
            for H in (1, 2, 3, 5, 10, 20, 40):
                for dirn in ("做多", "放空(假設成交)"):
                    ds = [d for d in D1 if d["路線"] == route and d["時段"] == sl and d["H"] == H and d["方向"] == dirn and sf(d)]
                    for ver, key, hk, ek in (("E-Test-1", "E-Test報酬", "E-Test持有日數", "E-Test進場日"), ("正式版(對照)", "正式版報酬(對照)", "正式版持有日數", "正式版進場日")):
                        if ver == "E-Test-1" and sl in ("盤後", "非交易日公告"): continue
                        xs = dedup([d for d in ds if d[key] != ""], ek)
                        s = stat([d[key] for d in xs], [d[hk] for d in xs], [d[ek] for d in xs], 路線=route, 時段=sl, 樣本=sname, 版本=ver, 口徑=dirn, 持有H=H)
                        if s: out1.append(s)
out2 = []
for route in ("A", "B"):
    for grp in ("≥5%", "1%～未滿5%", "<1%", "無法比較", "（非明確利益或稅後）"):
        for ol in ("否", "是"):
            for sname, sf in SAMP:
                for H in (1, 2, 3, 5):
                    for dirn in ("做多", "放空(假設成交)"):
                        xs = dedup([d for d in D2 if d["路線"] == route and d["利益占市值分組"] == grp and d["E開盤在漲停價"] == ol and d["H"] == H and d["方向"] == dirn and d["報酬"] != "" and sf(d)], "進場日E")
                        s = stat([d["報酬"] for d in xs], [d["持有日數"] for d in xs], [d["進場日E"] for d in xs], 路線=route, 利益占市值=grp, E開盤在漲停價=ol, 樣本=sname, 口徑=dirn, 持有H=H)
                        if s: out2.append(s)
C = ["樣本數", "平均報酬", "平均持有交易日數", "單利年化", "勝率", "賠率R", "凱利", "半凱利", "標準差", "t值", "雙尾p", "聚合單位", "聚合單位數", "單位最大筆數", "聚合t", "聚合p", "中位數", "N/A原因", "bt_stats版本"]
for fn, rows, lead in (("029_ETest1_公告時段_全表_V01_R01.csv", out1, ["路線", "時段", "樣本", "版本", "口徑", "持有H"]),
                       ("029_ETest2_開盤漲停濾網_全表_V01_R01.csv", out2, ["路線", "利益占市值", "E開盤在漲停價", "樣本", "口徑", "持有H"])):
    with open(fn, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(lead + C)
        for s in rows: w.writerow(["" if s.get(c) is None else s.get(c) for c in lead + C])
for fn, rows in (("029_ETest1_明細_V01_R01.csv", D1), ("029_ETest2_明細_V01_R01.csv", D2)):
    with open(fn, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print("E1", len(out1), "E2", len(out2), collections.Counter(d["時段"] for d in D1 if d["H"] == 1 and d["方向"] == "做多"))
