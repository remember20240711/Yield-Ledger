from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


# 这里集中定义 API 的请求体和响应体，避免前后端字段口径漂移。
class CreateStockRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    symbol: str = Field(min_length=1, max_length=32)
    trade_date: date
    shares: int = Field(ge=1)
    average_price: float = Field(gt=0)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip()


class CreateTransactionRequest(BaseModel):
    transaction_type: Literal["buy", "sell"] = "buy"
    trade_date: date
    shares: int = Field(ge=1)
    average_price: float = Field(gt=0)


class StockSearchItem(BaseModel):
    symbol: str
    normalized_symbol: str
    name: str
    market: str
    currency: str
    current_price: Optional[float] = None


class StockSearchResponse(BaseModel):
    items: list[StockSearchItem]


class StockRowResponse(BaseModel):
    id: int
    symbol: str
    normalized_symbol: str
    name: str
    market: str
    currency: str
    base_currency: str
    fx_rate_to_base: float
    total_shares: float
    current_price: float
    market_value: float
    average_cost: float
    total_cost: float
    profit_loss: float
    current_dividend_yield: float
    five_year_avg_yield: float
    ten_year_avg_yield: float
    annual_dividend: float
    latest_dividend_ttm: float
    latest_buy_price: float
    last_synced_at: Optional[datetime]
    sync_status: str
    sync_message: Optional[str] = None


class StockListResponse(BaseModel):
    items: list[StockRowResponse]
    base_currency: str


class PortfolioSummaryResponse(BaseModel):
    total_market_value: float
    total_annual_dividend: float
    overall_dividend_yield: float
    base_currency: str
    stock_count: int


class TransactionRecord(BaseModel):
    id: int
    transaction_type: Literal["buy", "sell"]
    trade_date: date
    shares: float
    average_price: float
    total_amount: float


class TransactionDetailResponse(BaseModel):
    stock_id: int
    symbol: str
    name: str
    currency: str
    transactions: list[TransactionRecord]
    total_shares: float
    average_cost: float
    total_cost: float


class DividendRecord(BaseModel):
    year: int
    dividend_per_share: float
    dividend_yield: float
    close_price: float
    currency: str
    source: str


class QuarterlyPriceRecord(BaseModel):
    label: str
    close_price: float
    year: int
    quarter: int


class DividendDetailResponse(BaseModel):
    stock_id: int
    symbol: str
    name: str
    currency: str
    latest_dividend_ttm: float
    current_dividend_yield: float
    dividends: list[DividendRecord]
    quarterly_prices: list[QuarterlyPriceRecord]


class PortfolioBackupTransaction(BaseModel):
    transaction_type: Literal["buy", "sell"]
    trade_date: date
    shares: float = Field(ge=0)
    average_price: float = Field(ge=0)
    total_amount: float = Field(ge=0)


class PortfolioBackupDividend(BaseModel):
    year: int
    dividend_per_share: float
    dividend_yield: float
    close_price: float
    currency: str
    source: str


class PortfolioBackupStock(BaseModel):
    symbol: str
    normalized_symbol: str
    name: str
    market: str
    currency: str
    last_price: Optional[float] = None
    latest_dividend_ttm: float = 0
    current_dividend_yield: float = 0
    five_year_avg_yield: float = 0
    ten_year_avg_yield: float = 0
    last_synced_at: Optional[datetime] = None
    sync_status: str = "pending"
    sync_message: Optional[str] = None
    transactions: list[PortfolioBackupTransaction] = Field(default_factory=list)
    dividends: list[PortfolioBackupDividend] = Field(default_factory=list)


class PortfolioExportResponse(BaseModel):
    version: str
    exported_at: datetime
    stocks: list[PortfolioBackupStock]


class PortfolioImportRequest(BaseModel):
    version: Optional[str] = None
    mode: Literal["replace", "merge"] = "replace"
    stocks: list[PortfolioBackupStock] = Field(default_factory=list)


class PortfolioImportResponse(BaseModel):
    imported_stocks: int
    imported_transactions: int
    imported_dividends: int
