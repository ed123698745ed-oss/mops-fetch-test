# 建立「上市櫃期間表」：每家公司初次上市櫃日～終止上市櫃日（不看重訊「市場別」欄位，該欄是現況）
# 來源優先序：官方(證交所/櫃買 openapi、證交所終止上市清單) > FinMind 下市清單 > 024 興櫃推定表 > 重訊公告文字證據
# 用法：python3 listing/build_periods.py  → listing/上市櫃期間表.csv
import json, csv, gzip, glob, re
N = lambda s: re.sub(r"\s+", "", s or "")
L = {d["公司代號"]: d["上市日期"] for d in json.load(open("listing/twse_L.json"))}
O = {d["SecuritiesCompanyCode"]: d["DateOfListing"] for d in json.load(open("listing/tpex_O.json"))}
def ad(s): y, m, d = s.split("/"); return f"{int(y)+1911}{m}{d}"
TWD = {x["Code"]: ad(x["DelistingDate"]) for x in json.load(open("delist/raw/twse_openapi_suspendListing.json"))}
FMD = {x["stock_id"]: x["date"].replace("-", "") for x in json.load(open("listing/delisting_finmind.json"))["data"]}
MANUAL_END = {"5326": ("20140901", "重訊『公告漢磊科技公司股票終止上櫃』(FinMind 缺)")}
P = {r["公司代號"]: r["推定興櫃末日(最後一筆異常開盤)"].replace("-", "") for r in csv.DictReader(open("listing/興櫃期間推定表_024.csv", encoding="utf-8-sig"))}
MIG = re.compile(r"上櫃轉上市|終止上櫃暨|終止上櫃及轉|初次上市暨終止上櫃|終止上櫃.{0,6}轉上市")   # 不可只用「轉上市」：興櫃轉上市也會命中
FIRST = re.compile(r"(初次上[市櫃]|上[市櫃]前).{0,12}(過額配售|承銷價格|收足股款)|過額配售|上櫃買賣日|上市買賣日")   # 只取掛牌前幾天的公告
BOND = re.compile(r"債")
FIRST_OTC = re.compile(r"(初次上櫃|上櫃前).{0,12}(過額配售|承銷價格|收足股款)|初次上櫃過額配售|上櫃買賣日")
mig, first_ev, first_otc, codes = set(), {}, {}, set()
for f in sorted(glob.glob("merged/MOPS每日重大訊息_公告總表_20*.csv.gz")):
    for r in csv.DictReader(gzip.open(f, "rt", encoding="utf-8-sig")):
        c = r["公司代號"]; codes.add(c); s = N(r["主旨"])
        if BOND.search(s): continue
        if MIG.search(s): mig.add(c)
        if FIRST.search(s) and "興櫃" not in s: first_ev.setdefault(c, []).append(r["發言日期"])
        if FIRST_OTC.search(s) and "興櫃" not in s and "上市" not in s: first_otc.setdefault(c, []).append(r["發言日期"])
def nxt(d):  # 推定興櫃末日的下一日視為上市櫃起日（近似）
    import datetime; x = datetime.datetime.strptime(d, "%Y%m%d") + datetime.timedelta(days=1); return x.strftime("%Y%m%d")
out = []
for c in sorted(codes | set(L) | set(O)):
    end, end_src = "", ""
    if c in TWD: end, end_src = TWD[c], "證交所終止上市清單"
    elif c in FMD: end, end_src = FMD[c], "FinMind下市清單"
    elif c in MANUAL_END: end, end_src = MANUAL_END[c]
    if c in L or c in O: end, end_src = "", ""          # 現仍上市櫃
    if c in O:
        first, src = O[c], "櫃買中心openapi上櫃日"
    elif c in L:
        if c in mig:
            if c in P: first, src = nxt(P[c]), "先上櫃後轉上市：024推定興櫃末日+1"
            elif c in first_otc and min(first_otc[c]) < L[c]: first, src = min(first_otc[c]), "先上櫃後轉上市：重訊初次上櫃公告日(近似)"
            else: first, src = "19000101", "先上櫃後轉上市：上櫃早於資料起點"
        else: first, src = L[c], "證交所openapi上市日"
    elif end:
        if c in P: first, src = nxt(P[c]), "已下市：024推定興櫃末日+1"
        elif c in first_ev: first, src = min(first_ev[c]), "已下市：重訊初次上市櫃公告日(近似)"
        else: first, src = "19000101", "已下市：上市櫃早於資料起點"
    else:
        continue   # 從未上市櫃（公開發行/興櫃）
    out.append([c, first, end, src, end_src])
w = csv.writer(open("listing/上市櫃期間表.csv", "w", encoding="utf-8-sig", newline=""))
w.writerow(["公司代號", "初次上市櫃日", "終止上市櫃日", "初次日來源", "終止日來源"]); w.writerows(out)
print("公司數", len(out), "已下市", sum(1 for x in out if x[2]))
