# A11：證交所「上市普通股股數增減公告」(LT185) 介面探測。只讀公開頁面，結果存 out/lt185/
import urllib.request, os, re
os.makedirs('out/lt185', exist_ok=True)
UA={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/129.0 Safari/537.36','Referer':'https://www.twse.com.tw/zh/page/announcement/LT185.html'}
def get(u,fn):
    try:
        t=urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=60).read().decode('utf-8','replace')
    except Exception as e: t=f'ERROR {e}'
    open('out/lt185/'+fn,'w',encoding='utf-8').write(u+'\n'+t); return t
page=get('https://www.twse.com.tw/zh/page/announcement/LT185.html','page.html')
for i,js in enumerate(set(re.findall(r'src="([^"]+\.js[^"]*)"',page))):
    if js.startswith('/'): js='https://www.twse.com.tw'+js
    get(js,f'js_{i}.js')
for i,u in enumerate(['https://www.twse.com.tw/rwd/zh/announcement/LT185?response=json&sdate=20240901&edate=20241031',
 'https://www.twse.com.tw/rwd/zh/announcement/LT185?response=json&startDate=20240901&endDate=20241031',
 'https://www.twse.com.tw/announcement/LT185?response=json&sdate=20240901&edate=20241031',
 'https://www.twse.com.tw/rwd/zh/announcement/lt185?response=json']):
    get(u,f'try_{i}.txt')
