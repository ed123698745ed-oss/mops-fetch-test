# 策略025「重大合約與授權終止後價格反應」判讀規則 R1（凍結於查看任何報酬之前）
# 依據：策略卡 V01 第 6～8 節；Ed 2026-10-13（工程合約納入但單獨標記）；Ed 2026-10-19（照 Elon 建議的邊界）
# 原則：只看首次公告當時的主旨與說明文字，不使用任何後續資料或報酬。
# 本檔是「規則」；無法用規則處理的個案，以 overrides_025.csv 逐筆覆寫並記錄理由（見 run_025.py）。
import re

RULE_VERSION = "R1.1"   # R1.1(2026-10-20 Ed)：股務代理改為排除

def norm(s):
    """主旨常被換行切斷字詞（如「股\n權」），一律去除空白與換行再比對"""
    import unicodedata
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", s or ""))   # R1.1：NFKC 統一異體字(如康熙部首「⼟」→「土」)

# ───────── 第一階段：候選（找可能的終止類公告）─────────
TERM = re.compile(r"終止|解除|不續約|不再續約|不予續約|提前結束|提前終止|屆期不續|返還")
OBJ = re.compile(r"合約|契約|協議|合作|授權|訂單|經銷|代理|供貨|採購|備忘錄|意向書|MOU", re.I)

def is_candidate(subj, body):
    subj, body = norm(subj), norm(body)
    hit_subj = bool(TERM.search(subj) and OBJ.search(subj))
    hit_body = bool(TERM.search(body) and OBJ.search(body)) and bool(TERM.search(subj))
    return hit_subj or hit_body

