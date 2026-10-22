# 029 步驟2：細分類、集團內部判定、後續公告判定、標的鍵、損益解析、串鏈、180日去重、上市櫃期間過濾 → A／B 訊號
import pandas as pd, re, json, csv, sys, datetime as dt
sys.path.insert(0, "."); from gainparse import field, parse
REPO = sys.argv[1]
c = pd.read_pickle("c1.pkl")
# ---- 上市櫃名單（簡稱、全名、產業）----
L = json.load(open(f"{REPO}/listing/twse_L.json")); O = json.load(open(f"{REPO}/listing/tpex_O.json"))
NAMES = {}; FIN = set()
for x in L:
    NAMES[x["公司代號"]] = {x["公司簡稱"].strip(), re.sub(r"股份有限公司$", "", x["公司名稱"].strip())}
    if x["產業別"] == "17": FIN.add(x["公司代號"])
for x in O:
    NAMES[x["SecuritiesCompanyCode"]] = {x["CompanyAbbreviation"].strip(), re.sub(r"股份有限公司$", "", x["CompanyName"].strip())}
    if x["SecuritiesIndustryCode"] == "17": FIN.add(x["SecuritiesCompanyCode"])
for code, nm in c.groupby("公司代號")["公司名稱"].agg(lambda s: set(s.dropna())).items():
    NAMES.setdefault(code, set()).update(nm)
FINRE = r"金控|金融控股|銀行|人壽|產險|保險|證券|票券|投信|期貨|商銀"
def is_fin(code, name): return code in FIN or bool(re.search(FINRE, name or ""))
NAME2CODE = {}
for code, ns in NAMES.items():
    for n in ns:
        if len(n) >= 3: NAME2CODE.setdefault(n, set()).add(code)
PER = {r["公司代號"]: r for r in csv.DictReader(open(f"{REPO}/listing/上市櫃期間表.csv", encoding="utf-8-sig"))}
# ---- 細分類修正 ----
keep = c["排除原因"] == ""
txt = c["主旨標的"]
fix_eq = (c["排除原因"].str.startswith("待核")) & txt.str.contains(r"孫公司|子公司.*(?:股|出資|讓售|處分|出售)$|喪失控制|大陸投資|轉投資|投資事業|處分.*公司$")
fix_ot = (c["排除原因"].str.startswith("待核")) & txt.str.contains(r"貨櫃|貨輪|散裝|輪一艘|船|經營權|營業讓與|事業群|業務")
c.loc[fix_eq, ["資產類型", "排除原因"]] = ["股權投資", ""]
c.loc[fix_ot & ~fix_eq, ["資產類型", "排除原因"]] = ["其他資產", ""]
# 金融業者處分有價證券（非子公司股權、非不動產）＝例行投資交易
fin = c.apply(lambda r: is_fin(r["公司代號"], r["公司名稱"]) or bool(re.search(FINRE, r["主旨"][:25])), axis=1)
sub_eq = txt.str.contains(r"(處分|出售|讓售|轉讓|釋出).{0,20}(子公司|孫公司)|喪失控制|長期股權投資|100%")
c.loc[(c["排除原因"] == "") & fin & (c["資產類型"] == "股權投資") & ~sub_eq, "排除原因"] = "例行金融交易：金融業者處分有價證券"
# 股權細分：上市櫃股票 vs 非上市股權／子公司股權（文字規則）
def eq_sub(s):
    if re.search(r"子公司|孫公司|喪失控制|轉投資|出資額|有限公司.*股權|股權.*%|大陸投資|合資", s): return "非上市股權／子公司股權"
    if re.search(r"普通股股票|股票|普通股|集中(交易)?市場|櫃檯買賣|鉅額|盤後|釋股", s): return "上市櫃股票（文字推定）"
    return "非上市股權／子公司股權"
c["股權細分"] = ""
m = c["資產類型"] == "股權投資"; c.loc[m, "股權細分"] = c.loc[m, "主旨標的"].apply(eq_sub)
# 後續公告類型
FOLLOW = r"不繼續|停止執行|撤銷|補充|更正|更新|補正|變更|修正|完成|交割|後續|進度|取消|終止|解除|延長|延期|續報|說明|本次.*價格|釋股價格|仲裁|收到.*款|結案|追認|已決定"
c["後續公告"] = c["主旨"].str.contains(FOLLOW)
# 集團內部移轉
def cparty(s):
    m = re.search(r"交易相對人(?:及其)?與公司之關係[^:：\n]*(?:\n[^:：\n]*)?[:：][ \t]*\n?(.*?)(?=\n\s*\d{1,2}\s*[.．、]|\Z)", s, re.S)
    if m: return re.sub(r"\s+", "", m.group(1))[:200]
    m = re.search(r"與交易標的公司之關係[:：][ \t]*\n?(.*?)(?=\n\s*\d{1,2}\s*[.．、]|\Z)", s, re.S)
    return ("標的公司關係:" + re.sub(r"\s+", "", m.group(1))[:120]) if m else ""
