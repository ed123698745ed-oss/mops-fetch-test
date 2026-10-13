# 逐日抓公開資訊觀測站「每日重大訊息」(t05st02)，保存原始 HTML(gzip) 並解析成 CSV
# 用法：python fetch_year.py 2023            （整年）
#       python fetch_year.py 20230505 20230623 （指定起訖日，含兩端）
import sys, os, re, gzip, csv, time, datetime, html as H, urllib.request, urllib.parse
a = sys.argv[1]
if len(a) == 4:
    start, end = datetime.date(int(a),1,1), datetime.date(int(a),12,31); tag = a
else:
    P = lambda x: datetime.datetime.strptime(x, "%Y%m%d").date()
    start, end = P(a), P(sys.argv[2]); tag = f"{a}_{sys.argv[2]}"
year = start.year
URL = "https://mopsov.twse.com.tw/mops/web/ajax_t05st02"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
rawdir = f"raw/{year}"; os.makedirs(rawdir, exist_ok=True); os.makedirs("data", exist_ok=True)
log = open(f"data/fetch_log_{tag}.txt", "a", encoding="utf-8")
def L(s): print(s); log.write(s + "\n"); log.flush()

def fetch(d):
    body = urllib.parse.urlencode({"encodeURIComponent":1,"step":1,"step00":0,"firstin":1,"off":1,
        "TYPEK":"all","year":d.year-1911,"month":f"{d.month:02d}","day":f"{d.day:02d}"}).encode()
    req = urllib.request.Request(URL, data=body, headers={"User-Agent":UA,"Referer":"https://mopsov.twse.com.tw/mops/web/t05st02"})
    return urllib.request.urlopen(req, timeout=90).read().decode("utf-8","replace")

form_re = re.compile(r"<form action='/mops/web/ajax_t05st02'.*?</form>", re.S)
inp_re = re.compile(r"<input type='hidden' name='h(\d+)' value='(.*?)'>", re.S)
typ_re = re.compile(r'TYPEK\.value="(\w+)"')
def parse(t, qdate):
    rows = []
    for f in form_re.findall(t):
        v = {"h1"+k[-1]: H.unescape(x) for k, x in inp_re.findall(f)}   # 欄位名 h<序號><0-8>，取最後一位
        m = typ_re.search(f)
        if "h11" not in v: continue
        rows.append([qdate, m.group(1) if m else "", v.get("h11",""), v.get("h10",""), v.get("h12",""), v.get("h13",""),
                     v.get("h14",""), v.get("h15",""), v.get("h16",""), v.get("h17",""), v.get("h18","")])
    return rows

out = open(f"data/announcements_{tag}.csv", "w", encoding="utf-8-sig", newline="")
w = csv.writer(out); w.writerow(["查詢日","市場別","公司代號","公司名稱","發言日期","發言時間","主旨","條款代號h15","款項h16","事實發生日","說明"])
d = start; n_total = 0
while d <= end and d <= datetime.date.today():
    rawdir = f"raw/{d.year}"; os.makedirs(rawdir, exist_ok=True)
    f = f"{rawdir}/t05st02_{d:%Y%m%d}.html.gz"
    for attempt in range(3):
        try:
            t = fetch(d)
            if "SECURITY" in t[:3000]:
                L(f"{d} 被擋(安全性錯誤頁)"); raise SystemExit(2)
            gzip.open(f, "wt", encoding="utf-8").write(t)
            rows = parse(t, d.strftime("%Y%m%d")); w.writerows(rows); out.flush(); n_total += len(rows)
            L(f"{d} 原始{len(t)}字元 公告{len(rows)}筆"); break
        except SystemExit: raise
        except Exception as e:
            L(f"{d} 第{attempt+1}次錯誤 {e}"); time.sleep(10)
    time.sleep(3)
    d += datetime.timedelta(days=1)
out.close(); L(f"完成 {tag} 共解析 {n_total} 筆(未去重)")
