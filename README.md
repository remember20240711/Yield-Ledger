# 息流账本 / Dividend Ledger

中文 | [English](README.en.md)

息流账本（Dividend Ledger），一个主要面向股票股息投资者的开源研究与持仓跟踪工具，支持 A 股、港股、美股的持仓录入、股息缓存、组合汇总与导入导出。

## 这是什么版本

这个仓库当前只包含 1 条产品线：

- `Web 自托管版`：主版本，也是本仓库默认推荐版本。技术栈是 `Vue 3 + FastAPI + SQLite`，通过 `Docker Compose` 启动，适合放在个人电脑、小主机、NAS、PVE LXC/VM 上长期运行。

如果你是从 GitHub 下载项目，并且想在浏览器里使用，那么你应该使用：

- `Web 自托管版`

当前仓库主线可视为：

- `Web 自托管版 v1.0.0`

这是目前仓库里最完整、最适合公开发布和持续使用的版本。

## 我应该用哪个版本

- 想要最快开始，且能接受先安装 Docker：使用 `Web 自托管版`
- 想部署到 PVE、NAS、小主机，长期运行：使用 `Web 自托管版`

## 核心功能

- 顶部汇总卡片展示持仓总市值、每年预计总分红、组合整体股息率
- 主表格展示每只股票的持仓汇总
- 添加持仓时立即同步该股票价格与分红缓存
- 买入或卖出后立即重算持仓，并刷新该股票缓存
- 持仓详情弹窗展示历史交易明细
- 点击当前股息率可查看最近 5 年股息率
- 删除股票时二次确认
- 支持 Excel 导出与 JSON 导入/导出，便于备份、迁移、恢复
- 持仓数据后台每 `30` 分钟自动刷新一次
- 每日 `03:00` 额外刷新一次持仓数据

## 技术栈

- 前端：Vue 3 + Vite + Element Plus + ECharts
- 后端：FastAPI + SQLAlchemy + APScheduler
- 数据库：SQLite
- 数据源：
  - 行情与分红：AkShare / yfinance / Yahoo Finance HTTP fallback
- 部署：
  - 主版本：Docker Compose
  - PVE / LXC：可用 Docker 部署，也可按环境改为原生 systemd 部署

## GitHub 下载后怎么用

你有两种获取方式：

1. `git clone`

```bash
git clone https://github.com/remember20240711/Yield-Ledger.git
cd Yield-Ledger
```

2. GitHub 页面点击 `Code` -> `Download ZIP`

下载后解压，进入项目根目录。

### 推荐方式：Docker 一键启动

这是当前仓库默认支持、也是最稳定的公开使用方式。

前提条件：

- 已安装 `Docker`
- 已安装或内置 `docker compose`
- Docker Desktop / Docker Engine 已经启动

macOS / Linux：

```bash
chmod +x ./start
./start
```

Windows：

- 双击运行 `start.bat`

启动脚本会自动：

- 检查 `docker` 是否存在
- 检查 `docker compose` 是否可用
- 首次自动创建 `.env`
- 自动创建 `data/`
- 执行 `docker compose up -d --build`
- 在桌面环境尝试打开 `http://127.0.0.1:8000`

启动成功后，浏览器访问：

- `http://127.0.0.1:8000`

## 手动 Docker 使用方式

如果你不想用 `start` 脚本，也可以手动执行：

```bash
cp .env.example .env
docker compose up -d --build
```

常用命令：

```bash
docker compose ps
docker compose logs -f --tail=200
docker compose down
docker compose up -d --build
```

代码更新后重新部署：

```bash
git pull
docker compose up -d --build
```

## 使用流程

第一次进入系统后，建议按下面顺序操作：

1. 点击“添加持仓”
2. 输入股票名称或代码，选择标的
3. 录入首次建仓日期、数量、成本价
4. 保存后，系统会把这只股票加入持仓列表
5. 后续可以继续对同一标的执行“买入”或“卖出”
6. 点击“当前股息率”可查看该股票最近 5 年股息率详情
7. 使用导入 / 导出功能进行备份和迁移

## 数据保存在哪里

