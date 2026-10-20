"""bt_stats — 回測統計共用函式（Elon 計算、Eve 核對的唯一口徑）

版本：1.0（2026-10-14）
依據：Elon 工作手冊 V15 第 7 節

用法（Python）：
    from bt_stats import summarize, summarize_df
    row = summarize(returns, hold_days=hold, cluster=entry_dates, cluster_unit="進場日")
    table = summarize_df(df, ret="報酬", hold="持有交易日數", cluster="進場日",
                         cluster_unit="進場日", by="參數組")

用法（命令列）：
    python bt_stats.py --selftest
    python bt_stats.py 明細.csv --ret 報酬 --hold 持有交易日數 --cluster 進場日 \
        --cluster-unit 進場日 --by 參數組 [--out 結果.csv]

規則摘要：
  - 報酬一律用小數（0.0123 = 1.23%），不得用百分數。
  - |報酬| < ZERO_TOL 視為 0：計入樣本數，不算勝，不進 R。
  - 輸入不得有缺值；排除的交易應在上游剔除並記錄排除原因。
  - 輸出為未四捨五入的數值；無法計算者為 None，原因寫在「N/A原因」。
  - 本檔不得複製後修改。錯誤或需新功能時回報 Ed，由 Ed 授權升版。
"""
from __future__ import annotations

import math
import sys
from collections import OrderedDict

import numpy as np
from scipy import stats as _st

VERSION = "1.0"
ZERO_TOL = 1e-9
TRADING_DAYS = 252

COLUMNS = [
    "樣本數", "平均報酬", "平均持有交易日數", "單利年化", "勝率", "賠率R",
    "凱利", "半凱利", "標準差", "t值", "雙尾p",
    "聚合單位", "聚合單位數", "單位最大筆數", "聚合t", "聚合p", "N/A原因", "bt_stats版本",
]


def _ttest(x: np.ndarray):
    """單樣本對 0、雙尾。回傳 (t, p, 原因)。"""
    n = len(x)
    if n < 2:
        return None, None, "樣本數<2"
    sd = float(np.std(x, ddof=1))
    if sd == 0:
        return None, None, "標準差為0"
    t = float(np.mean(x)) / (sd / math.sqrt(n))
    p = float(2 * _st.t.sf(abs(t), df=n - 1))
    return t, p, None


def summarize(returns, hold_days=None, cluster=None, cluster_unit=None) -> "OrderedDict":
    """計算一組交易的完整統計。

    returns      逐筆報酬（小數）。
    hold_days    逐筆實際占用資金的交易日數（同日進出=1）；None 則年化填 N/A。
    cluster      逐筆聚合單位標籤（進場日或批次代號）；None 則不算聚合 p。
    cluster_unit 聚合單位名稱，只能是「進場日」或「批次」。
    """
    r = np.asarray(returns, dtype=float)
    if r.ndim != 1:
        raise ValueError("returns 必須是一維")
    if np.isnan(r).any() or np.isinf(r).any():
        raise ValueError("returns 含缺值或無限值；排除的交易請在上游剔除並記錄原因")
    r = np.where(np.abs(r) < ZERO_TOL, 0.0, r)
    n = len(r)
    na = OrderedDict()
    out = OrderedDict((c, None) for c in COLUMNS)
    out["樣本數"] = n
    out["bt_stats版本"] = VERSION
    if n == 0:
        na["全部"] = "樣本數為0"
        out["N/A原因"] = "；".join(f"{k}:{v}" for k, v in na.items())
        return out

    out["平均報酬"] = float(np.mean(r))
    wins, losses = r[r > 0], r[r < 0]
    p_win = len(wins) / n
    out["勝率"] = p_win

    if len(losses) == 0:
        na["賠率R/凱利"] = "無虧損筆"
    elif len(wins) == 0:
        na["賠率R/凱利"] = "無獲利筆"
    else:
        R = float(np.mean(wins)) / abs(float(np.mean(losses)))
        out["賠率R"] = R
        k = p_win - (1 - p_win) / R
        out["凱利"] = k
        out["半凱利"] = k / 2

    if n >= 2:
        out["標準差"] = float(np.std(r, ddof=1))
    else:
        na["標準差"] = "樣本數<2"
    t, p, why = _ttest(r)
    out["t值"], out["雙尾p"] = t, p
    if why:
        na["t/p"] = why

    # 第九、十項
    if hold_days is None:
        na["持有日/年化"] = "未提供持有交易日數"
    else:
        h = np.asarray(hold_days, dtype=float)
        if len(h) != n:
            raise ValueError("hold_days 長度與 returns 不同")
        if np.isnan(h).any() or (h < 1).any() or (h != np.round(h)).any():
            raise ValueError("hold_days 必須是 ≥1 的整數（同日進出計 1）")
        out["平均持有交易日數"] = float(np.mean(h))
        out["單利年化"] = out["平均報酬"] * TRADING_DAYS / out["平均持有交易日數"]

    # 聚合 p
    if cluster is not None:
        if cluster_unit not in ("進場日", "批次"):
            raise ValueError("cluster_unit 只能是「進場日」或「批次」")
        c = np.asarray(cluster, dtype=object)
        if len(c) != n:
            raise ValueError("cluster 長度與 returns 不同")
        if any(x is None or (isinstance(x, float) and math.isnan(x)) for x in c):
            raise ValueError("cluster 含缺值")
        keys, inv = np.unique(c.astype(str), return_inverse=True)
        sums = np.bincount(inv, weights=r)
        cnts = np.bincount(inv)
        means = sums / cnts
        out["聚合單位"] = cluster_unit
        out["聚合單位數"] = len(keys)
        out["單位最大筆數"] = int(cnts.max())
        t2, p2, why2 = _ttest(means)
        out["聚合t"], out["聚合p"] = t2, p2
        if why2:
            na["聚合t/p"] = why2
        elif len(keys) < 10:
            na["聚合p提醒"] = "聚合單位數<10，檢定力不足"

    out["N/A原因"] = "；".join(f"{k}:{v}" for k, v in na.items()) or None
    return out


