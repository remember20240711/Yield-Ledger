# Yield Ledger

[中文](README.md) | English

Yield Ledger is an open-source dividend research and portfolio tracking tool for long-term cashflow investors, supporting CN (A-share), HK, and US stocks.

## Tech Stack

- Frontend: Vue 3 + Vite + Element Plus + ECharts
- Backend: FastAPI + SQLAlchemy + APScheduler
- Database: SQLite
- Data sources:
  - Price and dividends: AkShare / yfinance / Yahoo Finance HTTP fallback
- Deployment: Single-container Docker Compose

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
│  ├─ tsconfig.json
│  └─ vite.config.ts
├─ data/
├─ Dockerfile
├─ docker-compose.yml
├─ .env.example
├─ start
├─ README.md
└─ README.en.md
```

## Database Schema

Full SQL schema: [backend/schema.sql](backend/schema.sql)

Core tables:

- `stocks`: stock master data, cached price, TTM dividend, yield, sync status
- `transactions`: buy/sell history
- `dividends`: cached dividend history, unique by stock + year

## Key Features

- Top summary cards: total market value, annual expected dividends, portfolio yield
- Unified holdings table for all stocks
- Auto cache refresh for a stock after adding a position
- Recalculate holdings and refresh stock cache after buy/sell
- Transaction history drawer per stock
- Clickable current yield with 5-year dividend-yield details
- Delete confirmation for stock removal
- Excel export and JSON import/export for backup and migration
- Background holdings refresh every `30` minutes
- Additional daily holdings refresh at `03:00`

## Currency & Aggregation

- Price fields in transaction and stock details are shown in each stock's native currency
- Portfolio totals (market value, cost, P/L, expected dividends) are aggregated in `BASE_CURRENCY`
- Default base currency: `CNY`
- Default FX rates from `.env`:
  - `USD_TO_CNY=7.20`
  - `HKD_TO_CNY=0.92`

This is a lightweight long-running setup for personal use. Current implementation does not convert historical costs by trade-date FX.

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

Frontend dev server proxies `/api` to `http://localhost:8000`.

## Docker Deployment

1. One-click start (recommended):

```bash
chmod +x ./start
./start
```

The script will:

- Validate `docker compose`
- Auto-create `.env` on first run
- Start containers
- Try opening `http://127.0.0.1:8000` on desktop environments

2. Manual mode (optional):

```bash
cp .env.example .env
docker compose up -d --build
```

## iOS Client (Local-first)

- Project path: `ios/YieldLedgerIOS.xcodeproj`
- Guide: `ios/README.md`
- Behavior: no self-hosted backend required; holdings/trades persisted locally; quotes refresh on app launch and foreground

## Common Config

Supported keys in `.env`:

- `DATABASE_URL`: SQLite file path
- `SCHEDULER_ENABLED`: enable/disable scheduler
- `HOLDINGS_REFRESH_MINUTES`: refresh interval (default `30`)
- `HOLDINGS_DAILY_REFRESH_HOUR` / `HOLDINGS_DAILY_REFRESH_MINUTE`: daily refresh time
- `BASE_CURRENCY`: base currency for portfolio aggregation (default `CNY`)
- `USD_TO_CNY` / `HKD_TO_CNY`: FX rates for aggregation

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
