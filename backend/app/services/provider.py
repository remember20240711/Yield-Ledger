from __future__ import annotations

from dataclasses import dataclass
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional, Tuple

import pandas as pd
import yfinance as yf
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.dividend import Dividend
from app.models.stock import Stock
from app.models.stock_catalog import StockCatalog
from app.services.market import MarketResolver, ResolvedSymbol
from app.services.yahoo_http import YahooHttpClient
from app.utils.numbers import as_float, money, pct, price, to_decimal

try:
    import akshare as ak
except Exception:  # pragma: no cover - runtime dependency fallback
    ak = None


logger = logging.getLogger(__name__)


def _contains_cjk(value: Optional[str]) -> bool:
    # 中文名优先保留，避免同步后又被英文覆盖。
    if not value:
        return False
    return any("\u4e00" <= char <= "\u9fff" for char in value)


@dataclass
class AnnualDividend:
    year: int
    dividend_per_share: Decimal
    dividend_yield: Decimal
    close_price: Decimal
    currency: str
    source: str


@dataclass
class QuarterlyPricePoint:
    label: str
    close_price: Decimal
    year: int
    quarter: int


@dataclass
class MarketSnapshot:
    name: Optional[str]
    current_price: Decimal
    latest_dividend_ttm: Decimal
    current_dividend_yield: Decimal
    annual_dividends: list[AnnualDividend]


class YahooFinanceProvider:
    def _load_history(self, resolved: ResolvedSymbol, period: str) -> pd.DataFrame:
        # 分红和价格都依赖历史序列，这里统一做基础清洗。
        ticker = yf.Ticker(resolved.yahoo_symbol)
        history = ticker.history(period=period, interval="1d", auto_adjust=False)
        if history.empty:
            raise ValueError(f"无法获取 {resolved.normalized_symbol} 的历史行情")
        history = history.dropna(subset=["Close"]).copy()
        history.index = pd.to_datetime(history.index).tz_localize(None)
        return history

    def fetch_snapshot(self, resolved: ResolvedSymbol) -> MarketSnapshot:
        ticker = yf.Ticker(resolved.yahoo_symbol)
        history = self._load_history(resolved, "11y")
        current_price = price(history["Close"].iloc[-1])

        dividends = ticker.dividends
        if dividends is None:
            dividends = pd.Series(dtype="float64")
        dividends = dividends.dropna().copy()
        if not dividends.empty:
            dividends.index = pd.to_datetime(dividends.index).tz_localize(None)

        cutoff = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=365)
        latest_dividend_ttm = price(dividends[dividends.index >= cutoff].sum() if not dividends.empty else 0)

        annual_dividend_series = (
            dividends.groupby(dividends.index.year).sum() if not dividends.empty else pd.Series(dtype="float64")
        )
        annual_close_series = history.groupby(history.index.year)["Close"].last()

        annual_records: list[AnnualDividend] = []
        for year in sorted(set(annual_close_series.index.tolist()) | set(annual_dividend_series.index.tolist())):
            dividend_per_share = price(annual_dividend_series.get(year, 0))
            close_price = price(annual_close_series.get(year, 0))
            if dividend_per_share <= 0 and close_price <= 0:
                continue
            dividend_yield = pct((dividend_per_share / close_price) * 100 if close_price > 0 else 0)
            annual_records.append(
                AnnualDividend(
                    year=int(year),
                    dividend_per_share=dividend_per_share,
                    dividend_yield=dividend_yield,
                    close_price=close_price,
                    currency=resolved.currency,
                    source="yfinance",
                )
            )

        info_name = None
        try:
            info = ticker.info or {}
            info_name = info.get("shortName") or info.get("longName") or info.get("displayName")
        except Exception:
            info_name = None

        current_dividend_yield = next(
            (item.dividend_yield for item in reversed(annual_records) if item.dividend_yield > 0),
            Decimal("0"),
        )
        return MarketSnapshot(
            name=info_name,
            current_price=current_price,
            latest_dividend_ttm=latest_dividend_ttm,
            current_dividend_yield=current_dividend_yield,
            annual_dividends=sorted(annual_records, key=lambda item: item.year),
        )

    def fetch_recent_quarterly_prices(self, resolved: ResolvedSymbol, years: int = 5) -> list[QuarterlyPricePoint]:
        history = self._load_history(resolved, f"{years + 1}y")
        quarterly_close = history.groupby([history.index.year, history.index.quarter])["Close"].last()
        points: list[QuarterlyPricePoint] = []
        for (year, quarter), close in quarterly_close.items():
            points.append(
                QuarterlyPricePoint(
                    label=f"{int(year)} Q{int(quarter)}",
                    close_price=price(close),
                    year=int(year),
                    quarter=int(quarter),
                )
            )
        return points[-years * 4 :]


