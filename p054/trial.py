# 054 多空配置-同族群資產擴張策略：MOPS 財報歷史版本可行性試抓（D-054-20261104-1940-1）
# 只抓 5 檔種子公司、少量季度；每次請求間隔 3 秒；原始回應全部保存，不解析成結論。
# 試抓目的：
#  A. 資產負債表查詢(t164sb03)：2013Q4 年報是否列 2012-12-31 IFRS 比較數；2014Q1 是否列 2013Q1 比較數
#  B. 電子書(t57sb01)：財報檔案清單是否有上傳日期、是否區分更正版本
#  C. 財報更正：用 repo 既有重訊資料搜「更正」「重編」財報公告（不另抓）
import os, time, gzip, json, urllib.request, urllib.parse

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
OUT = "out/p054_trial"; os.makedirs(OUT, exist_ok=True)
log = open(f"{OUT}/log.txt", "w", encoding="utf-8")
def L(s): print(s); log.write(s + "\n"); log.flush()

CODES = ["3037", "8046", "3189", "2313", "2603"]  # 欣興、南電、景碩、華通、長榮
BS_Q = [(101, 4), (102, 1), (102, 4), (103, 1), (105, 2)]   # 民國年, 季
DOC_Y = [102, 103, 105]

def get(url, data=None, ref=None):
    h = {"User-Agent": UA}
    if ref: h["Referer"] = ref
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode() if data else None, headers=h)
    r = urllib.request.urlopen(req, timeout=90)
    return r.status, dict(r.headers), r.read()

def save(name, status, headers, body):
    open(f"{OUT}/{name}", "wb").write(body)
    blocked = b"SECURITY" in body[:3000]
    L(f"{name}: HTTP {status} {len(body)} bytes blocked={blocked} type={headers.get('Content-Type','')}")

for c in CODES:
    for y, s in BS_Q:
        try:
            st, hd, b = get("https://mopsov.twse.com.tw/mops/web/ajax_t164sb03",
                {"encodeURIComponent": 1, "step": 1, "firstin": 1, "off": 1, "queryName": "co_id",
                 "inpuType": "co_id", "TYPEK": "all", "isnew": "false", "co_id": c, "year": y, "season": f"{s:02d}"},
                ref="https://mopsov.twse.com.tw/mops/web/t164sb03")
            save(f"bs_{c}_{y}Q{s}.html", st, hd, b)
        except Exception as e:
            L(f"bs_{c}_{y}Q{s}: 錯誤 {e}")
        time.sleep(3)
    for y in DOC_Y:
        try:
            st, hd, b = get(f"https://doc.twse.com.tw/server-java/t57sb01?step=1&colorchg=1&co_id={c}&year={y}&mtype=A&")
            save(f"doc_{c}_{y}.html", st, hd, b)
        except Exception as e:
            L(f"doc_{c}_{y}: 錯誤 {e}")
        time.sleep(3)

# XBRL 整批檔：只記錄回應標頭與前 2KB，不下載全檔
for q in ["2013Q4", "2014Q1"]:
    try:
        req = urllib.request.Request(
            f"https://mops.twse.com.tw/server-java/FileDownLoad?step=9&fileName=tifrs-{q}.zip&filePath=/home/html/nas/ifrs/{q[:4]}/",
            headers={"User-Agent": UA})
        r = urllib.request.urlopen(req, timeout=90)
        head = r.read(2048)
        L(f"xbrl {q}: HTTP {r.status} len={r.headers.get('Content-Length')} type={r.headers.get('Content-Type')} zip={head[:2]==b'PK'}")
        open(f"{OUT}/xbrl_{q}_head.bin", "wb").write(head)
    except Exception as e:
        L(f"xbrl {q}: 錯誤 {e}")
    time.sleep(3)
L("完成")