Web 自托管版的数据默认保存在：

- `data/dividend_tracker.db`

这是 SQLite 单文件数据库，适合个人使用和备份。

如果你使用 Docker Compose，主机目录 `./data` 会挂载到容器内 `/app/data`，因此：

- 重建容器不会丢失数据
- 只要保留 `data/` 目录，就能保留历史持仓和缓存

## 备份与迁移

目前有 3 种备份方式：

- 直接备份 `data/dividend_tracker.db`
- 在前端导出 `Excel`
- 在前端导出 `JSON`

推荐做法：

- 日常迁移用 `Excel / JSON`
- 完整冷备份用 `data/dividend_tracker.db`

## 配置说明

首次启动时，脚本会根据 `.env.example` 自动生成 `.env`。

常用配置项：

- `DATABASE_URL`
  - SQLite 数据库路径
- `TIMEZONE`
  - 时区，默认 `Asia/Shanghai`
- `SCHEDULER_ENABLED`
  - 是否启用后台定时任务
- `HOLDINGS_REFRESH_MINUTES`
  - 持仓刷新间隔，默认 `30`
- `HOLDINGS_DAILY_REFRESH_HOUR`
  - 每日额外刷新小时，默认 `3`
- `HOLDINGS_DAILY_REFRESH_MINUTE`
  - 每日额外刷新分钟，默认 `0`
- `BASE_CURRENCY`
  - 组合汇总基准币种，默认 `CNY`
- `USD_TO_CNY`
  - 美元换算汇率
- `HKD_TO_CNY`
  - 港币换算汇率

## 汇率与汇总说明

- 当前股价、持仓详情中的价格按股票原币种展示
- 顶部汇总及主表中的市值、总成本、盈亏、预计分红按 `BASE_CURRENCY` 汇总估算
- 默认基准币种是 `CNY`
- 默认汇率来自 `.env`

这是轻量化方案，适合个人长期部署。当前实现未按交易日历史汇率换算成本。

## PVE / LXC 部署说明

如果你要部署在 PVE，推荐方式是：

- 新建一个独立的 Debian LXC 或 VM
- 在该容器或虚拟机中运行本项目

推荐原因：

- 与其他业务隔离更清晰
- 数据目录更容易独立备份
- 比直接堆在 PVE 宿主机上更安全、更规整

标准 Docker 部署路径：

```bash
git clone https://github.com/remember20240711/Yield-Ledger.git /opt/yield-ledger
cd /opt/yield-ledger
./start
```

如果你的 PVE 宿主机或 LXC 对 Docker 有额外限制，也可以改成：

- 原生 Python 虚拟环境
- `systemd` 托管 `uvicorn`

也就是说，仓库的主版本是 `Docker 版`，但在 PVE 环境里，允许按实际限制切换为 `systemd` 方式运行同一套 Web 代码。

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
│  ├─ package-lock.json
│  ├─ tsconfig.json
│  └─ vite.config.ts
├─ data/
├─ deploy/
├─ Dockerfile
├─ docker-compose.yml
├─ .env.example
├─ start
├─ start.bat
├─ README.md
└─ README.en.md
```

## 数据库表结构

完整建表 SQL 见 [backend/schema.sql](backend/schema.sql)。

核心表：

- `stocks`：股票基本信息、缓存价格、TTM 分红、股息率、同步状态
- `transactions`：每笔买入 / 卖出记录
- `dividends`：分红历史缓存，按股票与年份唯一

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

## 常见问题

### 1. 这是下载后直接双击就能用的桌面版吗？

不是。

当前仓库主版本是：

- `Web 自托管版`

它支持一键启动，但前提是你已经安装了 `Docker`。

### 2. 我下载后应该运行哪个文件？

- macOS / Linux：`./start`
- Windows：`start.bat`

### 3. 数据放在哪里？

- `data/dividend_tracker.db`

### 4. 更新代码后怎么升级？

```bash
git pull
docker compose up -d --build
```

### 5. 哪个版本最适合普通用户？

如果你想在浏览器里用，并且能安装 Docker，那么最推荐：

- `Web 自托管版`
