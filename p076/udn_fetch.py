# 076 S2：聯合新聞網站內搜尋（關鍵字逐頁抓到底），保存每頁原始 JSON 並彙整 CSV
import json, os, time, csv, urllib.request, urllib.parse, datetime
KWS = ['經營權之爭','經營權爭奪','經營權保衛戰','市場派','委託書大戰','委託書爭奪','股權爭奪','敵意併購',
       '自行召集','解任董事','董監席次','爭奪董事','董監改選','公開收購','股東臨時會 改選','經營權','公司派']
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36'
RAW = 'p076/udn_raw'; os.makedirs(RAW, exist_ok=True)
rows = {}; log = []
for kw in KWS:
    n = 0
    for p in range(1, 400):
        u = 'https://udn.com/api/more?' + urllib.parse.urlencode({'page': p, 'id': 'search:' + kw, 'channelId': 2, 'type': 'searchword'})
        try:
            t = urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': UA, 'Referer': 'https://udn.com/search/word/2/' + urllib.parse.quote(kw)}), timeout=60).read().decode('utf-8')
        except Exception as e:
            log.append(f'{kw}\t{p}\tERR {e}'); time.sleep(5); continue
        j = json.loads(t)
        open(f'{RAW}/{kw.replace(" ","_")}_{p:03d}.json', 'w', encoding='utf-8').write(t)
        L = j.get('lists') or []
        if not L: break
        for x in L:
            url = x.get('titleLink') or x.get('url') or ''
            r = rows.setdefault(url, {'url': url, 'title': x.get('title', ''), 'time': (x.get('time') or {}).get('date', ''),
                                      'paragraph': (x.get('paragraph') or '').replace('\n', ' '), 'kw': []})
            r['kw'].append(kw); n += 1
        time.sleep(0.8)
    log.append(f'{kw}\tpages={p-1}\titems={n}')
with open('p076/udn_articles.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f); w.writerow(['time', 'title', 'url', 'kw', 'paragraph'])
    for r in sorted(rows.values(), key=lambda r: r['time']):
        w.writerow([r['time'], r['title'], r['url'], '/'.join(r['kw']), r['paragraph']])
open('p076/udn_fetch_log.txt', 'w', encoding='utf-8').write(f'抓取時間(UTC) {datetime.datetime.utcnow().isoformat()}\n' + '\n'.join(log))
print('\n'.join(log)); print('total', len(rows))
