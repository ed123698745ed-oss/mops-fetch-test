# 058 盤點：(1) 公司基本資料 ajax_t05st03（主要經營業務／營業比重，63 檔現行資料）
#           (2) 年報（mtype=F）清單與 PDF：民國 112、113 年上傳者（S1 客戶證據，四條優先鏈 23 檔）；民國 115 年上傳者（最近年報，63 檔產品純度核對）
#               PDF 只保存 pdftotext 全文（gzip），不存 PDF
# 用法：python p058/fetch_ar.py；已存在略過（可接力）；每次請求間隔 3 秒
import os, re, sys, time, gzip, subprocess, urllib.request, urllib.parse
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
OUT = "out/p058/ar"; os.makedirs(OUT, exist_ok=True)
log = open(f"out/p058/ar_log_{os.environ.get('GITHUB_RUN_ID', 'local')}.txt", "a", encoding="utf-8")  # 每輪獨立日誌，避免多輪同時推送衝突
def L(s): print(s, flush=True); log.write(s + "\n"); log.flush()
DEADLINE = time.time() + 52 * 60
def rd(p): return [x.strip() for x in open(p, encoding="utf-8") if x.strip() and not x.startswith("#")]
def get(url, data=None, ref=None):
    h = {"User-Agent": UA}
    if ref: h["Referer"] = ref
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode() if data else None, headers=h)
    b = urllib.request.urlopen(req, timeout=120).read(); time.sleep(3)
    if b"SECURITY" in b[:3000]:
        L(f"被擋 {url}"); raise SystemExit(2)
    return b
def once(path, fn):
    if os.path.exists(path): return gzip.open(path).read()
    if time.time() > DEADLINE: L("時間到，下輪接力"); raise SystemExit(0)
    for a in range(3):
        try:
            b = fn(); gzip.open(path, "wb").write(b); L(f"{path} {len(b)}"); return b
        except SystemExit: raise
        except Exception as e: L(f"{path} 第{a+1}次錯誤 {e}"); time.sleep(10)
    return None
for c in rd("p058/codes_058.txt"):
    once(f"{OUT}/t05st03_{c}.html.gz", lambda c=c: get("https://mopsov.twse.com.tw/mops/web/ajax_t05st03",
        {"encodeURIComponent": 1, "step": 1, "firstin": 1, "off": 1, "keyword4": "", "code1": "", "TYPEK2": "",
         "checkbtn": "", "queryName": "co_id", "inpuType": "co_id", "TYPEK": "all", "co_id": c},
        ref="https://mopsov.twse.com.tw/mops/web/t05st03"))
jobs = [(c, y) for c in rd("p058/codes_ar.txt") for y in (112, 113)] + [(c, 115) for c in rd("p058/codes_058.txt")]
for c, y in jobs:
    if True:
        b = once(f"{OUT}/arlist_{c}_{y}.html.gz", lambda c=c, y=y: get(
            f"https://doc.twse.com.tw/server-java/t57sb01?step=1&colorchg=1&co_id={c}&year={y}&mtype=F&"))
        if not b: continue
        h = b.decode("big5", "ignore")
        fns = re.findall(r'readfile2\("F","%s","([^"]+\.pdf)"\)' % c, h)
        pick = [f for f in fns if "F04" in f] or fns
        if not pick: L(f"{c} {y} 無年報檔"); continue
        fn = pick[0]; txt = f"{OUT}/ar_{c}_{y}_{fn[:-4]}.txt.gz"
        if os.path.exists(txt): continue
        if time.time() > DEADLINE: L("時間到，下輪接力"); sys.exit(0)
        try:
            p9 = get(f"https://doc.twse.com.tw/server-java/t57sb01?step=9&kind=F&co_id={c}&filename={fn}").decode("big5", "ignore")
            m = re.search(r"href=['\"]?([^'\" >]+\.pdf)", p9, re.I)
            if not m: L(f"{c} {y} {fn} 找不到下載連結"); open(f"{OUT}/p9_{c}_{y}.html","w").write(p9[:5000]); continue
            pdf = get(urllib.parse.urljoin("https://doc.twse.com.tw/", m.group(1)))
            open("/tmp/a.pdf", "wb").write(pdf)
            subprocess.run(["pdftotext", "-layout", "/tmp/a.pdf", "/tmp/a.txt"], check=True)
            gzip.open(txt, "wb").write(open("/tmp/a.txt", "rb").read()); L(f"{txt} pdf {len(pdf)}")
        except SystemExit: raise
        except Exception as e: L(f"{c} {y} {fn} 錯誤 {e}")
L("完成")
