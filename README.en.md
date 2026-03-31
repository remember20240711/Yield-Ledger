# 息流账本 / Dividend Ledger

[中文](README.md) | English

Dividend Ledger is an open-source dividend research and portfolio tracking tool focused on stock dividend investors, with support for CN (A-share), HK, and US stocks.

## Which Version Is This

This repository currently contains only 1 product line:

- `Web self-hosted edition`: the main edition and the default recommendation for this repository. It is built with `Vue 3 + FastAPI + SQLite`, runs via `Docker Compose`, and is suitable for personal computers, mini PCs, NAS, and PVE LXC/VM deployments.

If you downloaded this project from GitHub and want to use it in a browser, you should use:

- `Web self-hosted edition`

The current repository mainline should be treated as:

- `Web self-hosted edition v1.0.0`

This is the most complete and publicly usable edition in the repo today.

## Which Version Should I Use

- If you want the quickest setup and can install Docker: use `Web self-hosted edition`
- If you want to deploy on PVE, NAS, or a mini server: use `Web self-hosted edition`

## Key Features

- Top summary cards for total market value, annual expected dividends, and portfolio yield
- Unified holdings table across all stocks
- Auto-refresh of price and dividend cache after adding a position
- Recalculation and cache refresh after each buy or sell
- Transaction history drawer per stock
- Clickable current yield with 5-year dividend yield detail
- Delete confirmation before removing a stock
- Excel export and JSON import/export for backup and migration
- Background holdings refresh every `30` minutes
- Additional daily holdings refresh at `03:00`

## Tech Stack

- Frontend: Vue 3 + Vite + Element Plus + ECharts
- Backend: FastAPI + SQLAlchemy + APScheduler
- Database: SQLite
- Data sources:
  - Prices and dividends: AkShare / yfinance / Yahoo Finance HTTP fallback
- Deployment:
  - Primary edition: Docker Compose
  - PVE / LXC: can run with Docker, or with native systemd depending on host restrictions

## How To Use It After Downloading From GitHub

You can get the project in 2 ways:

1. `git clone`

```bash
git clone https://github.com/remember20240711/Yield-Ledger.git
cd Yield-Ledger
```

2. GitHub UI -> `Code` -> `Download ZIP`

Then extract the archive and enter the project root directory.

### Recommended: One-Click Docker Start

This is the default and most stable public usage path for the repository.

Requirements:

- `Docker` is installed
- `docker compose` is available
- Docker Desktop / Docker Engine is already running

macOS / Linux:

```bash
chmod +x ./start
./start
```

Windows:

- Double-click `start.bat`

The startup script will automatically:

- Check whether `docker` exists
- Check whether `docker compose` is available
- Create `.env` on first launch
- Create `data/`
- Run `docker compose up -d --build`
- Try to open `http://127.0.0.1:8000` on desktop environments

After startup, open:

- `http://127.0.0.1:8000`

## Manual Docker Usage

If you prefer not to use the `start` script:

```bash
cp .env.example .env
docker compose up -d --build
```

Useful commands:

```bash
docker compose ps
docker compose logs -f --tail=200
docker compose down
docker compose up -d --build
```

To update after pulling new code:

```bash
git pull
docker compose up -d --build
```

## Typical User Flow

After first launch, the recommended flow is:

1. Click "Add Holding"
2. Search and choose a stock by name or code
3. Enter first buy date, shares, and cost price
4. Save and let the stock appear in the holdings table
5. Use "Buy" or "Sell" later for the same symbol
6. Click the current dividend yield to inspect 5-year yield details
7. Use import / export for backup and migration

## Where Data Is Stored

The Web self-hosted edition stores data in:

- `data/dividend_tracker.db`

This is a single SQLite file, which makes backup and migration straightforward.

With Docker Compose, the host `./data` directory is mounted into `/app/data` inside the container. That means:

- Rebuilding the container does not delete your portfolio data
- Keeping the `data/` directory is enough to preserve your history and cache

## Backup And Migration

You currently have 3 practical backup options:

- Back up `data/dividend_tracker.db`
- Export `Excel` from the UI
- Export `JSON` from the UI

Recommended usage:

- Use `Excel / JSON` for routine migration
- Use `data/dividend_tracker.db` for full cold backup

## Configuration

On first startup, the script will auto-create `.env` from `.env.example`.

Common config keys:

- `DATABASE_URL`
  - SQLite database path
- `TIMEZONE`
  - Timezone, default `Asia/Shanghai`
- `SCHEDULER_ENABLED`
  - Enable or disable background jobs
- `HOLDINGS_REFRESH_MINUTES`
  - Holdings refresh interval, default `30`
- `HOLDINGS_DAILY_REFRESH_HOUR`
  - Extra daily refresh hour, default `3`
- `HOLDINGS_DAILY_REFRESH_MINUTE`
  - Extra daily refresh minute, default `0`
- `BASE_CURRENCY`
  - Base currency for aggregated portfolio totals, default `CNY`
- `USD_TO_CNY`
  - USD conversion rate
- `HKD_TO_CNY`
  - HKD conversion rate

## Currency And Aggregation

- Price fields in holding detail views are shown in each stock's native currency
- Portfolio totals such as market value, cost, P/L, and expected dividends are aggregated in `BASE_CURRENCY`
- Default base currency is `CNY`
- Default FX values come from `.env`

This is a lightweight personal-use design. Historical trade-date FX conversion is not implemented yet.

## PVE / LXC Deployment Notes

If you want to deploy on PVE, the recommended way is:

- Create a dedicated Debian LXC or VM
- Run this project inside that container or VM

Why:

- Cleaner isolation from other services
- Easier independent backup of the data directory
- Safer and tidier than running everything directly on the PVE host

Standard Docker deployment path:

```bash
git clone https://github.com/remember20240711/Yield-Ledger.git /opt/yield-ledger
cd /opt/yield-ledger
./start
```

If your PVE host or LXC has Docker-related restrictions, you can also run the same Web codebase with:

- native Python virtualenv
- `systemd` + `uvicorn`

So the repository primary edition is still the `Docker edition`, but in PVE you may choose `systemd` deployment when the host environment requires it.

## Local Development

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server proxies `/api` to `http://localhost:8000`.

## Project Structure

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

## Database Schema

Full SQL schema: [backend/schema.sql](backend/schema.sql)

Core tables:

- `stocks`: stock master data, cached price, TTM dividend, yield, sync status
- `transactions`: buy / sell history
- `dividends`: cached dividend history, unique by stock + year

## API Overview

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

## FAQ

### 1. Is this a download-and-double-click desktop app?

No.

The primary public edition in this repo is:

- `Web self-hosted edition`

It supports one-click startup, but Docker must already be installed.

### 2. Which file should I run after downloading?

- macOS / Linux: `./start`
- Windows: `start.bat`

### 3. Where is my data stored?

- `data/dividend_tracker.db`

### 4. How do I update after new commits?

```bash
git pull
docker compose up -d --build
```

### 5. Which version is best for most users?

If you want to use the app in a browser and can install Docker, the best choice is:

- `Web self-hosted edition`