class AkshareChinaProvider:
    @staticmethod
    def _parse_value_frame(frame: pd.DataFrame) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if frame is None or frame.empty:
            return result
        for _, row in frame.iterrows():
            key = str(row.iloc[0]).strip()
            value = row.iloc[1]
            result[key] = value
        return result

    def fetch_name_and_price(self, resolved: ResolvedSymbol) -> Tuple[Optional[str], Optional[Decimal]]:
        if ak is None:
            return None, None

        symbol = resolved.normalized_symbol.split(".")[0]
        name = None
        current_price = None

        try:
            info_df = ak.stock_individual_info_em(symbol=symbol)
            info_map = self._parse_value_frame(info_df)
            name = (
                info_map.get("股票简称")
                or info_map.get("证券简称")
                or info_map.get("简称")
                or info_map.get("股票名称")
            )
            if name is not None:
                name = str(name).strip()
        except Exception:
            name = None

        try:
            quote_df = ak.stock_bid_ask_em(symbol=symbol)
            quote_map = self._parse_value_frame(quote_df)
            raw_price = quote_map.get("最新") or quote_map.get("最新价") or quote_map.get("当前价")
            if raw_price not in (None, "", "-"):
                current_price = price(raw_price)
        except Exception:
            current_price = None

        return name, current_price


class YahooHttpProvider:
    def __init__(self) -> None:
        self.client = YahooHttpClient()

    def fetch_snapshot(self, resolved: ResolvedSymbol) -> MarketSnapshot:
        history, dividends = self.client.fetch_history_with_dividends(resolved.yahoo_symbol, years=11)
        quote = self.client.fetch_quote(resolved.yahoo_symbol)

        cutoff = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=365)
        latest_dividend_ttm = price(dividends[dividends.index >= cutoff].sum() if not dividends.empty else 0)
        annual_dividend_series = dividends.groupby(dividends.index.year).sum() if not dividends.empty else pd.Series(dtype="float64")
        annual_close_series = history.groupby(history.index.year)["Close"].last()

        annual_records: list[AnnualDividend] = []
        for year in sorted(set(annual_close_series.index.tolist()) | set(annual_dividend_series.index.tolist())):
            dividend_per_share = price(annual_dividend_series.get(year, 0))
            close_price = price(annual_close_series.get(year, 0))
            if dividend_per_share <= 0 and close_price <= 0:
                continue
            dividend_yield = pct((dividend_per_share / close_price) * 100 if close_price > 0 else 0)
            annual_records.append(
                AnnualDividend(
                    year=int(year),
                    dividend_per_share=dividend_per_share,
                    dividend_yield=dividend_yield,
                    close_price=close_price,
                    currency=resolved.currency,
                    source="yahoo-http",
                )
            )

        current_price = price(quote.price if quote.price is not None else history["Close"].iloc[-1])
        current_dividend_yield = (
            pct((latest_dividend_ttm / current_price) * 100 if current_price > 0 else 0) if current_price else Decimal("0")
        )
        if current_dividend_yield <= 0:
            current_dividend_yield = next(
                (item.dividend_yield for item in reversed(annual_records) if item.dividend_yield > 0),
                Decimal("0"),
            )

        return MarketSnapshot(
            name=quote.name,
            current_price=current_price,
            latest_dividend_ttm=latest_dividend_ttm,
            current_dividend_yield=current_dividend_yield,
            annual_dividends=sorted(annual_records, key=lambda item: item.year),
        )

    def fetch_recent_quarterly_prices(self, resolved: ResolvedSymbol, years: int = 5) -> list[QuarterlyPricePoint]:
        history, _ = self.client.fetch_history_with_dividends(resolved.yahoo_symbol, years=years + 1)
        quarterly_close = history.groupby([history.index.year, history.index.quarter])["Close"].last()
        points: list[QuarterlyPricePoint] = []
        for (year, quarter), close in quarterly_close.items():
            points.append(
                QuarterlyPricePoint(
                    label=f"{int(year)} Q{int(quarter)}",
                    close_price=price(close),
                    year=int(year),
                    quarter=int(quarter),
                )
            )
        return points[-years * 4 :]


