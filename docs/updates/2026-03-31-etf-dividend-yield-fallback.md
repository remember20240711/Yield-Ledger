# 2026-03-31 ETF 股息率回补更新

## 背景

`512890.SH`（红利低波ETF华泰柏瑞）在 Yahoo Finance 返回的分红序列为空，导致服务端将其 `TTM 分红` 和 `当前股息率` 计算为 `0`，前端因此无法展示有效股息率。

## 本次改动

- 在 `backend/app/services/provider.py` 为 `CN ETF` 增加股息率 fallback。
- 当 Yahoo 分红为空且标的属于国内 ETF 时：
  - 通过 `AkShare fund_portfolio_hold_em` 获取 ETF 最新披露持仓。
  - 将成分股代码映射为 Yahoo 行情代码。
  - 批量拉取成分股最近 2 年价格和分红。
  - 用最近 12 个月每只成分股的 `TTM 分红 / 最新股价` 计算成分股股息率。
  - 按 ETF 最新披露权重加总，得到 ETF 估算股息率。
  - 再按 `ETF 当前价格 × 估算股息率` 回推出 `latest_dividend_ttm`。
- 同时修正年度分红缓存逻辑：
  - 只有存在实际分红的年份才写入年度分红表。
  - 避免 ETF 明细页出现只有价格、没有分红却显示为 `0%` 的历史年份。

## 结果

以 `512890.SH` 为例：

- 修复前：
  - `current_dividend_yield = 0`
  - `latest_dividend_ttm = 0`
  - `sync_message = price=yfinance, dividend=yfinance`
- 修复后：
  - `current_dividend_yield = 4.95`
  - `latest_dividend_ttm = 0.0594`
  - `sync_message = price=yfinance, dividend=akshare-etf-holdings:2025年4季度股票投资明细`

## 验证

- 本地验证：
  - `python3 -m py_compile backend/app/services/provider.py`
  - 使用临时 SQLite 库执行 `refresh_stock`，确认 `512890` 能返回非零股息率。
- 口径校验：
  - 持仓反推结果：`4.95%`
  - 官方中证红利低波动指数股息率：`5.01%`
  - 差值：`0.06` 个百分点
  - 相对误差：约 `1.20%`
- 线上验证：
  - 已部署到 `192.168.50.7:8000`
  - `GET /api/stocks` 返回 `512890.SH.current_dividend_yield = 4.95`
  - `POST /api/stocks/1/refresh` 返回 `latest_dividend_ttm = 0.0594`

## 备注

- 该口径属于“持仓反推估算”，不是基金公司或指数公司直接披露的 ETF 官方股息率。
- 前端当前仍显示“当前股息率”，如果需要更严谨，可进一步改成“估算股息率”并加来源提示。