c["交易相對人"] = c["說明"].apply(cparty)
INT = r"(本公司|母公司)?(之)?(100%|百分之百|全資)?(子公司|孫公司|母公司|曾孫公司)|同一集團|集團內|關係企業|聯屬公司|組織(架構)?重整|架構調整"
def internal(r):
    cp = r["交易相對人"]; s = r["主旨"]
    hit = (not cp.startswith("標的公司關係") and re.search(INT, cp) and not re.search(r"非(本公司)?(之)?(關係人|子公司)", cp[:15])) \
          or re.search(r"(子公司|孫公司|本公司).{0,30}(向|予|給|讓與|轉讓予|售予).{0,20}(子公司|孫公司|母公司)|集團內|組織重整|架構調整", s)
    if not hit: return ""
    other = [code for n, codes in NAME2CODE.items() if n in cp for code in codes if code != r["公司代號"]]
    return ("集團內部但交易對方為其他上市櫃公司（保留，Ed 10/22）：" + "/".join(sorted(set(other))[:3])) if other else "集團內部移轉（排除）"
c["集團內部"] = c.apply(internal, axis=1)
c.loc[(c["排除原因"] == "") & (c["集團內部"] == "集團內部移轉（排除）"), "排除原因"] = "集團內部移轉"
# 損益
c["損益欄位"] = c["說明"].apply(field)
P = c["損益欄位"].apply(parse).apply(pd.Series); P.columns = ["損益_" + x for x in P.columns]
c = pd.concat([c, P], axis=1)
c["量化損益"] = c["損益_狀態"].isin(["單一數值", "區間", "零"])
c["FVOCI_不進損益"] = c["損益欄位"].fillna("").str.contains(r"股東權益|保留盈餘|未分配盈餘|其他綜合損益|不影響損益|不列入損益")
c["歸屬層級"] = c["主旨"].str.contains(r"代.{0,12}(子公司|孫公司)|子公司.{0,20}公告").map({True: "子公司層級", False: "本公司"})
# 標的鍵
STRIP = r"股份有限公司|有限公司|\(股\)公司|（股）公司|股份|公司|普通股|特別股|股票|股權|持股|出資額|本公司|子公司|孫公司|代|公告|處分|出售|讓售|轉讓|決議|董事會|部分|全部|之|所持有|持有|案|事宜|相關|資訊|[「」『』\"\s\d%.,，、()（）]|百分之\S+|英屬|開曼|維京|薩摩亞"
def tkey(r):
    s = r["標的"] or ""; subj = r["主旨"]
    if r["資產類型"] == "不動產":
        for src in (s, subj):
            m = re.search(r"([一-鿿]{1,5}段)", src) or re.search(r"([一-鿿]{1,4}(?:路|街|大道))", src) or re.search(r"([一-鿿]{2}(?:區|鄉|鎮))", src)
            if m: return "不動產:" + m.group(1)
        return "不動產:未識別"
    if r["資產類型"] == "股權投資":
        src = s if s else subj
        m = re.search(r"(?:處分|出售|讓售|轉讓|釋出)(.{2,40}?)(?:之?(?:普通股|股票|股權|股份|特別股|出資額))", subj)
        name = m.group(1) if m else src
        k = re.sub(STRIP, "", name)[:6]
        return "股權:" + (k or "未識別")
    return r["資產類型"] + ":" + ("船" if re.search("船|輪", r["主旨標的"]) else ("設備" if re.search("設備|機器|模具|產線", r["主旨標的"]) else "其他"))
c["標的鍵"] = c.apply(tkey, axis=1)
c["發言時間"] = c["發言時間"].fillna("0").str.zfill(6)
c = c.sort_values(["公司代號", "發言日期", "發言時間"]).reset_index(drop=True)
c.to_pickle("c2.pkl")
k = c[c["排除原因"] == ""]
print("保留公告", len(k)); print(k["資產類型"].value_counts().to_string()); print(k["股權細分"].value_counts().to_string())
print("後續公告", k["後續公告"].sum(), "｜量化損益", k["量化損益"].sum(), "｜子公司層級", (k["歸屬層級"] == "子公司層級").sum())
print(k["損益_狀態"].value_counts().to_string()); print(c["集團內部"].value_counts().to_string())
print(c["排除原因"].value_counts().to_string())
