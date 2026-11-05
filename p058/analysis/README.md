# 058 S2 樣本內快篩：程式與輸出（Elon 保留，續做正式策略包時交付）
執行順序：parse_fin.py → margin_extract.py → run_is.py → stats_is.py（signals.py、engine.py 為模組；elon_tools.py 取自 elon-backtest 技能；統計用 bt_stats 1.2，sha256 e99c85e9…，不貼本體）。
輸入：out/p058/raw（公開資訊觀測站季報原始申報）、out/p054/raw、out/p054/corrlist、out/p058/ca（FinMind 公司行動）、FinMind 月營收、sector-tracker 官方日行情與融資融券表。
只計算凍結紀錄的樣本內；樣本外未計算。