# ───────── 第二階段：排除類別（依序，第一個命中者為準；皆看主旨）─────────
# 卡上明列排除：正常履約完成、一般人事契約、可能終止/協商、傳聞、除權息/增減資/可轉債。
# 其餘為 Elon 補的邊界（Ed 2026-10-19 同意）：租約、不動產、股權/合資/併購/投資、融資、衍生性、臨床試驗、訴訟、專業服務委任。
LEASE = re.compile(r"租約|租賃|使用權資產")
CUSTOMER = re.compile(r"客戶|買主|主要供應商")          # MOPS「重要客戶/供應商停止往來」款項
# 公司名稱內含「工程/營造」者先剔除，避免把公司名稱誤當工程合約
ENG_NAME = re.compile(r"[^\s，。、（）()「」『』與及和之]{1,10}(?:工程|營造)(?:股份有限公司|\(股\)公司|（股）公司|有限公司|公司)")
ENG = re.compile(r"工程|營造|發包|承攬|統包|委建|興建|施工")
EXCLUDE_RULES = [
    ("競業禁止",       re.compile(r"競業|同業競爭")),
    ("集團內部合約",   re.compile(r"本公司與子公司|與子公司[^，。]{2,20}(?:終止|解除)|母子公司")),
    ("解除限制(非終止)", re.compile(r"解除.{0,15}限制")),
    ("可轉債/上市櫃",  re.compile(r"轉換公司債|可轉債|公司債|債券|贖回權|終止櫃檯|終止櫃買|終止上櫃|終止上市|終止其上市|特別股|興櫃|掛牌|創新板|下市|存託憑證|GDR|公開發行")),
    ("專業服務委任",   re.compile(r"會計師|簽證|輔導|承銷商|證券承銷")),
    ("人事/員工",      re.compile(r"經理人|董事長|總經理|執行長|獨立董事|解任|辭任|聘任|聘僱|勞動契約|僱傭|員工|職務|行員|發言人|主管|營運長|資訊安全長|職稱|之職")),
    ("股權/合資/併購/投資", re.compile(r"合資|合併|收購|併購|股份轉換|股份交換|換股|股權|股份買賣|股份受讓|受讓.*股份|認購|認股|增資|減資|私募|庫藏股|設立.*公司|投資案|有價證券|分割|"
                                      r"轉投資|共同投資|聯合投資|投資協議|投資契約|投資興建|大陸投資|赴.*投資|投資.*賭場|出資|終止投資|股利|資本公積|現金返還|理財產品|可終止式")),
    ("訴訟/仲裁",      re.compile(r"訴訟|起訴|提起|判決|裁定|仲裁|假扣押|民事|刑事|和解|反訴|訴請")),
    ("融資/保證",      re.compile(r"借款|聯貸|授信|融資|額度|背書|保證|票據|信託|聯合協議|清償|週轉|財務支援|資金貸與|資金融通|貸與|扣押")),
    ("衍生性商品",     re.compile(r"衍生性|期貨|選擇權|遠期|換匯|交換合約|避險")),
    ("臨床試驗",       re.compile(r"臨床|收案|試驗")),
    ("展延(非終止)",   re.compile(r"展延")),
    ("澄清(歸策略024)", re.compile(r"澄清|媒體報導")),
    ("洽談(無合約)",   re.compile(r"洽談")),
]
CODEV = re.compile(r"合建|共同(?:投資|合資)?興建|興建合作|合作興建|委託興建及都市更新|都市更新|土地合作|土地買賣|不動產買賣|房地買賣|不良債權|合宜住宅|招商|標售|BOT")
REALESTATE = re.compile(r"土地|不動產|合建|房地|房產|房屋|廠房|預售屋|地上權|地號|都市更新|城市更新|危老|重建|合作開發|開發案|合宜住宅|標售|招商|用地使用權|土地使用權|使用權出讓|BOT")
UNCERTAIN = re.compile(r"擬|預計|將於|洽談|協商|研議|評估|可能")
DEFINITE = re.compile(r"董事會決議|董事會通過|董事會已|已通知|已發函|函告|終止通知|已簽署|已終止|已解除|業已|合意終止|雙方同意")
ASSET = re.compile(r"處分|取得|機器設備|設備案|設備暨系統")
GENERIC = re.compile(r"^(?:公告|補充公告|更正)?(?:本公司|代子公司[^，與]{0,20})?(?:簽定|簽訂|簽署)?(?:之)?(?:重要)?(?:契約|合約)(?:終止|解除)(?:相關資料|公告|案|事宜)?[。]?$|^公告本公司終止重要合約$|^公告解除契約$|^公告本公司簽署終止合約$")
PARTNER_STOP = re.compile(r"(?:客戶|供應商).{0,6}(?:終止|停止).{0,4}往來|終止業務往來")
TRANSFER_AGENT = re.compile(r"股務代理|股務事務|股務業務")

# ───────── 第三階段：合約類型、終止時點、公司角色 ─────────
LICENSE = re.compile(r"授權|技術移轉|專利|權利金|商標|被授權|特許|license", re.I)
EARLY = re.compile(r"提前|期前|未屆|屆滿前|期限前|未到期|中途|違約|逾期")
NONRENEW = re.compile(r"不續約|不再續約|不予續約|屆期不續|期滿後不|屆滿後不|到期後不|到期不|屆期不再")

def role_of(subj, body):
    t = subj + norm(body)[:300]
    if re.search(r"被授權|取得.*授權", t): return "被授權方"
    if re.search(r"授權予|授權他人|授權方", t): return "授權方"
    if re.search(r"採購|發包|訂購|委建|委託.*(營造|廠商)", t): return "採購方"
    if re.search(r"經銷|代理|銷售|供貨|供應|代工", t): return "供貨/服務提供者"
    return "不明"

