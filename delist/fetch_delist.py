# 抓官方終止上市清單（證交所擋雲端 IP，故在 GitHub Actions 跑）
import urllib.request, json, os, time
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/129.0 Safari/537.36"}
def get(u, f):
    for i in range(3):
        try:
            t = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read()
            open(f, "wb").write(t); print("OK", len(t), u); return
        except Exception as e:
            print("ERR", i, u, e); time.sleep(5)
os.makedirs("delist/raw", exist_ok=True)
get("https://openapi.twse.com.tw/v1/company/suspendListingCsvAndHtml", "delist/raw/twse_openapi_suspendListing.json")
for y in range(2005, 2027):
    get(f"https://www.twse.com.tw/rwd/zh/company/suspendListing?selectYear={y}&response=json", f"delist/raw/twse_rwd_{y}.json")
    time.sleep(3)
for u, f in [("https://www.tpex.org.tw/openapi/v1/tpex_spendi_history", "tpex_spendi_history.json")]:
    get(u, "delist/raw/" + f)
