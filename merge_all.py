# 合併所有抓取分段的公告 CSV，依年份輸出去重後的公告總表，並列出每年缺漏日期
# 用法：python merge_all.py
import csv, gzip, glob, os, datetime
from collections import defaultdict

os.makedirs("merged", exist_ok=True)
hdr, by_year, seen = None, defaultdict(list), set()
for f in sorted(glob.glob("data/announcements_*.csv.gz")):
    for r in csv.reader(gzip.open(f, "rt", encoding="utf-8-sig")):
        if r[0] == "查詢日":
            hdr = r; continue
        k = (r[2], r[4], r[5], r[6])          # 公司代號、發言日期、發言時間、主旨
        if k in seen:
            continue
        seen.add(k); by_year[r[4][:4]].append(r)

for y, rows in sorted(by_year.items()):
    rows.sort(key=lambda r: (r[4], r[5], r[2]))
    with gzip.open(f"merged/MOPS每日重大訊息_公告總表_{y}.csv.gz", "wt", encoding="utf-8-sig", newline="") as g:
        w = csv.writer(g); w.writerow(hdr); w.writerows(rows)
    print(y, "去重後", len(rows), "上市櫃", sum(r[1] in ("sii", "otc") for r in rows))

# 缺漏日期：以 raw 原始檔是否存在判斷（查詢日）
for ydir in sorted(glob.glob("raw/*")):
    y = int(os.path.basename(ydir))
    have = {os.path.basename(p)[8:16] for p in glob.glob(f"{ydir}/*.html.gz")}
    d, miss = datetime.date(y, 1, 1), []
    while d.year == y and d <= datetime.date.today():
        if d.strftime("%Y%m%d") not in have:
            miss.append(d.strftime("%m%d"))
        d += datetime.timedelta(days=1)
    print(y, "已抓", len(have), "天，缺", len(miss), "天", (miss if len(miss) <= 40 else miss[:5] + ["…"] + miss[-5:]))
