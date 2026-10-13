# 測試 GitHub Actions 主機能否連到公開資訊觀測站（只抓一天，存原始檔）
import urllib.request, urllib.parse, json
_log=open("result.txt","w",encoding="utf-8")
def _p(*a):
    s=" ".join(str(x) for x in a); print(s); _log.write(s+"\n"); _log.flush()
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
try:
    _p("本機對外 IP:", urllib.request.urlopen("https://api.ipify.org", timeout=20).read().decode())
except Exception as e:
    _p("IP 查詢失敗", e)
tests = [
  ("mopsov_t05st02", "https://mopsov.twse.com.tw/mops/web/ajax_t05st02",
   {"encodeURIComponent":1,"step":1,"step00":0,"firstin":1,"off":1,"TYPEK":"all","year":112,"month":"03","day":"08"}),
  ("mops_home", "https://mops.twse.com.tw/mops/", None),
  ("twse_home", "https://www.twse.com.tw/zh/", None),
]
for name, url, form in tests:
    try:
        data = urllib.parse.urlencode(form).encode() if form else None
        req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Referer": "https://mopsov.twse.com.tw/mops/web/t05st02"})
        r = urllib.request.urlopen(req, timeout=60)
        html = r.read().decode("utf-8", "replace")
        blocked = "SECURITY" in html
        open(f"{name}.html", "w", encoding="utf-8").write(html)
        _p(f"{name}: HTTP {r.status}, {len(html)} 字元, 被擋={blocked}")
        if not blocked: _p(html[:800].replace("\n"," "))
    except Exception as e:
        _p(f"{name}: 錯誤 {e}")
