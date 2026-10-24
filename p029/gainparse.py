# 029 處分損益欄位解析（固定規則；無法解析者不推估）
import re, taxrule
CUR = [("TWD", r"新臺幣|新台幣|台幣|臺幣|NTD|NT\$|TWD|NT"), ("USD", r"美元|美金|USD|US\$|U\.S\.\$"), ("CNY", r"人民幣|RMB|CNY"),
       ("HKD", r"港幣|港元|HKD|HK\$"), ("JPY", r"日圓|日幣|日元|JPY"), ("EUR", r"歐元|EUR"), ("VND", r"越南盾|VND"), ("THB", r"泰銖|THB"),
       ("MYR", r"馬幣|令吉|MYR"), ("SGD", r"新加坡幣|新幣|SGD"), ("KRW", r"韓元|韓圜|KRW"), ("PHP", r"披索|PHP"), ("IDR", r"印尼盾|IDR"),
       ("GBP", r"英鎊|GBP"), ("AUD", r"澳幣|AUD"), ("INR", r"盧比|INR"), ("CAD", r"加幣|CAD"), ("CHF", r"瑞士法郎|瑞郎|CHF"), ("NZD", r"紐幣|NZD"), ("ZAR", r"南非幣|ZAR"), ("SEK", r"瑞典幣|SEK")]
UNIT = [(1e8, r"億"), (1e7, r"仟萬|千萬"), (1e6, r"百萬|佰萬|仟仟"), (1e4, r"萬"), (1e3, r"仟|千|K\b")]
def field(s):
    m = re.search(r"(?:預計|預估)?處分利益[（(]或損失[）)][^:：\n]*(?:\n[^:：\n]*)?[:：][ \t]*\n?(.*?)(?=\n\s*\d{1,2}\s*[.．、]|\Z)", s, re.S)
    if m: return m.group(1).strip()
    m = re.search(r"\d{1,2}\s*[.．、]\s*(?:預計)?處分(?:利益|損益|損失)[^:：\n]{0,30}[:：][ \t]*\n?(.*?)(?=\n\s*\d{1,2}\s*[.．、]|\Z)", s, re.S)
    return m.group(1).strip() if m else None
def compound(t):
    # 「31億3,100萬」「3億1仟5佰萬」「1億3千7百萬」→ 單一數字（元）；億以下的仟／佰若接「萬」，屬萬的倍數
    def wan(seg):
        seg = seg.replace(",", "")
        if re.fullmatch(r"\d+(?:\.\d+)?", seg): return float(seg)
        tot = 0.0
        for num, u in re.findall(r"(\d+(?:\.\d+)?)\s*(仟|千|佰|百|拾|十)?", seg):
            tot += float(num) * {"仟": 1000, "千": 1000, "佰": 100, "百": 100, "拾": 10, "十": 10, "": 1, None: 1}[u]
        return tot
    def rep(m):
        a, rest = m.group(1), m.group(2) or ""
        v = float(a.replace(",", "")) * 1e8
        if rest: v += wan(rest) * 1e4
        return f" {v:.0f}元 "
    t = re.sub(r"([\d,]+(?:\.\d+)?)\s*億\s*((?:[\d,]+(?:\.\d+)?\s*(?:仟|千|佰|百|拾|十)?\s*)+)萬", rep, t)
    # 「3仟9佰萬」「1千5百萬」→ (3000+900)×1 萬
    t = re.sub(r"(?<![\d,.])((?:\d+\s*(?:仟|千|佰|百|拾|十)\s*){2,}\d*)萬", lambda m: f" {wan(m.group(1)) * 1e4:.0f}元 ", t)
    return t
CN = {"零": 0, "〇": 0, "○": 0, "壹": 1, "一": 1, "貳": 2, "二": 2, "兩": 2, "參": 3, "叁": 3, "三": 3, "肆": 4, "四": 4, "伍": 5, "五": 5, "陸": 6, "六": 6, "柒": 7, "七": 7, "捌": 8, "八": 8, "玖": 9, "九": 9}
CU = {"拾": 10, "十": 10, "佰": 100, "百": 100, "仟": 1000, "千": 1000}
def cn2num(seg):
    total, sec, num = 0, 0, 0
    for ch in seg:
        if ch in CN: num = CN[ch]
        elif ch in CU: sec += (num or 1) * CU[ch]; num = 0
        elif ch == "萬": total += (sec + num) * 10000; sec = num = 0
        elif ch == "億": total += (sec + num) * 100000000; sec = num = 0
    return total + sec + num
def cnfix(t):
    return re.sub(r"(?<![\d,.])(?=[零〇○壹貳參叁肆伍陸柒捌玖]*[壹貳參叁肆伍陸柒捌玖])[零〇○壹貳參叁肆伍陸柒捌玖拾佰仟萬億]{2,}(?=\s*元)", lambda m: f" {cn2num(m.group(0))}元 ", t)