def summarize_df(df, ret, hold=None, cluster=None, cluster_unit=None, by=None):
    """對明細表依 by 分組計算，回傳 pandas DataFrame（每組一列）。"""
    import pandas as pd

    def one(g):
        return summarize(
            g[ret].to_numpy(),
            hold_days=None if hold is None else g[hold].to_numpy(),
            cluster=None if cluster is None else g[cluster].to_numpy(),
            cluster_unit=cluster_unit,
        )

    if by is None:
        return pd.DataFrame([one(df)])
    rows = []
    for key, g in df.groupby(by, sort=False):
        row = OrderedDict()
        row[by if isinstance(by, str) else "組合"] = key
        row.update(one(g))
        rows.append(row)
    return pd.DataFrame(rows)


# ---------------- 自我測試 ----------------
def _selftest():
    ok = True

    def check(name, got, exp, tol=1e-12):
        nonlocal ok
        good = (got is None and exp is None) or (
            got is not None and exp is not None and abs(got - exp) <= tol)
        print(("PASS " if good else "FAIL ") + f"{name}: {got} (預期 {exp})")
        ok &= good

    # 手算案例：+2%, -1%, 浮點零, +1%
    r = [0.02, -0.01, 1e-16, 0.01]
    s = summarize(r, hold_days=[1, 2, 1, 4], cluster=["d1", "d1", "d2", "d3"], cluster_unit="進場日")
    check("平均報酬", s["平均報酬"], 0.02 / 4)
    check("勝率(零計入分母)", s["勝率"], 0.5)
    check("賠率R", s["賠率R"], 0.015 / 0.01)
    check("凱利", s["凱利"], 0.5 - 0.5 / 1.5)
    check("半凱利", s["半凱利"], (0.5 - 0.5 / 1.5) / 2)
    check("標準差", s["標準差"], float(np.std([0.02, -0.01, 0.0, 0.01], ddof=1)))
    t_ref = _st.ttest_1samp([0.02, -0.01, 0.0, 0.01], 0)
    check("t值", s["t值"], float(t_ref.statistic))
    check("雙尾p", s["雙尾p"], float(t_ref.pvalue))
    check("平均持有", s["平均持有交易日數"], 2.0)
    check("單利年化", s["單利年化"], 0.005 * 252 / 2)
    a_ref = _st.ttest_1samp([0.005, 0.0, 0.01], 0)  # d1 平均 0.005、d2 0、d3 0.01
    check("聚合單位數", s["聚合單位數"], 3, tol=0)
    check("聚合t", s["聚合t"], float(a_ref.statistic))
    check("聚合p", s["聚合p"], float(a_ref.pvalue))

    s2 = summarize([0.01, 0.02, 0.03])
    check("無虧損→R為N/A", s2["賠率R"], None)
    check("無虧損→凱利N/A", s2["凱利"], None)
    print("N/A原因範例：", s2["N/A原因"])

    # 群聚造成的顯著性高估示範：20 批，每批 10 筆完全同向
    rng = np.random.default_rng(0)
    batch_eff = rng.normal(0.006, 0.02, 20)
    rr = np.repeat(batch_eff, 10) + rng.normal(0, 0.002, 200)
    s3 = summarize(rr, cluster=np.repeat(np.arange(20), 10), cluster_unit="批次")
    print(f"群聚示範：逐筆 N={s3['樣本數']} p={s3['雙尾p']:.4g}；"
          f"批次 N={s3['聚合單位數']} p={s3['聚合p']:.4g}")

    for bad, kw in [([0.01, float('nan')], {}), ([0.01], {"hold_days": [0]}),
                    ([0.01, 0.02], {"cluster": ["a", "b"], "cluster_unit": "週"})]:
        try:
            summarize(bad, **kw)
            print("FAIL 應拒絕不合法輸入", bad, kw)
            ok = False
        except ValueError as e:
            print("PASS 拒絕不合法輸入：", e)
    print("全部通過" if ok else "有失敗項目")
    return ok


def _main(argv):
    import argparse
    import pandas as pd
    ap = argparse.ArgumentParser(description=f"bt_stats {VERSION}")
    ap.add_argument("csv", nargs="?")
    ap.add_argument("--ret")
    ap.add_argument("--hold")
    ap.add_argument("--cluster")
    ap.add_argument("--cluster-unit", choices=["進場日", "批次"])
    ap.add_argument("--by")
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return 0 if _selftest() else 1
    if not a.csv or not a.ret:
        ap.error("需要 csv 與 --ret")
    df = pd.read_csv(a.csv)
    res = summarize_df(df, a.ret, a.hold, a.cluster, a.cluster_unit, a.by)
    if a.out:
        res.to_csv(a.out, index=False, encoding="utf-8-sig")
    else:
        with pd.option_context("display.max_columns", None, "display.width", 200):
            print(res.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
