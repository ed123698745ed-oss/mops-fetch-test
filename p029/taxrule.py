# 029 R03：稅別判定（Ed 2026-10-24：公告寫明金額「已扣除稅費」者視為稅後）
import re
FUT = re.compile(r"(尚待|待|將|俟|視|仍須|仍需|須以|需以)[^。；;]*")                       # 未來才扣除的子句（金額本身未扣）
PRE = re.compile(r"(尚未|未(?!來)|不含|未含)\s*(扣除|扣減|減除|計入|包含)?[^。；;，,]{0,12}(稅|稅費|稅賦|稅負|稅款)")
NET = re.compile(r"(扣除|減除|扣減|扣繳|扣抵|減去|扣掉)[^。；;]{0,30}(稅|稅費|稅賦|稅負|稅款)|考慮[^。；;]{0,12}稅[負賦費]?後|稅[費負賦]?後之?處分")
def tax(t1):
    if "稅後" in t1: return "稅後"
    s = FUT.sub("", t1)
    if PRE.search(t1) and not NET.search(PRE.sub("", s)): return "稅前"
    if NET.search(PRE.sub("", s)): return "稅後"
    if "稅前" in t1: return "稅前"
    return "推定稅前（格式欄位，Ed 10/22）"
