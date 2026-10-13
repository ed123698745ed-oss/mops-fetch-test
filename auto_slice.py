# 自動接力：找出 2010-01-01 至今尚未抓取的日期（以 raw/ 原始檔判斷），由新到舊排序，
# 切給第 idx 個工作（共 n 個），每個工作 per 天。輸出 dates:YYYYMMDD,... 給 fetch_year.py
import sys, os, glob, datetime
idx, n, per = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
have = {os.path.basename(p)[8:16] for p in glob.glob("raw/*/*.html.gz")}
d, miss = datetime.date.today() - datetime.timedelta(days=1), []
while d >= datetime.date(2010, 1, 1):
    if d.strftime("%Y%m%d") not in have:
        miss.append(d)
    d -= datetime.timedelta(days=1)
mine = sorted(miss[idx * per:(idx + 1) * per])
print("dates:" + ",".join(x.strftime("%Y%m%d") for x in mine) if mine else "")
