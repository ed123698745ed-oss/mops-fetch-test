# 054 v2：已下市前身公司（2311/2325/6251）t164sb03 不再提供，改抓電子書合併財報 PDF（D-054-20261105-0041-1 MOPS 路線）
# 保存：step9 回應 HTML、pdftotext -layout 文字(gzip)、PDF 的 sha256；不保存 PDF 本體
import os, sys, time, gzip, re, hashlib, subprocess, urllib.request
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
OUT = "out/p054/pdftxt"; os.makedirs(OUT, exist_ok=True)
log = open("out/p054/pdf_log.txt", "a", encoding="utf-8")
def L(s): print(s); log.write(s + "\n"); log.flush()
def get(u): return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=120).read()
DEADLINE = time.time() + 50 * 60
for line in open("p054/pdf_list.txt"):
    if not line.strip(): continue
    c, fn = line.strip().split(",")
    t = f"{OUT}/{fn}.txt.gz"
    if os.path.exists(t) and os.path.getsize(t) > 200: continue
    if time.time() > DEADLINE: L("時間到"); break
    for a in range(3):
        try:
            h = get(f"https://doc.twse.com.tw/server-java/t57sb01?step=9&kind=A&co_id={c}&filename={fn}")
            with gzip.open(f"{OUT}/{fn}.step9.html.gz", "wb") as g: g.write(h)
            m = re.search(rb"href=['\"]?(/pdf/[^'\" >]+\.pdf)", h)
            if not m: L(f"{fn} 無PDF連結 {h[:200]!r}"); break
            time.sleep(2)
            p = get("https://doc.twse.com.tw" + m.group(1).decode())
            if not p.startswith(b"%PDF"): L(f"{fn} 非PDF {p[:100]!r}"); break
            open("/tmp/x.pdf", "wb").write(p)
            txt = subprocess.run(["pdftotext", "-layout", "/tmp/x.pdf", "-"], capture_output=True).stdout
            with gzip.open(t, "wb") as g: g.write(txt)
            L(f"{fn} pdf {len(p)} sha256 {hashlib.sha256(p).hexdigest()} txt {len(txt)}"); break
        except Exception as e:
            L(f"{fn} 第{a+1}次錯誤 {e}"); time.sleep(10)
    time.sleep(3)
L("完成")