class MarketDataService:
    def __init__(self) -> None:
        self.market_resolver = MarketResolver()
        self.yahoo_provider = YahooFinanceProvider()
        self.yahoo_http_provider = YahooHttpProvider()
        self.ak_provider = AkshareChinaProvider()

    def _fetch_snapshot(self, resolved: ResolvedSymbol) -> tuple[MarketSnapshot, str]:
        # 多数据源顺序尝试，返回命中的 provider 方便排查。
        errors: list[str] = []
        providers = [
            ("yfinance", self.yahoo_provider),
            ("yahoo-http", self.yahoo_http_provider),
        ]
        for provider_name, provider in providers:
            try:
                snapshot = provider.fetch_snapshot(resolved)
                logger.info("snapshot provider selected: %s for %s", provider_name, resolved.normalized_symbol)
                return snapshot, provider_name
            except Exception as exc:
                errors.append(f"{provider_name}: {exc}")
        raise ValueError(" ; ".join(errors) if errors else f"无法获取 {resolved.normalized_symbol} 的行情与分红")

    def _average_yield(self, dividends: list[AnnualDividend], years: int) -> Decimal:
        valid = [item.dividend_yield for item in dividends if item.dividend_yield > 0]
        if not valid:
            return Decimal("0")
        subset = valid[-years:] if len(valid) >= years else valid
        return pct(sum(subset) / len(subset))

    def refresh_stock(self, db: Session, stock: Stock) -> Stock:
        # 单只持仓刷新时会同时更新名称、价格、TTM 分红和年度股息缓存。
        resolved = ResolvedSymbol(
            original_symbol=stock.symbol,
            normalized_symbol=stock.normalized_symbol,
            yahoo_symbol=stock.yahoo_symbol,
            market=stock.market,
            currency=stock.currency,
        )

        yahoo_snapshot: Optional[MarketSnapshot] = None
        china_name: Optional[str] = None
        china_price: Optional[Decimal] = None
        snapshot_provider = ""

        if stock.market == "CN":
            china_name, china_price = self.ak_provider.fetch_name_and_price(resolved)

        catalog_name = db.scalar(
            select(StockCatalog.name).where(StockCatalog.normalized_symbol == resolved.normalized_symbol)
        )

        try:
            yahoo_snapshot, snapshot_provider = self._fetch_snapshot(resolved)
        except Exception as exc:
            if china_price is None and stock.last_price is None:
                stock.sync_status = "failed"
                stock.sync_message = str(exc)[:255]
                stock.last_synced_at = datetime.now(timezone.utc)
                db.add(stock)
                db.commit()
                db.refresh(stock)
                return stock

        snapshot_name = (
            stock.name
            if _contains_cjk(stock.name)
            else catalog_name or china_name or stock.name or (yahoo_snapshot.name if yahoo_snapshot else None)
        )
        snapshot_price = china_price or (yahoo_snapshot.current_price if yahoo_snapshot else None) or to_decimal(stock.last_price)
        latest_dividend_ttm = yahoo_snapshot.latest_dividend_ttm if yahoo_snapshot else Decimal("0")
        current_dividend_yield = (
            pct((latest_dividend_ttm / snapshot_price) * 100 if snapshot_price and snapshot_price > 0 else 0)
            if snapshot_price
            else (yahoo_snapshot.current_dividend_yield if yahoo_snapshot else Decimal("0"))
        )
        annual_dividends = yahoo_snapshot.annual_dividends if yahoo_snapshot else []

        stock.name = snapshot_name
        stock.last_price = snapshot_price
        stock.latest_dividend_ttm = latest_dividend_ttm
        stock.current_dividend_yield = current_dividend_yield
        stock.five_year_avg_yield = self._average_yield(annual_dividends, 5)
        stock.ten_year_avg_yield = self._average_yield(annual_dividends, 10)
        stock.sync_status = "ok"
        stock.sync_message = f"price={ 'akshare' if china_price else snapshot_provider }, dividend={snapshot_provider}"[:255]
        stock.last_synced_at = datetime.now(timezone.utc)
        db.add(stock)

        db.execute(delete(Dividend).where(Dividend.stock_id == stock.id))
        for record in annual_dividends[-10:]:
            db.add(
                Dividend(
                    stock_id=stock.id,
                    year=record.year,
                    dividend_per_share=record.dividend_per_share,
                    dividend_yield=record.dividend_yield,
                    close_price=record.close_price,
                    currency=record.currency,
                    source=record.source,
                )
            )

        db.commit()
        db.refresh(stock)
        return stock

    def refresh_stock_by_id(self, db: Session, stock_id: int) -> Stock:
        stock = db.get(Stock, stock_id)
        if stock is None:
            raise ValueError("股票不存在")
        return self.refresh_stock(db, stock)

    def refresh_all(self, db: Session) -> None:
        stocks = db.scalars(select(Stock)).all()
        for stock in stocks:
            self.refresh_stock(db, stock)

    def get_recent_quarterly_prices(self, stock: Stock, years: int = 5) -> list[QuarterlyPricePoint]:
        resolved = ResolvedSymbol(
            original_symbol=stock.symbol,
            normalized_symbol=stock.normalized_symbol,
            yahoo_symbol=stock.yahoo_symbol,
            market=stock.market,
            currency=stock.currency,
        )
        for provider_name, provider in (
            ("yfinance", self.yahoo_provider),
            ("yahoo-http", self.yahoo_http_provider),
        ):
            try:
                points = provider.fetch_recent_quarterly_prices(resolved, years)
                logger.info("quarterly price provider selected: %s for %s", provider_name, resolved.normalized_symbol)
                return points
            except Exception:
                continue
        return []


market_data_service = MarketDataService()