def clean(t):
    t = cnfix(t)
    t = re.sub(r"[\d,.]+\s*(?:仟|千|萬)?\s*(?:股|張|坪|平方|單位|戶|輛|艘)", " ", t)
    t = compound(t)
    t = re.sub(r"\d+(?:\.\d+)?\s*[~～至\-－]\s*\d+(?:\.\d+)?\s*%", " ", t)
    t = re.sub(r"\d{2,4}\s*[/／.年]\s*\d{1,2}\s*[/／.月]\s*\d{1,2}\s*日?", " ", t)      # 日期
    t = re.sub(r"\d{1,2}\s*月\s*\d{1,2}\s*日?|\d{1,2}\s*月份?", " ", t)
    t = re.sub(r"\d{2,4}\s*年(?:度|第?\d季|Q\d)?", " ", t); t = re.sub(r"\d+\s*%|百分之\S+", " ", t)
    t = re.sub(r"[（(]\s*\d\s*[)）]|第\s*\d+\s*[期季次項款條]|\d+\s*[股張筆坪平方]", " ", t)
    t = re.sub(r"Q\d|\d{3}Q\d|\(\d{3}Q\d\)", " ", t)
    t = re.sub(r"匯率\s*[:：為]?\s*[\d.]+|#\s*\d+|(?<![A-Za-z$])[A-Za-z]{1,6}\s*\d+(?![\d,.])|每股[^，,。；]{0,12}?\d+(?:\.\d+)?\s*元|\d+\s*地號|\b[A-Z]\.", " ", t)
    t = re.sub(r"第\s*\d+\s*(?:階段|批|次|筆|標|期)|[-－]{2}\s*\d{1,2}(?![\d,])|[\d,.]+\s*(?:仟|千|萬)?\s*(?:股|張|坪|平方|單位|戶|輛|艘)", " ", t)
    t = re.sub(r"(^|[\s。；;，,])\d{1,2}\s*[.．、](?!\d)", " ", t)
    return t
