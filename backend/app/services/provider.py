from __future__ import annotations

from dataclasses import dataclass
import logging
from datetime import datetime, timezone
from decimal import Decimal
import re
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


@dataclass
class DividendFallbackEstimate:
    latest_dividend_ttm: Decimal
    current_dividend_yield: Decimal
    source: str


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
            if dividend_per_share <= 0:
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

    @staticmethod
    def _parse_cn_fund_quarter_label(label: Any) -> tuple[int, int]:
        match = re.search(r"(\d{4})年(\d)季度", str(label))
        if not match:
            return 0, 0
        return int(match.group(1)), int(match.group(2))

    def _load_latest_etf_holdings(self, fund_code: str) -> tuple[Optional[pd.DataFrame], Optional[str]]:
        if ak is None:
            return None, None

        current_year = datetime.now(timezone.utc).year
        for year in range(current_year, current_year - 3, -1):
            try:
                frame = ak.fund_portfolio_hold_em(symbol=fund_code, date=str(year))
            except Exception:
                continue
            if frame is None or frame.empty or "季度" not in frame.columns:
                continue

            labels = [label for label in frame["季度"].dropna().astype(str).unique().tolist() if label]
            if not labels:
                continue
            latest_label = max(labels, key=self._parse_cn_fund_quarter_label)
            latest = frame[frame["季度"].astype(str) == latest_label].copy()
            if latest.empty:
                continue
            return latest, latest_label
        return None, None

    def estimate_etf_dividend_from_holdings(
        self,
        resolved: ResolvedSymbol,
        current_price: Optional[Decimal],
    ) -> Optional[DividendFallbackEstimate]:
        if ak is None or current_price is None or current_price <= 0:
            return None

        fund_code = resolved.normalized_symbol.split(".")[0]
        holdings, quarter_label = self._load_latest_etf_holdings(fund_code)
        if holdings is None or holdings.empty or quarter_label is None:
            return None

        if "占净值比例" not in holdings.columns or "股票代码" not in holdings.columns:
            return None

        holdings["weight"] = pd.to_numeric(holdings["占净值比例"], errors="coerce").fillna(0.0)
        holdings["stock_code"] = holdings["股票代码"].astype(str).str.extract(r"(\d{6})", expand=False)
        holdings = holdings[(holdings["weight"] > 0) & holdings["stock_code"].notna()].copy()
        if holdings.empty:
            return None

        total_weight = float(holdings["weight"].sum())
        if total_weight < 50:
            return None

        holdings["yahoo_symbol"] = holdings["stock_code"].map(
            lambda code: f"{code}.SS" if code.startswith(("5", "6", "9")) else f"{code}.SZ"
        )
        yahoo_symbols = holdings["yahoo_symbol"].dropna().unique().tolist()
        if not yahoo_symbols:
            return None

        try:
            batch = yf.download(
                yahoo_symbols,
                period="2y",
                interval="1d",
                auto_adjust=False,
                actions=True,
                progress=False,
                group_by="ticker",
                threads=True,
            )
        except Exception:
            return None
        if batch is None or batch.empty:
            return None

        yields: dict[str, float] = {}
        if isinstance(batch.columns, pd.MultiIndex):
            tickers = batch.columns.get_level_values(0).unique().tolist()
            for symbol in tickers:
                try:
                    symbol_frame = batch[symbol]
                except Exception:
                    continue
                close_series = symbol_frame.get("Close")
                if close_series is None:
                    continue
                close_series = close_series.dropna()
                if close_series.empty:
                    continue
                latest_close = float(close_series.iloc[-1])
                if latest_close <= 0:
                    continue
                dividends = symbol_frame.get("Dividends")
                if dividends is None:
                    ttm_dividend = 0.0
                else:
                    dividends = dividends.dropna()
                    cutoff = close_series.index.max() - pd.Timedelta(days=365)
                    ttm_dividend = float(dividends[dividends.index >= cutoff].sum()) if not dividends.empty else 0.0
                yields[str(symbol)] = (ttm_dividend / latest_close) * 100 if ttm_dividend > 0 else 0.0
        else:
            close_series = batch.get("Close")
            if close_series is not None:
                close_series = close_series.dropna()
                if not close_series.empty:
                    latest_close = float(close_series.iloc[-1])
                    dividends = batch.get("Dividends")
                    dividends = dividends.dropna() if dividends is not None else pd.Series(dtype="float64")
                    cutoff = close_series.index.max() - pd.Timedelta(days=365)
                    ttm_dividend = float(dividends[dividends.index >= cutoff].sum()) if not dividends.empty else 0.0
                    yields[yahoo_symbols[0]] = (ttm_dividend / latest_close) * 100 if latest_close > 0 else 0.0

        if not yields:
            return None

        holdings["yield_pct"] = holdings["yahoo_symbol"].map(yields).fillna(0.0)
        covered_weight = float(holdings.loc[holdings["yahoo_symbol"].isin(yields.keys()), "weight"].sum())
        if covered_weight < total_weight * 0.7:
            return None

        weighted_yield = float((holdings["weight"] * holdings["yield_pct"]).sum()) / total_weight
        if weighted_yield <= 0:
            return None

        current_dividend_yield = pct(weighted_yield)
        latest_dividend_ttm = price((current_price * current_dividend_yield) / Decimal("100"))
        return DividendFallbackEstimate(
            latest_dividend_ttm=latest_dividend_ttm,
            current_dividend_yield=current_dividend_yield,
            source=f"akshare-etf-holdings:{quarter_label}",
        )


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
            if dividend_per_share <= 0:
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

    @staticmethod
    def _should_estimate_cn_etf_yield(resolved: ResolvedSymbol, *name_candidates: Optional[str]) -> bool:
        if resolved.market != "CN":
            return False
        code = resolved.normalized_symbol.split(".")[0]
        if code.startswith(("5", "1")):
            return True
        combined_name = " ".join(filter(None, name_candidates)).upper()
        return "ETF" in combined_name

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
        dividend_provider = ""

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
        dividend_provider = snapshot_provider

        if (
            self._should_estimate_cn_etf_yield(resolved, stock.name, catalog_name, china_name)
            and latest_dividend_ttm <= 0
            and current_dividend_yield <= 0
            and snapshot_price
            and snapshot_price > 0
        ):
            fallback_estimate = self.ak_provider.estimate_etf_dividend_from_holdings(resolved, snapshot_price)
            if fallback_estimate is not None:
                latest_dividend_ttm = fallback_estimate.latest_dividend_ttm
                current_dividend_yield = fallback_estimate.current_dividend_yield
                dividend_provider = fallback_estimate.source

        stock.name = snapshot_name
        stock.last_price = snapshot_price
        stock.latest_dividend_ttm = latest_dividend_ttm
        stock.current_dividend_yield = current_dividend_yield
        stock.five_year_avg_yield = self._average_yield(annual_dividends, 5)
        stock.ten_year_avg_yield = self._average_yield(annual_dividends, 10)
        stock.sync_status = "ok"
        stock.sync_message = f"price={ 'akshare' if china_price else snapshot_provider }, dividend={dividend_provider or snapshot_provider}"[:255]
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
