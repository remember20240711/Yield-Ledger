# Yield Ledger

息流账本，一个面向长期现金流投资者的开源股息研究与持仓跟踪工具，支持 A 股、港股、美股的持仓录入、股息缓存与组合汇总。

## 技术栈

- 前端：Vue 3 + Vite + Element Plus + ECharts
- 后端：FastAPI + SQLAlchemy + APScheduler
- 数据库：SQLite
- 数据源：
  - 行情与分红：AkShare / yfinance / Yahoo Finance HTTP fallback
- 部署：Docker Compose 单容器部署

## 项目目录结构

```text
.
├─ backend/
│  ├─ app/
│  │  ├─ api/
│  │  ├─ core/
│  │  ├─ db/
│  │  ├─ models/
│  │  ├─ schemas/
│  │  ├─ services/
│  │  ├─ tasks/
│  │  ├─ utils/
│  │  ├─ static/
│  │  └─ main.py
│  ├─ requirements.txt
│  └─ schema.sql
├─ frontend/
│  ├─ src/
│  │  ├─ api/
│  │  ├─ components/
│  │  ├─ types/
│  │  ├─ utils/
│  │  ├─ App.vue
│  │  ├─ main.ts
│  │  └─ style.css
│  ├─ index.html
│  ├─ package.json
│  ├─ tsconfig.json
│  └─ vite.config.ts
├─ data/
├─ Dockerfile
├─ docker-compose.yml
├─ .env.example
└─ README.md
```

## 数据库表结构

完整建表 SQL 见 [backend/schema.sql](/Users/kaiqizhuang/股息/backend/schema.sql)。

核心表：

- `stocks`：股票基本信息、缓存价格、TTM 分红、股息率、同步状态
- `transactions`：每笔买入/卖出记录
- `dividends`：分红历史缓存，按股票与年份唯一

## 核心功能

- 顶部汇总卡片展示持仓总市值、每年预计总分红、组合整体股息率
- 主表格展示每只股票的持仓汇总
- 添加持仓时立即同步该股票价格与分红缓存
- 买入或卖出后立即重算持仓，并刷新该股票缓存
- 持仓详情弹窗展示历史交易明细
- 点击当前股息率可查看最近 5 年股息率
- 删除股票时二次确认
- 支持 Excel 导出与 JSON 导入/导出（可备份、迁移、恢复）
- 持仓数据后台每 `30` 分钟自动刷新一次
- 每日 `03:00` 只额外刷新持仓数据

## 汇率与汇总说明

- 当前股价、持仓均价、持仓详情中的价格按股票原币种展示
- 顶部汇总及主表中的市值、总成本、盈亏、预计分红按 `BASE_CURRENCY` 汇总估算
- 默认基准币种是 `CNY`
- 默认汇率来自 `.env`：
  - `USD_TO_CNY=7.20`
  - `HKD_TO_CNY=0.92`

这是轻量化方案，适合个人长期部署。当前实现未按交易日历史汇率换算成本。

## 本地开发

### 后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端开发环境会把 `/api` 代理到 `http://localhost:8000`。

## Docker 部署

1. 创建环境文件：

```bash
cp .env.example .env
```

2. 启动服务：

```bash
docker-compose up -d --build
```

3. 打开浏览器：

```text
http://<你的主机IP>:8000
```

## 常用配置

`.env` 支持以下关键配置：

- `DATABASE_URL`：SQLite 文件路径
- `SCHEDULER_ENABLED`：是否启用每日定时刷新
- `HOLDINGS_REFRESH_MINUTES`：持仓刷新间隔，默认 `30`
- `HOLDINGS_DAILY_REFRESH_HOUR` / `HOLDINGS_DAILY_REFRESH_MINUTE`：每日持仓刷新时间
- `BASE_CURRENCY`：组合汇总基准币种，默认 `CNY`
- `USD_TO_CNY` / `HKD_TO_CNY`：汇总换算汇率

## API 概览

- `GET /api/summary`
- `GET /api/stocks`
- `POST /api/stocks`
- `POST /api/stocks/{id}/transactions`
- `GET /api/stocks/{id}/transactions`
- `GET /api/stocks/{id}/dividends`
- `POST /api/stocks/{id}/refresh`
- `POST /api/refresh`
- `GET /api/portfolio/export`
- `GET /api/portfolio/export.xlsx`
- `POST /api/portfolio/import`
- `DELETE /api/stocks/{id}`
