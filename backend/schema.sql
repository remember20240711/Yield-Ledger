CREATE TABLE IF NOT EXISTS stocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol VARCHAR(32) NOT NULL,
    normalized_symbol VARCHAR(32) NOT NULL UNIQUE,
    yahoo_symbol VARCHAR(32) NOT NULL,
    name VARCHAR(128) NOT NULL,
    market VARCHAR(8) NOT NULL,
    currency VARCHAR(8) NOT NULL,
    last_price NUMERIC(18, 4),
    latest_dividend_ttm NUMERIC(18, 4) NOT NULL DEFAULT 0,
    current_dividend_yield NUMERIC(10, 4) NOT NULL DEFAULT 0,
    five_year_avg_yield NUMERIC(10, 4) NOT NULL DEFAULT 0,
    ten_year_avg_yield NUMERIC(10, 4) NOT NULL DEFAULT 0,
    last_synced_at DATETIME,
    sync_status VARCHAR(16) NOT NULL DEFAULT 'pending',
    sync_message VARCHAR(255),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id INTEGER NOT NULL,
    transaction_type VARCHAR(8) NOT NULL DEFAULT 'buy',
    trade_date DATE NOT NULL,
    shares NUMERIC(18, 4) NOT NULL,
    average_price NUMERIC(18, 4) NOT NULL,
    total_amount NUMERIC(18, 2) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (stock_id) REFERENCES stocks (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_transactions_stock_id ON transactions (stock_id);

CREATE TABLE IF NOT EXISTS dividends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    dividend_per_share NUMERIC(18, 4) NOT NULL DEFAULT 0,
    dividend_yield NUMERIC(10, 4),
    close_price NUMERIC(18, 4),
    currency VARCHAR(8) NOT NULL,
    source VARCHAR(32) NOT NULL DEFAULT 'cache',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (stock_id) REFERENCES stocks (id) ON DELETE CASCADE,
    UNIQUE (stock_id, year)
);

CREATE INDEX IF NOT EXISTS idx_dividends_stock_id ON dividends (stock_id);

CREATE TABLE IF NOT EXISTS stock_catalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol VARCHAR(32) NOT NULL,
    normalized_symbol VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    market VARCHAR(8) NOT NULL,
    currency VARCHAR(8) NOT NULL,
    last_price NUMERIC(18, 4),
    source VARCHAR(32) NOT NULL DEFAULT 'catalog',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_stock_catalog_symbol ON stock_catalog (symbol);
CREATE INDEX IF NOT EXISTS idx_stock_catalog_name ON stock_catalog (name);
CREATE INDEX IF NOT EXISTS idx_stock_catalog_market ON stock_catalog (market);

CREATE TABLE IF NOT EXISTS income_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    normalized_symbol VARCHAR(32) NOT NULL,
    market VARCHAR(8) NOT NULL,
    name VARCHAR(128) NOT NULL,
    recommendation VARCHAR(64) NOT NULL DEFAULT '待评估',
    verdict VARCHAR(64) NOT NULL DEFAULT '待评估',
    note VARCHAR(255),
    is_blacklisted BOOLEAN NOT NULL DEFAULT 0,
    total_score FLOAT NOT NULL DEFAULT 0,
    base_score FLOAT NOT NULL DEFAULT 0,
    bonus_score FLOAT NOT NULL DEFAULT 0,
    dividend_yield_score FLOAT NOT NULL DEFAULT 0,
    payout_ratio_score FLOAT NOT NULL DEFAULT 0,
    continuity_score FLOAT NOT NULL DEFAULT 0,
    fcf_score FLOAT NOT NULL DEFAULT 0,
    roe_score FLOAT NOT NULL DEFAULT 0,
    debt_score FLOAT NOT NULL DEFAULT 0,
    pe_score FLOAT NOT NULL DEFAULT 0,
    current_dividend_yield FLOAT,
    payout_ratio FLOAT,
    dividend_streak_years INTEGER,
    dividend_cagr_5y FLOAT,
    fcf_coverage FLOAT,
    roe_avg_3y FLOAT,
    debt_ratio FLOAT,
    pe_percentile_5y FLOAT,
    management_bonus FLOAT,
    data_status VARCHAR(32) NOT NULL DEFAULT 'pending',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_income_scores_market ON income_scores (market);
CREATE INDEX IF NOT EXISTS idx_income_scores_symbol ON income_scores (normalized_symbol);