def classify(subj, body, h15="", h16=""):
    """回傳 dict：判讀(符合/符合-工程/符合-租賃出租方/排除/待人工)、類別、合約類型、終止時點、公司角色、規則備註"""
    subj, body = norm(subj), norm(body)
    out = {"判讀": "", "類別": "", "合約類型": "", "終止時點": "", "公司角色": "", "規則備註": ""}
    eng = bool(ENG.search(ENG_NAME.sub("", subj)))
    # 1. 租賃：出租方且為重要客戶 → 納入並標記；其餘租約排除
    if LEASE.search(subj):
        if CUSTOMER.search(subj):
            out.update(判讀="符合-租賃出租方", 類別="租賃出租方/重要客戶", 合約類型="商業合約",
                       規則備註="Ed 2026-10-19：納入，單獨標記")
            return _timing(out, subj, body)
        out.update(判讀="排除", 類別="租約/使用權資產"); return out
    # 2. 排除類別（工程承攬合約內含「合建」「融資」「投資興建」字樣者不因此排除）
    for name, rx in EXCLUDE_RULES:
        if rx.search(subj):
            if eng and name in ("股權/合資/併購/投資", "融資/保證"):
                continue
            out.update(判讀="排除", 類別=name); return out
    if CODEV.search(subj) or (REALESTATE.search(subj) and not eng and not LICENSE.search(subj)):
        out.update(判讀="排除", 類別="不動產/土地合建"); return out
    # 3. 需人工的情形
    if GENERIC.search(subj):
        out.update(判讀="待人工", 類別="主旨未載合約對象", 規則備註="需讀說明文字")
        return _timing(out, subj, body)
    if ASSET.search(subj) and not LICENSE.search(subj):
        out.update(判讀="排除", 類別="資產買賣(處分/取得)", 規則備註="Elon 補的邊界：資產買賣合約不屬商業合約/授權，待 Ed 確認")
        return out
    if UNCERTAIN.search(subj) and not DEFINITE.search(body[:800]):
        out.update(判讀="待人工", 類別="非確定/擬終止", 規則備註="卡 6：僅稱可能終止/協商者不納入；擬/預計需人工看是否為確定決議")
        return _timing(out, subj, body)
    # 4. 納入
    if PARTNER_STOP.search(subj):
        if re.search(r"租賃", body[:800]):
            out.update(判讀="符合-租賃出租方", 類別="租賃出租方/重要客戶", 合約類型="商業合約", 規則備註="MOPS「重要客戶/供應商終止往來」款項；說明為租賃合約到期不續約；Ed 2026-10-19：出租方納入並標記")
        else:
            out.update(判讀="符合", 類別="商業合約", 合約類型="商業合約", 規則備註="MOPS「重要客戶/供應商終止往來」款項")
        return _timing(out, subj, body)
    if TERM.search(subj) and OBJ.search(subj):
        if TRANSFER_AGENT.search(subj):
            out.update(判讀="排除", 類別="股務代理業務(服務契約)", 規則備註="Ed 2026-10-20：股務代理為公司付費的行政服務契約，不影響營收，不納入")
            return out
        elif eng:
            out.update(判讀="符合-工程", 類別="工程合約(發包方)", 合約類型="工程")
        elif LICENSE.search(subj) and re.search(r"經銷|代理|供貨|採購|銷售|訂單", subj):
            out.update(判讀="待人工", 類別="授權/商業混合", 合約類型="混合")
        elif LICENSE.search(subj):
            out.update(判讀="符合", 類別="技術與產品授權", 合約類型="技術與產品授權")
        else:
            out.update(判讀="符合", 類別="商業合約", 合約類型="商業合約")
        if re.search(r"備忘錄|意向書|MOU", subj):
            out["規則備註"] = (out["規則備註"] + "；" if out["規則備註"] else "") + "備忘錄/意向書(Ed 2026-10-19：納入並標記)"
        return _timing(out, subj, body)
    out.update(判讀="待人工", 類別="主旨未明示終止合約(僅說明文字命中)")
    return _timing(out, subj, body)

def _timing(out, subj, body):
    t = subj + body[:800]
    if NONRENEW.search(t): out["終止時點"] = "到期不續約"
    elif EARLY.search(t): out["終止時點"] = "提前終止"
    else: out["終止時點"] = "不明"
    out["公司角色"] = role_of(subj, body)
    return out
