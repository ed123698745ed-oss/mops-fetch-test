# 054 v2 D-054-20261105-1005-1：已下市前身 2311/2325/6251 合併財報 PDF 中圖片型資產負債表以 OCR 取數
# 用法：python p054/fetch_ocr.py <slice> <nslices>；每份 PDF 對第 1～15 頁中「文字層少於 300 字元」的頁面做 OCR（300dpi，chi_tra+eng，psm 6）
# 保存：out/p054/ocr/<pdf>_p<頁>.txt.gz 與 log（含 PDF sha256）；不保存 PDF 本體
import os, sys, time, gzip, re, hashlib, subprocess, urllib.request
k, n = int(sys.argv[1]), int(sys.argv[2])
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
OUT = "out/p054/ocr"; os.makedirs(OUT, exist_ok=True)
log = open(f"out/p054/ocr_log_{k}.txt", "a", encoding="utf-8")
def L(s): print(s); log.write(s + "\n"); log.flush()
def get(u): return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=120).read()
DEADLINE = time.time() + 75 * 60
rows = [l.strip().split(",") for l in open("p054/pdf_list.txt") if l.strip()][k::n]
for c, fn in rows:
    done = f"{OUT}/{fn}.done"
    if os.path.exists(done): continue
    if time.time() > DEADLINE: L("時間到"); break
    p = None
    for a in range(3):
        try:
            h = get(f"https://doc.twse.com.tw/server-java/t57sb01?step=9&kind=A&co_id={c}&filename={fn}")
            m = re.search(rb"href=['\"]?(/pdf/[^'\" >]+\.pdf)", h)
            if not m: L(f"{fn} 無PDF連結"); break
            time.sleep(2); p = get("https://doc.twse.com.tw" + m.group(1).decode())
            if not p.startswith(b"%PDF"): L(f"{fn} 非PDF"); p = None
            break
        except Exception as e:
            L(f"{fn} 第{a+1}次錯誤 {e}"); time.sleep(10)
    if not p: continue
    open("/tmp/x.pdf", "wb").write(p)
    pages = []
    for pg in range(1, 16):
        t = subprocess.run(["pdftotext", "-f", str(pg), "-l", str(pg), "-layout", "/tmp/x.pdf", "-"], capture_output=True).stdout
        if subprocess.run(["pdfinfo", "/tmp/x.pdf"], capture_output=True).stdout and len(t.strip()) < 300: pages.append(pg)
    for pg in pages:
        subprocess.run(["pdftoppm", "-f", str(pg), "-l", str(pg), "-r", "300", "-gray", "-png", "/tmp/x.pdf", "/tmp/pg"])
        img = [f for f in os.listdir("/tmp") if f.startswith("pg") and f.endswith(".png")]
        if not img: continue
        o = subprocess.run(["tesseract", "/tmp/" + img[0], "-", "-l", "chi_tra+eng", "--psm", "6"], capture_output=True).stdout
        for f in img: os.remove("/tmp/" + f)
        with gzip.open(f"{OUT}/{fn}_p{pg:02d}.txt.gz", "wb") as g: g.write(o)
    open(done, "w").write(",".join(map(str, pages)))
    L(f"{fn} sha256 {hashlib.sha256(p).hexdigest()} ocr_pages {pages}")
    time.sleep(3)
L(f"slice {k} 完成")
