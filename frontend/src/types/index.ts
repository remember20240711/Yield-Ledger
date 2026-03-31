// 前后端共享的页面数据结构集中放在这里，便于统一字段口径。
export interface PortfolioSummary {
  total_market_value: number
  total_annual_dividend: number
  overall_dividend_yield: number
  total_latest_full_year_dividend: number
  overall_latest_full_year_yield: number
  base_currency: string
  stock_count: number
}

export interface StockRow {
  id: number
  symbol: string
  normalized_symbol: string
  name: string
  market: 'CN' | 'HK' | 'US'
  currency: string
  base_currency: string
  fx_rate_to_base: number
  total_shares: number
  current_price: number
  market_value: number
  average_cost: number
  total_cost: number
  profit_loss: number
  current_dividend_yield: number
  five_year_avg_yield: number
  ten_year_avg_yield: number
  annual_dividend: number
  latest_dividend_ttm: number
  latest_full_year: number
  latest_full_year_dividend: number
  latest_full_year_dividend_yield: number
  latest_full_year_annual_dividend: number
  latest_buy_price: number
  last_synced_at: string | null
  sync_status: string
  sync_message?: string | null
}

export interface StockSearchItem {
  symbol: string
  normalized_symbol: string
  name: string
  market: 'CN' | 'HK' | 'US'
  currency: string
  current_price: number | null
}

export interface StockSearchResponse {
  items: StockSearchItem[]
}

export interface StockListResponse {
  items: StockRow[]
  base_currency: string
}

export interface TransactionRecord {
  id: number
  transaction_type: 'buy' | 'sell'
  trade_date: string
  shares: number
  average_price: number
  total_amount: number
}

export interface TransactionDetail {
  stock_id: number
  symbol: string
  name: string
  currency: string
  transactions: TransactionRecord[]
  total_shares: number
  average_cost: number
  total_cost: number
}

export interface DividendRecord {
  year: number
  dividend_per_share: number
  dividend_yield: number
  close_price: number
  currency: string
  source: string
}

export interface QuarterlyPriceRecord {
  label: string
  close_price: number
  year: number
  quarter: number
}

export interface DividendDetail {
  stock_id: number
  symbol: string
  name: string
  currency: string
  latest_dividend_ttm: number
  current_dividend_yield: number
  latest_full_year: number
  latest_full_year_dividend: number
  latest_full_year_dividend_yield: number
  dividends: DividendRecord[]
  quarterly_prices: QuarterlyPriceRecord[]
}

export interface CreateStockPayload {
  name: string
  symbol: string
  trade_date: string
  shares: number
  average_price: number
}

export interface CreateTransactionPayload {
  transaction_type: 'buy' | 'sell'
  trade_date: string
  shares: number
  average_price: number
}

export interface PortfolioBackupTransaction {
  transaction_type: 'buy' | 'sell'
  trade_date: string
  shares: number
  average_price: number
  total_amount: number
}

export interface PortfolioBackupDividend {
  year: number
  dividend_per_share: number
  dividend_yield: number
  close_price: number
  currency: string
  source: string
}

export interface PortfolioBackupStock {
  symbol: string
  normalized_symbol: string
  name: string
  market: 'CN' | 'HK' | 'US'
  currency: string
  last_price: number | null
  latest_dividend_ttm: number
  current_dividend_yield: number
  five_year_avg_yield: number
  ten_year_avg_yield: number
  last_synced_at: string | null
  sync_status: string
  sync_message?: string | null
  transactions: PortfolioBackupTransaction[]
  dividends: PortfolioBackupDividend[]
}

export interface PortfolioBackupData {
  version?: string
  exported_at?: string
  mode?: 'replace' | 'merge'
  stocks: PortfolioBackupStock[]
}

export interface PortfolioImportResult {
  imported_stocks: number
  imported_transactions: number
  imported_dividends: number
}