NUM = r"([-－−]?\s*\d[\d,，]*(?:\.\d+)?)"
def parse(t):
    """回傳 dict: 狀態, 正負, 幣別, 金額(原幣元), 下限, 上限, 預估實際, 稅別, 約當台幣(公司揭露), 疑義"""
    out = {"狀態": "", "方向": "", "幣別": "", "金額": None, "下限": None, "上限": None, "預估實際": "", "稅別": "", "公司揭露約當台幣": None, "疑義": ""}
    if t is None or not isinstance(t, str): out["狀態"] = "無損益欄位"; return out
    raw = t; t1 = re.sub(r"^\s*(?:預計)?處分利益[（(]或損失[）)][^:：]{0,20}[:：]", "", t.replace("\n", " "))
    if re.fullmatch(r"\s*(不適用|N/?A|na|－|-|無|尚無|—)\s*[。.]?\s*", t1, re.I): out["狀態"] = "不適用／無"; return out
    out["預估實際"] = "預估" if re.search(r"預計|預估|暫估|估計|估算|約", t1) else ("實際" if re.search(r"實際|已實現|認列|確定", t1) else "未明")
    out["稅別"] = taxrule.tax(t1)   # R03：Ed 2026-10-24「已扣除稅費」視為稅後（taxrule.py）
    if re.search(r"尚待|待.*(評估|估算|確定|計算)|尚未.*(確定|估算|評估)|無法.*(估|計算)|視.*而定|將依|另行公告|俟", t1) and not re.search(NUM, clean(t1)):
        out["狀態"] = "未量化（尚待估算等）"; return out
    c = clean(t1)
    tw = re.search(r"約當\s*(?:新臺幣|新台幣|台幣)?\s*" + NUM + r"\s*(仟|千|萬|百萬|佰萬|億)?\s*(?:新?台幣)?\s*元?", c)
    if tw:
        v = float(re.sub(r"[,，\s－−]", "", tw.group(1)).replace("－", "-")); mul = 1
        for m_, p in UNIT:
            if tw.group(2) and re.search(p, tw.group(2)): mul = m_; break
        out["公司揭露約當台幣"] = abs(v) * mul
        c = c[:tw.start()] + c[tw.end():]
    nums = [(m.start(), m.group(1)) for m in re.finditer(NUM, c)]
    vals = []
    for pos, s in nums:
        s2 = re.sub(r"[,，\s]", "", s).replace("－", "-").replace("−", "-")
        try: v = float(s2)
        except ValueError: continue
        after = c[pos + len(s): pos + len(s) + 6]; before = c[max(0, pos - 12): pos]
        mul = 1
        for m_, p in UNIT:
            if re.match(r"\s*[)）(（]?\s*(?:元)?\s*(?:" + p + ")", after) or re.search("(?:" + p + r")\s*元?\s*$", before): mul = m_; break
        cur = ""
        for code, p in CUR:
            if re.search(p, before[-8:], re.I): cur = code; break
        if not cur:
            for code, p in CUR:
                if re.search(p, after, re.I): cur = code; break
        vals.append((v * mul, cur, pos))
    if not vals:
        if re.search(r"無(處分)?(利益|損益|損失)|未產生|不產生|無損益|損益為零|無重大", t1): out.update(狀態="零", 方向="零", 金額=0.0, 幣別="TWD"); return out
        out["狀態"] = "未量化（無數字）"; return out
    if not re.search(r"利益|損失|損益|獲利|利得|淨利|收益|虧損", t1) and re.search(r"帳面|成本|價金|總金額|交易金額|每股|淨值", c[:max(0, vals[0][2])]):
        out["狀態"] = "未量化（只揭露價金／帳面／成本）"; return out
    loss = bool(re.search(r"損失|虧損|負數|為負|減少", t1)) and not re.search(r"利益", t1.split("損失")[0][-6:] if "損失" in t1 else "")
    gain_word = bool(re.search(r"利益|獲利|收益", t1))
    curs = {v[1] for v in vals if v[1]}
    cur = vals[0][1] or (sorted(curs)[0] if len(curs) == 1 else "TWD")
    if len(curs) > 1:
        tw2 = [v for v in vals if v[1] == "TWD"]
        if cur != "TWD" and tw2 and out["公司揭露約當台幣"] is None: out["公司揭露約當台幣"] = abs(tw2[0][0])
        elif cur == "TWD" and not vals[0][1]: pass
        else: out["疑義"] += "多幣別；"
    rng = re.search(NUM + r"[^\d至~～到]{0,6}(?:至|~|～|到)\s*[^\d]{0,6}?" + NUM, c)
    rng2 = re.search(r"\d\s*(?:仟|千|萬|百萬|佰萬|億)?\s*元\s*[-－]\s*\d", c)
    if rng2 and not rng: rng = rng2; vals = [(abs(v[0]), v[1], v[2]) for v in vals]
    absvals = [abs(v[0]) for v in vals]
    if rng and len(vals) >= 2:
        a0, a1 = absvals[0], absvals[1]
        # 區間只有一端帶單位（如「46.27~62.84億元」）：比照另一端的倍數
        r0 = [float(re.sub(r"[,，\s]", "", x).replace("－", "-").replace("−", "-")) for x in rng.groups() if x]
        if len(r0) == 2 and abs(r0[0]) > 0 and abs(r0[1]) > 0:
            m0, m1 = a0 / abs(r0[0]), a1 / abs(r0[1])
            if m0 == 1 and m1 > 1: a0 *= m1
            elif m1 == 1 and m0 > 1: a1 *= m0
        lo, hi = sorted([a0, a1]); out.update(下限=lo, 上限=hi, 金額=None)
        out["狀態"] = "區間"
    else:
        distinct = sorted({round(a, 2) for a in absvals})
        pick = 0
        if len(distinct) > 1:
            kws = [m.end() for m in re.finditer(r"處分(?:利益|損失|損益|淨利|利得|毛利)|(?:淨)?(?:利益|損失|獲利|利得)", c)]
            cand = [k for k, v in enumerate(vals) if any(0 <= v[2] - e <= 30 for e in kws)]
            pick = cand[0] if cand else 0
            out["疑義"] += "多個數值，取損益字樣後第一個；" if cand else "多個數值，取第一個；"
            if vals[pick][1] and vals[pick][1] != "TWD" and out["公司揭露約當台幣"] is None:
                tw2 = [v for v in vals[pick + 1:pick + 3] if v[1] == "TWD"]
                if tw2: out["公司揭露約當台幣"] = abs(tw2[0][0])
        ctx = c[max(0, vals[pick][2] - 14): vals[pick][2]]
        if re.search(r"成本|帳面|價金|總金額|交易金額|淨值|總價", ctx) and not re.search(r"利益|損失|損益|獲利|利得", ctx):
            out["狀態"] = "未量化（只揭露價金／帳面／成本）"; return out
        out["金額"] = absvals[pick]; out["狀態"] = "單一數值"; cur = vals[pick][1] or cur
    if (out["金額"] == 0) or (out["狀態"] == "區間" and out["上限"] == 0): out.update(方向="零", 狀態="零")
    elif loss and gain_word: out["方向"] = "不明（利益與損失字樣並存）"; out["疑義"] += "利益損失並存；"
    elif loss or any(v[0] < 0 for v in vals): out["方向"] = "損失"
    else: out["方向"] = "利益"
    out["幣別"] = cur
    return out
