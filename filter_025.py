# 025 候選篩選：從每日重大訊息 CSV 找「合約／授權終止」候選公告（試抓用，規則待 Ed 確認後凍結）
# 用法：python filter_025.py data/announcements_2023.csv.gz out/candidates_2023.csv
import sys, csv, gzip, re
from collections import Counter

src, dst = sys.argv[1], sys.argv[2]
op = gzip.open if src.endswith(".gz") else open
rows = list(csv.DictReader(op(src, "rt", encoding="utf-8-sig")))

# 去重：同公司、同發言日期時間、同主旨只留一筆（每日頁面以前一日17:30為界，相鄰查詢日會重疊）
seen, uniq = set(), []
for r in rows:
    k = (r["公司代號"], r["發言日期"], r["發言時間"], r["主旨"])
    if k not in seen:
        seen.add(k); uniq.append(r)

TERM = re.compile(r"終止|解除|不續約|不再續約|不予續約|提前結束|提前終止|屆期不續|返還")
OBJ = re.compile(r"合約|契約|協議|合作|授權|訂單|經銷|代理|供貨|採購|備忘錄|MOU", re.I)
# 明顯不屬本題（卡上排除或建議排除）的主題，只做標記，不刪除，供人工核對
EXCL = re.compile(r"私募|增資|減資|可轉換公司債|轉換公司債|股份轉換|合併|分割|收購|併購|公開收購|"
                  r"租賃|租約|不動產|土地|廠房買賣|借款|聯貸|授信|額度|委任|董事|經理人|會計師|簽證|"
                  r"庫藏股|股利|除權|除息|上櫃|上市|終止上市|終止櫃檯|下市|興櫃|股票|"
                  r"衍生性|期貨|避險|投資案|處分|取得")

out = []
for r in uniq:
    if r["市場別"] not in ("sii", "otc"):   # 本題股票池只含上市、上櫃
        continue
    subj = r["主旨"]
    hit_subj = bool(TERM.search(subj) and OBJ.search(subj))
    hit_body = bool(TERM.search(r["說明"]) and OBJ.search(r["說明"])) and bool(TERM.search(subj))
    if hit_subj or hit_body:
        r2 = dict(r)
        r2["命中位置"] = "主旨" if hit_subj else "主旨含終止詞+說明含合約詞"
        r2["疑似排除主題"] = "、".join(sorted(set(EXCL.findall(subj)))) or ""
        out.append(r2)

cols = list(out[0].keys()) if out else []
with open(dst, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(out)

print(f"原始 {len(rows)} 筆，去重後 {len(uniq)} 筆，上市櫃 {sum(r['市場別'] in ('sii','otc') for r in uniq)} 筆")
print(f"候選 {len(out)} 筆；其中疑似排除主題 {sum(1 for r in out if r['疑似排除主題'])} 筆")
print("候選條款代號(h15,h16):", Counter((r["條款代號h15"], r["款項h16"]) for r in out).most_common(10))
