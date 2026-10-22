# 合併價格資料：031 抓取（全期）優先；其餘沿用 029 已抓資料並輸出其抓取區間供涵蓋檢查
import os, glob
A, B, C = 'data/out/p031', 'd29/out/p029', 'comb'
os.makedirs(C, exist_ok=True)
for f in glob.glob(C + '/*'): os.remove(f)
full = {f.split('_')[0] for f in os.listdir(A) if f.endswith('TaiwanStockCapitalReductionReferencePrice.json')}
for f in os.listdir(A): os.symlink(os.path.abspath(f'{A}/{f}'), f'{C}/{f}')
rng = {}
for l in open('/root/mops-fetch-test/codes_029.txt'):
    c, s, e, _ = l.strip().split(','); rng[c] = (s, e)
n = 0; out = []
for c, (s, e) in rng.items():
    if c in full: continue
    for ds in ('TaiwanStockPrice.csv.gz', 'TaiwanStockDividendResult.json', 'TaiwanStockCapitalReductionReferencePrice.json', 'TaiwanStockSplitPrice.json'):
        src = f'{B}/{c}_{ds}'
        if os.path.exists(src) and not os.path.exists(f'{C}/{c}_{ds}'): os.symlink(os.path.abspath(src), f'{C}/{c}_{ds}')
    out.append(f'{c},{s},{e}'); n += 1
open('ranges029.txt', 'w').write('\n'.join(out) + '\n'); print('031 全期', len(full), '029 沿用', n)
