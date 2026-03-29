from __future__ import annotations

from dataclasses import dataclass
import logging
from datetime import datetime, timedelta, timezone
import time
from decimal import Decimal
from typing import Optional

import pandas as pd
import yfinance as yf
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.income_score import IncomeScore
from app.models.stock_catalog import StockCatalog
from app.services.market import MarketResolver
from app.services.yahoo_http import YahooHttpClient, extract_raw
from app.utils.numbers import as_float, pct, price, to_decimal


@dataclass
class ScoreCandidate:
    symbol: str
    name: str
    market: str


@dataclass
class ScoreMetrics:
    name: str
    market: str
    normalized_symbol: str
    profile: str
    current_dividend_yield: Optional[Decimal]
    payout_ratio: Optional[Decimal]
    dividend_streak_years: int
    dividend_cagr_5y: Optional[Decimal]
    fcf_coverage: Optional[Decimal]
    roe_avg_3y: Optional[Decimal]
    debt_ratio: Optional[Decimal]
    pe_percentile_5y: Optional[Decimal]
    management_bonus: Decimal
    note: Optional[str]


CN_UNIVERSE = [
    ScoreCandidate("600900", "长江电力", "CN"),
    ScoreCandidate("600919", "江苏银行", "CN"),
    ScoreCandidate("601398", "工商银行", "CN"),
    ScoreCandidate("601939", "建设银行", "CN"),
    ScoreCandidate("601288", "农业银行", "CN"),
    ScoreCandidate("601988", "中国银行", "CN"),
    ScoreCandidate("601328", "交通银行", "CN"),
    ScoreCandidate("600036", "招商银行", "CN"),
    ScoreCandidate("601166", "兴业银行", "CN"),
    ScoreCandidate("601169", "北京银行", "CN"),
    ScoreCandidate("601818", "光大银行", "CN"),
    ScoreCandidate("601009", "南京银行", "CN"),
    ScoreCandidate("601229", "上海银行", "CN"),
    ScoreCandidate("601658", "邮储银行", "CN"),
    ScoreCandidate("601088", "中国神华", "CN"),
    ScoreCandidate("600188", "兖矿能源", "CN"),
    ScoreCandidate("601225", "陕西煤业", "CN"),
    ScoreCandidate("600028", "中国石化", "CN"),
    ScoreCandidate("601857", "中国石油", "CN"),
    ScoreCandidate("600050", "中国联通", "CN"),
    ScoreCandidate("601728", "中国电信", "CN"),
    ScoreCandidate("601985", "中国核电", "CN"),
    ScoreCandidate("600011", "华能国际", "CN"),
    ScoreCandidate("600027", "华电国际", "CN"),
    ScoreCandidate("600886", "国投电力", "CN"),
]

HK_UNIVERSE = [
    ScoreCandidate("00005.HK", "汇丰控股", "HK"),
    ScoreCandidate("00011.HK", "恒生银行", "HK"),
    ScoreCandidate("02388.HK", "中银香港", "HK"),
    ScoreCandidate("00939.HK", "建设银行", "HK"),
    ScoreCandidate("01398.HK", "工商银行", "HK"),
    ScoreCandidate("03988.HK", "中国银行", "HK"),
    ScoreCandidate("01288.HK", "农业银行", "HK"),
    ScoreCandidate("03328.HK", "交通银行", "HK"),
    ScoreCandidate("00883.HK", "中国海洋石油", "HK"),
    ScoreCandidate("00386.HK", "中国石油化工股份", "HK"),
    ScoreCandidate("00857.HK", "中国石油股份", "HK"),
    ScoreCandidate("00941.HK", "中国移动", "HK"),
    ScoreCandidate("00728.HK", "中国电信", "HK"),
    ScoreCandidate("00762.HK", "中国联通", "HK"),
    ScoreCandidate("00002.HK", "中电控股", "HK"),
    ScoreCandidate("00006.HK", "电能实业", "HK"),
    ScoreCandidate("01038.HK", "长江基建集团", "HK"),
    ScoreCandidate("00823.HK", "领展房产基金", "HK"),
    ScoreCandidate("00003.HK", "香港中华煤气", "HK"),
    ScoreCandidate("00016.HK", "新鸿基地产", "HK"),
    ScoreCandidate("01109.HK", "华润置地", "HK"),
    ScoreCandidate("01928.HK", "金沙中国有限公司", "HK"),
]

US_UNIVERSE = [
    ScoreCandidate("KO", "Coca-Cola", "US"),
    ScoreCandidate("PEP", "PepsiCo", "US"),
    ScoreCandidate("PG", "Procter & Gamble", "US"),
    ScoreCandidate("JNJ", "Johnson & Johnson", "US"),
    ScoreCandidate("ABBV", "AbbVie", "US"),
    ScoreCandidate("XOM", "Exxon Mobil", "US"),
    ScoreCandidate("CVX", "Chevron", "US"),
    ScoreCandidate("T", "AT&T", "US"),
    ScoreCandidate("VZ", "Verizon", "US"),
    ScoreCandidate("MO", "Altria", "US"),
    ScoreCandidate("PM", "Philip Morris", "US"),
    ScoreCandidate("IBM", "IBM", "US"),
    ScoreCandidate("O", "Realty Income", "US"),
    ScoreCandidate("NNN", "NNN REIT", "US"),
    ScoreCandidate("WPC", "W. P. Carey", "US"),
    ScoreCandidate("MCD", "McDonald's", "US"),
    ScoreCandidate("HD", "Home Depot", "US"),
    ScoreCandidate("LOW", "Lowe's", "US"),
    ScoreCandidate("ADP", "ADP", "US"),
    ScoreCandidate("BLK", "BlackRock", "US"),
    ScoreCandidate("UPS", "UPS", "US"),
    ScoreCandidate("PFE", "Pfizer", "US"),
    ScoreCandidate("BMY", "Bristol Myers Squibb", "US"),
    ScoreCandidate("MDT", "Medtronic", "US"),
    ScoreCandidate("KMB", "Kimberly-Clark", "US"),
]

UNIVERSE_BY_MARKET = {
    "CN": CN_UNIVERSE,
    "HK": HK_UNIVERSE,
    "US": US_UNIVERSE,
}

RAW_PROFILE_BY_SYMBOL = {
    "600919": "financial",
    "601398": "financial",
    "601939": "financial",
    "601288": "financial",
    "601988": "financial",
    "601328": "financial",
    "600036": "financial",
    "601166": "financial",
    "601169": "financial",
    "601818": "financial",
    "601009": "financial",
    "601229": "financial",
    "601658": "financial",
    "00005.HK": "financial",
    "00011.HK": "financial",
    "02388.HK": "financial",
    "00939.HK": "financial",
    "01398.HK": "financial",
    "03988.HK": "financial",
    "01288.HK": "financial",
    "03328.HK": "financial",
    "BLK": "financial",
    "00823.HK": "reit",
    "O": "reit",
    "NNN": "reit",
    "WPC": "reit",
    "600900": "stable",
    "600050": "stable",
    "601728": "stable",
    "601985": "stable",
    "600011": "stable",
    "600027": "stable",
    "600886": "stable",
    "00941.HK": "stable",
    "00728.HK": "stable",
    "00762.HK": "stable",
    "00002.HK": "stable",
    "00006.HK": "stable",
    "01038.HK": "stable",
    "00003.HK": "stable",
    "KO": "stable",
    "PEP": "stable",
    "PG": "stable",
    "JNJ": "stable",
    "ABBV": "stable",
    "T": "stable",
    "VZ": "stable",
    "MO": "stable",
    "PM": "stable",
    "PFE": "stable",
    "BMY": "stable",
    "MDT": "stable",
    "KMB": "stable",
    "601088": "cyclical",
    "600188": "cyclical",
    "601225": "cyclical",
    "600028": "cyclical",
    "601857": "cyclical",
    "00883.HK": "cyclical",
    "00386.HK": "cyclical",
    "00857.HK": "cyclical",
    "00016.HK": "cyclical",
    "01109.HK": "cyclical",
    "01928.HK": "cyclical",
    "XOM": "cyclical",
    "CVX": "cyclical",
}

PROFILE_LABELS = {
    "quality": "质量复利",
    "stable": "稳健收息",
    "cyclical": "周期高息",
    "financial": "金融股",
    "reit": "REIT",
}


logger = logging.getLogger(__name__)


def _contains_cjk(value: Optional[str]) -> bool:
    # A股名称统一用中文展示，避免被英文简称覆盖。
    if not value:
        return False
    return any("\u4e00" <= char <= "\u9fff" for char in value)


class IncomeScoreService:
    def __init__(self) -> None:
        self.market_resolver = MarketResolver()
        self.yahoo_http_client = YahooHttpClient()
        self.cache_ttl = timedelta(days=1)
        self.display_name_map = self._build_display_name_map()
        self.profile_map = self._build_profile_map()

    def _build_display_name_map(self) -> dict[tuple[str, str], str]:
        items: dict[tuple[str, str], str] = {}
        for market, candidates in UNIVERSE_BY_MARKET.items():
            for candidate in candidates:
                normalized_symbol = self.market_resolver.resolve(candidate.symbol).normalized_symbol
                items[(market, normalized_symbol)] = candidate.name
        return items

    def _preferred_display_name(
        self,
        market: str,
        normalized_symbol: str,
        fallback_name: Optional[str],
        candidate_name: Optional[str] = None,
    ) -> str:
        # CN 强制中文优先：目录中文名 > 中文回退名 > 既有映射 > 兜底。
        mapped_name = self.display_name_map.get((market, normalized_symbol))
        if market.upper() == "CN":
            if _contains_cjk(candidate_name):
                return str(candidate_name).strip()
            if _contains_cjk(fallback_name):
                return str(fallback_name).strip()
            if _contains_cjk(mapped_name):
                return str(mapped_name).strip()
            return (candidate_name or fallback_name or mapped_name or normalized_symbol).strip()
        return (mapped_name or fallback_name or candidate_name or normalized_symbol).strip()

    def _catalog_candidates(self, db: Session, market: str) -> list[ScoreCandidate]:
        items = db.scalars(
            select(StockCatalog)
            .where(StockCatalog.market == market.upper())
            .order_by(StockCatalog.normalized_symbol.asc())
        ).all()
        return [
            ScoreCandidate(
                symbol=item.normalized_symbol,
                name=item.name,
                market=item.market,
            )
            for item in items
        ]

    def _build_profile_map(self) -> dict[str, str]:
        # 评分按行业画像走不同阈值，先把候选池映射成稳定画像。
        items: dict[str, str] = {}
        for raw_symbol, profile in RAW_PROFILE_BY_SYMBOL.items():
            items[self.market_resolver.resolve(raw_symbol).normalized_symbol] = profile
        return items

    def _profile_for_symbol(self, normalized_symbol: str) -> str:
        return self.profile_map.get(normalized_symbol, "quality")

    def _profile_label(self, normalized_symbol: str) -> str:
        return PROFILE_LABELS.get(self._profile_for_symbol(normalized_symbol), "质量复利")

    def _is_stale(self, updated_at: Optional[datetime]) -> bool:
        if updated_at is None:
            return True
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - updated_at > self.cache_ttl

    def _annual_dividends(self, dividends: pd.Series) -> dict[int, Decimal]:
        if dividends is None or dividends.empty:
            return {}
        clean = dividends.dropna().copy()
        if clean.empty:
            return {}
        clean.index = pd.to_datetime(clean.index).tz_localize(None)
        grouped = clean.groupby(clean.index.year).sum()
        return {int(year): price(value) for year, value in grouped.items() if value and value > 0}

    def _dividend_streak(self, annual_dividends: dict[int, Decimal]) -> int:
        if not annual_dividends:
            return 0
        years = sorted(annual_dividends.keys(), reverse=True)
        streak = 0
        expected = years[0]
        for year in years:
            if year != expected or annual_dividends.get(year, Decimal("0")) <= 0:
                break
            streak += 1
            expected -= 1
        return streak

    def _dividend_cagr_5y(self, annual_dividends: dict[int, Decimal]) -> Optional[Decimal]:
        years = sorted(annual_dividends.keys())
        valid_years = [year for year in years if annual_dividends[year] > 0]
        if len(valid_years) < 5:
            return None
        start_year = valid_years[-5]
        end_year = valid_years[-1]
        start_value = annual_dividends[start_year]
        end_value = annual_dividends[end_year]
        periods = end_year - start_year
        if periods <= 0 or start_value <= 0 or end_value <= 0:
            return None
        cagr = ((end_value / start_value) ** (Decimal("1") / Decimal(str(periods))) - Decimal("1")) * Decimal("100")
        return pct(cagr)

    def _average_3y(self, frame: Optional[pd.DataFrame], keys: list[str]) -> Optional[Decimal]:
        if frame is None or frame.empty:
            return None
        for key in keys:
            if key in frame.index:
                values = [to_decimal(value) for value in frame.loc[key].dropna().tolist()[:3]]
                values = [value for value in values if value != 0]
                if values:
                    return sum(values) / Decimal(str(len(values)))
        return None

    def _latest_value(self, frame: Optional[pd.DataFrame], keys: list[str]) -> Optional[Decimal]:
        if frame is None or frame.empty:
            return None
        for key in keys:
            if key in frame.index:
                series = frame.loc[key].dropna().tolist()
                if series:
                    return to_decimal(series[0])
        return None

    def _compute_metrics_with_yfinance(self, candidate: ScoreCandidate) -> ScoreMetrics:
        resolved = self.market_resolver.resolve(candidate.symbol)
        profile = self._profile_for_symbol(resolved.normalized_symbol)
        ticker = yf.Ticker(resolved.yahoo_symbol)
        info = {}
        try:
            info = ticker.info or {}
        except Exception:
            info = {}

        history = ticker.history(period="6y", interval="1d", auto_adjust=False)
        history = history.dropna(subset=["Close"]).copy() if not history.empty else history
        close_series = history["Close"] if not history.empty and "Close" in history else pd.Series(dtype="float64")
        current_price = price(close_series.iloc[-1]) if not close_series.empty else None

        dividends = ticker.dividends
        annual_dividends = self._annual_dividends(dividends)
        latest_dividend_ttm = Decimal("0")
        if dividends is not None and not dividends.empty:
            clean_dividends = dividends.dropna().copy()
            clean_dividends.index = pd.to_datetime(clean_dividends.index).tz_localize(None)
            cutoff = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=365)
            latest_dividend_ttm = price(clean_dividends[clean_dividends.index >= cutoff].sum())

        current_dividend_yield = None
        if current_price and current_price > 0 and latest_dividend_ttm >= 0:
            current_dividend_yield = pct((latest_dividend_ttm / current_price) * 100)

        payout_ratio = None
        raw_payout = info.get("payoutRatio")
        if raw_payout not in (None, "", "None"):
            payout_ratio = pct(to_decimal(raw_payout) * 100 if to_decimal(raw_payout) <= 1 else to_decimal(raw_payout))

        financials = None
        balance_sheet = None
        cashflow = None
        try:
            financials = ticker.financials
        except Exception:
            financials = None
        try:
            balance_sheet = ticker.balance_sheet
        except Exception:
            balance_sheet = None
        try:
            cashflow = ticker.cashflow
        except Exception:
            cashflow = None

        shares_outstanding = to_decimal(info.get("sharesOutstanding"))
        avg_dividend_per_share_3y = None
        if annual_dividends:
            recent_years = sorted(annual_dividends.keys(), reverse=True)[:3]
            values = [annual_dividends[year] for year in recent_years if annual_dividends[year] > 0]
            if values:
                avg_dividend_per_share_3y = sum(values) / Decimal(str(len(values)))

        raw_free_cash_flow = to_decimal(info.get("freeCashflow"))
        if raw_free_cash_flow <= 0:
            raw_free_cash_flow = self._average_3y(cashflow, ["Free Cash Flow", "Operating Cash Flow"])

        fcf_coverage = None
        if raw_free_cash_flow and raw_free_cash_flow > 0 and shares_outstanding > 0 and avg_dividend_per_share_3y:
            avg_fcf_per_share = raw_free_cash_flow / shares_outstanding
            if avg_dividend_per_share_3y > 0:
                fcf_coverage = price(avg_fcf_per_share / avg_dividend_per_share_3y)

        roe_avg_3y = None
        raw_roe = info.get("returnOnEquity")
        if raw_roe not in (None, "", "None"):
            roe_avg_3y = pct(to_decimal(raw_roe) * 100 if to_decimal(raw_roe) <= 1 else to_decimal(raw_roe))
        else:
            avg_income = self._average_3y(financials, ["Net Income", "Net Income Common Stockholders"])
            avg_equity = self._average_3y(balance_sheet, ["Stockholders Equity", "Common Stock Equity", "Total Equity"])
            if avg_income and avg_equity and avg_equity > 0:
                roe_avg_3y = pct((avg_income / avg_equity) * 100)

        debt_ratio = None
        total_liabilities = self._latest_value(
            balance_sheet,
            ["Total Liabilities Net Minority Interest", "Total Liabilities", "Current Liabilities"],
        )
        total_assets = self._latest_value(balance_sheet, ["Total Assets"])
        if total_liabilities and total_assets and total_assets > 0:
            debt_ratio = pct((total_liabilities / total_assets) * 100)

        pe_percentile_5y = None
        if not close_series.empty:
            recent_close = close_series.tail(min(len(close_series), 1250))
            if not recent_close.empty:
                percentile = (recent_close <= recent_close.iloc[-1]).sum() / len(recent_close) * 100
                pe_percentile_5y = pct(percentile)

        management_bonus = Decimal("0")

        return ScoreMetrics(
            name=self._preferred_display_name(
                candidate.market,
                resolved.normalized_symbol,
                info.get("shortName") or info.get("longName") or candidate.name,
                candidate.name,
            ),
            market=candidate.market,
            normalized_symbol=resolved.normalized_symbol,
            profile=profile,
            current_dividend_yield=current_dividend_yield,
            payout_ratio=payout_ratio,
            dividend_streak_years=self._dividend_streak(annual_dividends),
            dividend_cagr_5y=self._dividend_cagr_5y(annual_dividends),
            fcf_coverage=fcf_coverage,
            roe_avg_3y=roe_avg_3y,
            debt_ratio=debt_ratio,
            pe_percentile_5y=pe_percentile_5y,
            management_bonus=management_bonus,
            note=None,
        )

    def _extract_annual_statements(self, summary: dict, module_name: str, item_key: str) -> list[dict]:
        module = summary.get(module_name) or {}
        statements = module.get(item_key) or []
        if not isinstance(statements, list):
            return []
        return statements

    def _average_statement_value(self, statements: list[dict], keys: list[str], years: int = 3) -> Optional[Decimal]:
        values: list[Decimal] = []
        for item in statements[:years]:
            for key in keys:
                raw = extract_raw(item.get(key))
                if raw not in (None, ""):
                    values.append(to_decimal(raw))
                    break
        values = [value for value in values if value != 0]
        if not values:
            return None
        return sum(values) / Decimal(str(len(values)))

    def _latest_statement_value(self, statements: list[dict], keys: list[str]) -> Optional[Decimal]:
        for item in statements[:1]:
            for key in keys:
                raw = extract_raw(item.get(key))
                if raw not in (None, ""):
                    return to_decimal(raw)
        return None

    def _compute_metrics_with_yahoo_http(self, candidate: ScoreCandidate) -> ScoreMetrics:
        resolved = self.market_resolver.resolve(candidate.symbol)
        profile = self._profile_for_symbol(resolved.normalized_symbol)
        history, dividends = self.yahoo_http_client.fetch_history_with_dividends(resolved.yahoo_symbol, years=6)
        quote = self.yahoo_http_client.fetch_quote(resolved.yahoo_symbol)
        summary = self.yahoo_http_client.fetch_quote_summary(
            resolved.yahoo_symbol,
            [
                "price",
                "summaryDetail",
                "defaultKeyStatistics",
                "financialData",
                "incomeStatementHistory",
                "balanceSheetHistory",
                "cashflowStatementHistory",
            ],
        )

        close_series = history["Close"] if not history.empty and "Close" in history else pd.Series(dtype="float64")
        current_price = price(quote.price if quote.price is not None else close_series.iloc[-1]) if not close_series.empty or quote.price is not None else None
        annual_dividends = self._annual_dividends(dividends)

        latest_dividend_ttm = Decimal("0")
        if not dividends.empty:
            cutoff = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=365)
            latest_dividend_ttm = price(dividends[dividends.index >= cutoff].sum())

        current_dividend_yield = None
        if current_price and current_price > 0:
            current_dividend_yield = pct((latest_dividend_ttm / current_price) * 100)

        summary_detail = summary.get("summaryDetail") or {}
        financial_data = summary.get("financialData") or {}
        price_module = summary.get("price") or {}

        payout_ratio_raw = extract_raw(summary_detail.get("payoutRatio"))
        payout_ratio = pct(to_decimal(payout_ratio_raw) * 100 if to_decimal(payout_ratio_raw) <= 1 else to_decimal(payout_ratio_raw)) if payout_ratio_raw not in (None, "") else None

        shares_outstanding = to_decimal(extract_raw(price_module.get("sharesOutstanding")))
        avg_dividend_per_share_3y = None
        if annual_dividends:
            recent_years = sorted(annual_dividends.keys(), reverse=True)[:3]
            values = [annual_dividends[year] for year in recent_years if annual_dividends[year] > 0]
            if values:
                avg_dividend_per_share_3y = sum(values) / Decimal(str(len(values)))

        free_cash_flow_raw = extract_raw(financial_data.get("freeCashflow"))
        free_cash_flow = to_decimal(free_cash_flow_raw)
        if free_cash_flow <= 0:
            cashflow_statements = self._extract_annual_statements(summary, "cashflowStatementHistory", "cashflowStatements")
            free_cash_flow = self._average_statement_value(
                cashflow_statements,
                ["freeCashFlow", "totalCashFromOperatingActivities"],
            ) or Decimal("0")

        fcf_coverage = None
        if free_cash_flow > 0 and shares_outstanding > 0 and avg_dividend_per_share_3y and avg_dividend_per_share_3y > 0:
            fcf_coverage = price((free_cash_flow / shares_outstanding) / avg_dividend_per_share_3y)

        roe_raw = extract_raw(financial_data.get("returnOnEquity"))
        roe_avg_3y = pct(to_decimal(roe_raw) * 100 if to_decimal(roe_raw) <= 1 else to_decimal(roe_raw)) if roe_raw not in (None, "") else None

        balance_statements = self._extract_annual_statements(summary, "balanceSheetHistory", "balanceSheetStatements")
        total_liabilities = self._latest_statement_value(
            balance_statements,
            ["totalLiab", "totalCurrentLiabilities"],
        )
        total_assets = self._latest_statement_value(balance_statements, ["totalAssets"])
        debt_ratio = pct((total_liabilities / total_assets) * 100) if total_liabilities and total_assets and total_assets > 0 else None

        pe_percentile_5y = None
        if not close_series.empty:
            recent_close = close_series.tail(min(len(close_series), 1250))
            if not recent_close.empty:
                percentile = (recent_close <= recent_close.iloc[-1]).sum() / len(recent_close) * 100
                pe_percentile_5y = pct(percentile)

        return ScoreMetrics(
            name=self._preferred_display_name(
                candidate.market,
                resolved.normalized_symbol,
                quote.name or candidate.name,
                candidate.name,
            ),
            market=candidate.market,
            normalized_symbol=resolved.normalized_symbol,
            profile=profile,
            current_dividend_yield=current_dividend_yield,
            payout_ratio=payout_ratio,
            dividend_streak_years=self._dividend_streak(annual_dividends),
            dividend_cagr_5y=self._dividend_cagr_5y(annual_dividends),
            fcf_coverage=fcf_coverage,
            roe_avg_3y=roe_avg_3y,
            debt_ratio=debt_ratio,
            pe_percentile_5y=pe_percentile_5y,
            management_bonus=Decimal("0"),
            note=None,
        )

    def _compute_metrics(self, candidate: ScoreCandidate) -> ScoreMetrics:
        # 评分指标先尽量从可用数据源抓齐，再进入统一打分阶段。
        providers = [
            ("yfinance", self._compute_metrics_with_yfinance),
            ("yahoo-http", self._compute_metrics_with_yahoo_http),
        ]
        errors: list[str] = []
        for provider_name, provider in providers:
            try:
                metrics = provider(candidate)
                logger.info("ranking provider selected: %s for %s", provider_name, candidate.symbol)
                return metrics
            except Exception as exc:
                errors.append(f"{provider_name}: {exc}")
        raise ValueError(" ; ".join(errors) if errors else f"评分数据获取失败: {candidate.symbol}")

    def _score_yield(self, yield_pct: Optional[Decimal], profile: str) -> tuple[Decimal, bool, Optional[str]]:
        if yield_pct is None:
            return Decimal("0"), False, "缺少股息率数据"
        if yield_pct > 10:
            return Decimal("0"), True, "股息率超过10%，触发高息陷阱警报"
        if profile == "quality":
            if Decimal("3") <= yield_pct <= Decimal("6"):
                return Decimal("20"), False, None
            if Decimal("2") <= yield_pct < Decimal("3") or Decimal("6") < yield_pct <= Decimal("8"):
                return Decimal("15"), False, None
            if Decimal("1") <= yield_pct < Decimal("2"):
                return Decimal("8"), False, None
            return Decimal("0"), False, None
        if profile == "stable":
            if Decimal("4") <= yield_pct <= Decimal("7.5"):
                return Decimal("20"), False, None
            if Decimal("3") <= yield_pct < Decimal("4") or Decimal("7.5") < yield_pct <= Decimal("9"):
                return Decimal("15"), False, None
            if Decimal("2") <= yield_pct < Decimal("3"):
                return Decimal("8"), False, None
            return Decimal("0"), False, None
        if profile == "cyclical":
            if Decimal("5") <= yield_pct <= Decimal("8.5"):
                return Decimal("20"), False, None
            if Decimal("3") <= yield_pct < Decimal("5") or Decimal("8.5") < yield_pct <= Decimal("10"):
                return Decimal("15"), False, None
            if Decimal("1.5") <= yield_pct < Decimal("3"):
                return Decimal("8"), False, None
            return Decimal("0"), False, None
        if profile == "financial":
            if Decimal("4") <= yield_pct <= Decimal("8"):
                return Decimal("20"), False, None
            if Decimal("3") <= yield_pct < Decimal("4") or Decimal("8") < yield_pct <= Decimal("10"):
                return Decimal("15"), False, None
            if Decimal("2") <= yield_pct < Decimal("3"):
                return Decimal("8"), False, None
            return Decimal("0"), False, None
        if profile == "reit":
            if Decimal("4.5") <= yield_pct <= Decimal("8.5"):
                return Decimal("20"), False, None
            if Decimal("3.5") <= yield_pct < Decimal("4.5") or Decimal("8.5") < yield_pct <= Decimal("10"):
                return Decimal("15"), False, None
            if Decimal("2.5") <= yield_pct < Decimal("3.5"):
                return Decimal("8"), False, None
            return Decimal("0"), False, None
        if yield_pct >= 5:
            return Decimal("20"), False, None
        if yield_pct >= 3:
            return Decimal("15"), False, None
        if yield_pct >= 1:
            return Decimal("5"), False, None
        return Decimal("0"), False, None

    def _score_payout(self, payout_ratio: Optional[Decimal], profile: str) -> Decimal:
        if payout_ratio is None:
            return Decimal("0")
        if profile == "financial":
            if Decimal("20") <= payout_ratio <= Decimal("50"):
                return Decimal("15")
            if Decimal("50") < payout_ratio <= Decimal("65"):
                return Decimal("12")
            if Decimal("10") <= payout_ratio < Decimal("20") or Decimal("65") < payout_ratio <= Decimal("80"):
                return Decimal("8")
            return Decimal("0")
        if profile == "reit":
            if Decimal("55") <= payout_ratio <= Decimal("90"):
                return Decimal("15")
            if Decimal("40") <= payout_ratio < Decimal("55") or Decimal("90") < payout_ratio <= Decimal("100"):
                return Decimal("10")
            if Decimal("25") <= payout_ratio < Decimal("40"):
                return Decimal("5")
            return Decimal("0")
        if profile == "stable":
            if Decimal("40") <= payout_ratio <= Decimal("75"):
                return Decimal("15")
            if Decimal("25") <= payout_ratio < Decimal("40") or Decimal("75") < payout_ratio <= Decimal("90"):
                return Decimal("10")
            if payout_ratio < Decimal("25"):
                return Decimal("5")
            return Decimal("0")
        if profile == "cyclical":
            if Decimal("25") <= payout_ratio <= Decimal("60"):
                return Decimal("15")
            if Decimal("15") <= payout_ratio < Decimal("25") or Decimal("60") < payout_ratio <= Decimal("75"):
                return Decimal("10")
            if Decimal("75") < payout_ratio <= Decimal("90"):
                return Decimal("5")
            return Decimal("0")
        if Decimal("30") <= payout_ratio <= Decimal("65"):
            return Decimal("15")
        if Decimal("20") <= payout_ratio < Decimal("30") or Decimal("65") < payout_ratio <= Decimal("80"):
            return Decimal("10")
        if payout_ratio < Decimal("20"):
            return Decimal("5")
        return Decimal("0")

    def _score_continuity(self, streak_years: int, cagr_5y: Optional[Decimal], profile: str) -> Decimal:
        growth = cagr_5y if cagr_5y is not None else Decimal("0")
        floors = {
            "quality": Decimal("2"),
            "stable": Decimal("0"),
            "cyclical": Decimal("-5"),
            "financial": Decimal("-10"),
            "reit": Decimal("0"),
        }
        floor = floors.get(profile, Decimal("0"))
        if streak_years >= 12 and growth >= floor:
            return Decimal("15")
        if streak_years >= 8 and growth >= floor - Decimal("3"):
            return Decimal("12")
        if streak_years >= 5 and growth >= floor - Decimal("6"):
            return Decimal("8")
        if streak_years >= 3:
            return Decimal("5")
        return Decimal("0")

    def _score_fcf(
        self,
        coverage: Optional[Decimal],
        profile: str,
        payout_ratio: Optional[Decimal],
        roe_avg_3y: Optional[Decimal],
    ) -> Decimal:
        if profile == "financial":
            if roe_avg_3y is not None and roe_avg_3y >= Decimal("10"):
                return Decimal("8")
            if payout_ratio is not None and payout_ratio <= Decimal("70"):
                return Decimal("8")
            return Decimal("5")
        if coverage is None:
            return Decimal("0")
        if profile == "cyclical":
            if coverage > Decimal("1.6"):
                return Decimal("15")
            if coverage >= Decimal("1.1"):
                return Decimal("10")
            if coverage >= Decimal("0.9"):
                return Decimal("5")
            return Decimal("0")
        if coverage > Decimal("1.4"):
            return Decimal("15")
        if coverage >= Decimal("1.0"):
            return Decimal("10")
        if coverage >= Decimal("0.8"):
            return Decimal("5")
        return Decimal("0")

    def _score_roe(self, roe_avg_3y: Optional[Decimal], debt_ratio: Optional[Decimal], profile: str) -> Decimal:
        if roe_avg_3y is None or roe_avg_3y < Decimal("5"):
            return Decimal("0")
        if profile == "financial":
            if roe_avg_3y >= Decimal("15"):
                return Decimal("15")
            if roe_avg_3y >= Decimal("12"):
                return Decimal("12")
            if roe_avg_3y >= Decimal("9"):
                return Decimal("8")
            return Decimal("5")
        if roe_avg_3y >= Decimal("15"):
            if debt_ratio is None or debt_ratio < Decimal("60"):
                return Decimal("15")
            return Decimal("10")
        if roe_avg_3y >= Decimal("10"):
            return Decimal("10")
        return Decimal("5")

    def _score_debt(self, debt_ratio: Optional[Decimal], profile: str) -> Decimal:
        if profile == "financial":
            return Decimal("7")
        if debt_ratio is None:
            return Decimal("0")
        if profile == "reit":
            if debt_ratio < Decimal("45"):
                return Decimal("10")
            if debt_ratio < Decimal("60"):
                return Decimal("8")
            if debt_ratio <= Decimal("75"):
                return Decimal("5")
            if debt_ratio <= Decimal("85"):
                return Decimal("3")
            return Decimal("0")
        if profile == "stable":
            if debt_ratio < Decimal("35"):
                return Decimal("10")
            if debt_ratio < Decimal("50"):
                return Decimal("7")
            if debt_ratio <= Decimal("70"):
                return Decimal("4")
            if debt_ratio <= Decimal("80"):
                return Decimal("2")
            return Decimal("0")
        if profile == "cyclical":
            if debt_ratio < Decimal("30"):
                return Decimal("10")
            if debt_ratio < Decimal("45"):
                return Decimal("7")
            if debt_ratio <= Decimal("60"):
                return Decimal("4")
            if debt_ratio <= Decimal("70"):
                return Decimal("2")
            return Decimal("0")
        if debt_ratio < Decimal("30"):
            return Decimal("10")
        if debt_ratio < Decimal("50"):
            return Decimal("7")
        if debt_ratio <= Decimal("70"):
            return Decimal("4")
        return Decimal("0")

    def _score_pe(self, pe_percentile_5y: Optional[Decimal], profile: str) -> Decimal:
        if pe_percentile_5y is None:
            return Decimal("0")
        if profile == "financial":
            if pe_percentile_5y < Decimal("40"):
                return Decimal("10")
            if pe_percentile_5y <= Decimal("70"):
                return Decimal("6")
            return Decimal("0")
        if profile == "reit":
            if pe_percentile_5y < Decimal("35"):
                return Decimal("10")
            if pe_percentile_5y <= Decimal("65"):
                return Decimal("5")
            return Decimal("0")
        if profile == "quality":
            if pe_percentile_5y < Decimal("30"):
                return Decimal("10")
            if pe_percentile_5y <= Decimal("55"):
                return Decimal("5")
            return Decimal("0")
        if pe_percentile_5y < Decimal("30"):
            return Decimal("10")
        if pe_percentile_5y <= Decimal("60"):
            return Decimal("5")
        return Decimal("0")

    def _grade_from_score(self, total_score: Decimal, is_blacklisted: bool) -> str:
        if is_blacklisted:
            return "E"
        if total_score >= Decimal("85"):
            return "A"
        if total_score >= Decimal("75"):
            return "B"
        if total_score >= Decimal("65"):
            return "C"
        if total_score >= Decimal("50"):
            return "D"
        return "E"

    def _recommendation_for_grade(self, grade: str, profile: str, is_blacklisted: bool) -> str:
        if is_blacklisted:
            if profile == "financial":
                return "触发硬风险，先观察资本与分红修复"
            if profile == "reit":
                return "触发硬风险，先观察分派与杠杆修复"
            if profile == "cyclical":
                return "触发硬风险，先等周期和现金流修复"
            return "触发硬风险，先不建仓，等待复评"

        recommendations = {
            "quality": {
                "A": "优先研究，可分批建仓并长期跟踪",
                "B": "适合底仓，等回撤时分批配置",
                "C": "先纳入观察，等待估值或股息改善",
                "D": "暂列观察名单，除非安全边际明显改善",
                "E": "当前安全边际不足，先观察基本面变化",
            },
            "stable": {
                "A": "适合作为核心收息底仓，逢回撤配置",
                "B": "可作收息底仓，回撤时分批介入",
                "C": "先观察，等股息率或确定性更好再介入",
                "D": "暂不做核心仓，等待收益率回到合理区间",
                "E": "分红吸引力不足，先观察不急于配置",
            },
            "cyclical": {
                "A": "景气与分红匹配，可顺周期分批参与",
                "B": "可小步布局，重点跟踪现金流与景气",
                "C": "先跟踪周期拐点，不急于当前建仓",
                "D": "仅保留观察，暂不建议当前周期重仓",
                "E": "景气与分红不匹配，先等待周期修复",
            },
            "financial": {
                "A": "股息与经营质量均衡，可作金融底仓",
                "B": "可列入底仓候选，跟踪分红与资本质量",
                "C": "先观察拨备、资本和分红稳定性",
                "D": "先看资产质量改善，再考虑是否介入",
                "E": "分红与资本质量未达标，先保持观察",
            },
            "reit": {
                "A": "分派与杠杆匹配，可作现金流底仓",
                "B": "可作收益型底仓，关注资产质量变化",
                "C": "先观察出租率、利率和分派稳定性",
                "D": "先观察债务与分派压力，不急于配置",
                "E": "分派与杠杆组合一般，先观察现金流修复",
            },
        }
        return recommendations.get(profile, recommendations["quality"]).get(grade, "继续观察")

    def _verdict(self, total_score: Decimal, profile: str, is_blacklisted: bool) -> tuple[str, str]:
        grade = self._grade_from_score(total_score, is_blacklisted)
        return grade, self._recommendation_for_grade(grade, profile, is_blacklisted)

    def _compose_note(self, metrics: ScoreMetrics, is_blacklisted: bool, note: Optional[str]) -> Optional[str]:
        notes: list[str] = []
        if is_blacklisted and note:
            notes.append(note)
        elif note:
            notes.append(note)

        if metrics.profile == "financial":
            notes.append("金融股采用专用口径：FCF 与资产负债率不做工业股硬性扣分，以分红纪律、ROE 和估值位置为主。")
        elif metrics.profile == "reit":
            notes.append("REIT 采用放宽后的派息率与杠杆阈值，估值项使用价格分位代理。")
        elif metrics.profile == "cyclical":
            notes.append("周期股更重视现金流覆盖与派息可持续性，估值项使用价格分位代理。")

        if metrics.pe_percentile_5y is not None:
            notes.append("估值项当前使用5年价格分位代理，并非严格PE历史分位。")

        if not notes:
            return None
        return "；".join(dict.fromkeys(notes))[:255]

    def _apply_scorecard(self, metrics: ScoreMetrics) -> dict[str, Decimal | bool | Optional[str] | str]:
        # 所有行业最后都落到同一份 scorecard，便于缓存和前端展示。
        yield_score, is_blacklisted, note = self._score_yield(metrics.current_dividend_yield, metrics.profile)
        payout_score = self._score_payout(metrics.payout_ratio, metrics.profile)
        continuity_score = self._score_continuity(metrics.dividend_streak_years, metrics.dividend_cagr_5y, metrics.profile)
        fcf_score = self._score_fcf(metrics.fcf_coverage, metrics.profile, metrics.payout_ratio, metrics.roe_avg_3y)
        roe_score = self._score_roe(metrics.roe_avg_3y, metrics.debt_ratio, metrics.profile)
        debt_score = self._score_debt(metrics.debt_ratio, metrics.profile)
        pe_score = self._score_pe(metrics.pe_percentile_5y, metrics.profile)
        bonus_score = metrics.management_bonus
        base_score = yield_score + payout_score + continuity_score + fcf_score + roe_score + debt_score + pe_score
        total_score = min(Decimal("100"), base_score + bonus_score)
        verdict, recommendation = self._verdict(total_score, metrics.profile, is_blacklisted)
        return {
            "yield_score": yield_score,
            "payout_score": payout_score,
            "continuity_score": continuity_score,
            "fcf_score": fcf_score,
            "roe_score": roe_score,
            "debt_score": debt_score,
            "pe_score": pe_score,
            "bonus_score": bonus_score,
            "base_score": base_score,
            "total_score": total_score,
            "verdict": verdict,
            "recommendation": recommendation,
            "is_blacklisted": is_blacklisted,
            "note": self._compose_note(metrics, is_blacklisted, note),
        }

    def _serialize(self, score: IncomeScore, catalog_name: Optional[str] = None) -> dict:
        # 列表页和详情页共用同一套序列化字段。
        display_name = self._preferred_display_name(
            score.market,
            score.normalized_symbol,
            score.name,
            catalog_name,
        )
        return {
            "symbol": score.normalized_symbol,
            "market": score.market,
            "name": display_name,
            "profile": self._profile_label(score.normalized_symbol),
            "recommendation": score.recommendation,
            "verdict": score.verdict,
            "note": score.note,
            "is_blacklisted": score.is_blacklisted,
            "total_score": round(score.total_score, 2),
            "base_score": round(score.base_score, 2),
            "bonus_score": round(score.bonus_score, 2),
            "dividend_yield_score": round(score.dividend_yield_score, 2),
            "payout_ratio_score": round(score.payout_ratio_score, 2),
            "continuity_score": round(score.continuity_score, 2),
            "fcf_score": round(score.fcf_score, 2),
            "roe_score": round(score.roe_score, 2),
            "debt_score": round(score.debt_score, 2),
            "pe_score": round(score.pe_score, 2),
            "current_dividend_yield": round(score.current_dividend_yield or 0, 2) if score.current_dividend_yield is not None else None,
            "payout_ratio": round(score.payout_ratio or 0, 2) if score.payout_ratio is not None else None,
            "dividend_streak_years": score.dividend_streak_years,
            "dividend_cagr_5y": round(score.dividend_cagr_5y or 0, 2) if score.dividend_cagr_5y is not None else None,
            "fcf_coverage": round(score.fcf_coverage or 0, 2) if score.fcf_coverage is not None else None,
            "roe_avg_3y": round(score.roe_avg_3y or 0, 2) if score.roe_avg_3y is not None else None,
            "debt_ratio": round(score.debt_ratio or 0, 2) if score.debt_ratio is not None else None,
            "pe_percentile_5y": round(score.pe_percentile_5y or 0, 2) if score.pe_percentile_5y is not None else None,
            "management_bonus": round(score.management_bonus or 0, 2) if score.management_bonus is not None else 0,
            "data_status": score.data_status,
            "updated_at": score.updated_at,
        }

    def _upsert_score(self, db: Session, candidate: ScoreCandidate) -> IncomeScore:
        try:
            metrics = self._compute_metrics(candidate)
            scorecard = self._apply_scorecard(metrics)
            data_status = "ok"
        except Exception as exc:
            resolved = self.market_resolver.resolve(candidate.symbol)
            metrics = ScoreMetrics(
                name=candidate.name,
                market=candidate.market,
                normalized_symbol=resolved.normalized_symbol,
                profile=self._profile_for_symbol(resolved.normalized_symbol),
                current_dividend_yield=None,
                payout_ratio=None,
                dividend_streak_years=0,
                dividend_cagr_5y=None,
                fcf_coverage=None,
                roe_avg_3y=None,
                debt_ratio=None,
                pe_percentile_5y=None,
                management_bonus=Decimal("0"),
                note=str(exc)[:255],
            )
            scorecard = self._apply_scorecard(metrics)
            data_status = "failed"

        existing = db.scalar(
            select(IncomeScore)
            .where(
                IncomeScore.market == candidate.market,
                IncomeScore.normalized_symbol == metrics.normalized_symbol,
            )
            .order_by(IncomeScore.updated_at.desc(), IncomeScore.id.desc())
        )
        if existing is None:
            existing = IncomeScore(market=candidate.market, normalized_symbol=metrics.normalized_symbol, name=metrics.name)

        existing.name = metrics.name
        existing.recommendation = str(scorecard["recommendation"])
        existing.verdict = str(scorecard["verdict"])
        existing.note = scorecard["note"]
        existing.is_blacklisted = bool(scorecard["is_blacklisted"])
        existing.total_score = as_float(scorecard["total_score"])
        existing.base_score = as_float(scorecard["base_score"])
        existing.bonus_score = as_float(scorecard["bonus_score"])
        existing.dividend_yield_score = as_float(scorecard["yield_score"])
        existing.payout_ratio_score = as_float(scorecard["payout_score"])
        existing.continuity_score = as_float(scorecard["continuity_score"])
        existing.fcf_score = as_float(scorecard["fcf_score"])
        existing.roe_score = as_float(scorecard["roe_score"])
        existing.debt_score = as_float(scorecard["debt_score"])
        existing.pe_score = as_float(scorecard["pe_score"])
        existing.current_dividend_yield = as_float(metrics.current_dividend_yield) if metrics.current_dividend_yield is not None else None
        existing.payout_ratio = as_float(metrics.payout_ratio) if metrics.payout_ratio is not None else None
        existing.dividend_streak_years = metrics.dividend_streak_years
        existing.dividend_cagr_5y = as_float(metrics.dividend_cagr_5y) if metrics.dividend_cagr_5y is not None else None
        existing.fcf_coverage = as_float(metrics.fcf_coverage) if metrics.fcf_coverage is not None else None
        existing.roe_avg_3y = as_float(metrics.roe_avg_3y) if metrics.roe_avg_3y is not None else None
        existing.debt_ratio = as_float(metrics.debt_ratio) if metrics.debt_ratio is not None else None
        existing.pe_percentile_5y = as_float(metrics.pe_percentile_5y) if metrics.pe_percentile_5y is not None else None
        existing.management_bonus = as_float(metrics.management_bonus)
        existing.data_status = data_status
        existing.updated_at = datetime.now(timezone.utc)
        db.add(existing)
        return existing

    def recalculate_cached_scores(self, db: Session) -> int:
        # 调整打分规则后，可直接用本地缓存重算，不必重新联网抓数。
        items = db.scalars(select(IncomeScore)).all()
        for item in items:
            metrics = ScoreMetrics(
                name=item.name,
                market=item.market,
                normalized_symbol=item.normalized_symbol,
                profile=self._profile_for_symbol(item.normalized_symbol),
                current_dividend_yield=to_decimal(item.current_dividend_yield) if item.current_dividend_yield is not None else None,
                payout_ratio=to_decimal(item.payout_ratio) if item.payout_ratio is not None else None,
                dividend_streak_years=item.dividend_streak_years or 0,
                dividend_cagr_5y=to_decimal(item.dividend_cagr_5y) if item.dividend_cagr_5y is not None else None,
                fcf_coverage=to_decimal(item.fcf_coverage) if item.fcf_coverage is not None else None,
                roe_avg_3y=to_decimal(item.roe_avg_3y) if item.roe_avg_3y is not None else None,
                debt_ratio=to_decimal(item.debt_ratio) if item.debt_ratio is not None else None,
                pe_percentile_5y=to_decimal(item.pe_percentile_5y) if item.pe_percentile_5y is not None else None,
                management_bonus=to_decimal(item.management_bonus) if item.management_bonus is not None else Decimal("0"),
                note=None if item.data_status == "ok" else item.note,
            )
            scorecard = self._apply_scorecard(metrics)
            item.recommendation = str(scorecard["recommendation"])
            item.verdict = str(scorecard["verdict"])
            item.note = scorecard["note"]
            item.is_blacklisted = bool(scorecard["is_blacklisted"])
            item.total_score = as_float(scorecard["total_score"])
            item.base_score = as_float(scorecard["base_score"])
            item.bonus_score = as_float(scorecard["bonus_score"])
            item.dividend_yield_score = as_float(scorecard["yield_score"])
            item.payout_ratio_score = as_float(scorecard["payout_score"])
            item.continuity_score = as_float(scorecard["continuity_score"])
            item.fcf_score = as_float(scorecard["fcf_score"])
            item.roe_score = as_float(scorecard["roe_score"])
            item.debt_score = as_float(scorecard["debt_score"])
            item.pe_score = as_float(scorecard["pe_score"])
            item.updated_at = datetime.now(timezone.utc)
            db.add(item)
        db.commit()
        return len(items)

    def refresh_market(self, db: Session, market: str) -> int:
        return self._refresh_market(db, market, throttle_seconds=0)

    def _refresh_market(self, db: Session, market: str, throttle_seconds: float) -> int:
        market = market.upper()
        candidates = self._catalog_candidates(db, market)
        if not candidates:
            return 0
        for index, candidate in enumerate(candidates, start=1):
            self._upsert_score(db, candidate)
            if index % 100 == 0:
                db.commit()
            if throttle_seconds > 0:
                time.sleep(throttle_seconds)
        db.commit()
        return len(candidates)

    def refresh_all(self, db: Session, throttle_seconds: float = 0) -> int:
        total = 0
        for market in UNIVERSE_BY_MARKET:
            total += self._refresh_market(db, market, throttle_seconds=throttle_seconds)
        return total

    def latest_refresh_at(self, db: Session) -> Optional[datetime]:
        # 取评分缓存的最新更新时间，用于判断是否需要自动刷新。
        return db.scalar(select(func.max(IncomeScore.updated_at)))

    def list_scores(self, db: Session, market: str, page: int = 1, page_size: int = 50) -> dict:
        market = market.upper()
        safe_page = max(page, 1)
        safe_page_size = min(max(page_size, 1), 50)
        query = (
            select(IncomeScore)
            .where(IncomeScore.market == market)
            .order_by(IncomeScore.total_score.desc(), IncomeScore.current_dividend_yield.desc().nullslast())
        )
        total = db.scalar(select(func.count()).select_from(IncomeScore).where(IncomeScore.market == market)) or 0
        items = db.scalars(
            query.offset((safe_page - 1) * safe_page_size).limit(safe_page_size)
        ).all()
        cn_name_map: dict[str, str] = {}
        if market == "CN" and items:
            symbols = [item.normalized_symbol for item in items]
            cn_name_map = {
                symbol: name
                for symbol, name in db.execute(
                    select(StockCatalog.normalized_symbol, StockCatalog.name).where(
                        StockCatalog.market == "CN",
                        StockCatalog.normalized_symbol.in_(symbols),
                    )
                ).all()
            }
        return {
            "items": [self._serialize(item, cn_name_map.get(item.normalized_symbol)) for item in items],
            "page": safe_page,
            "page_size": safe_page_size,
            "total": total,
        }

    def get_score_detail(self, db: Session, market: str, symbol: str) -> Optional[dict]:
        market = market.upper()
        resolved = self.market_resolver.resolve(symbol)
        item = db.scalar(
            select(IncomeScore)
            .where(
                IncomeScore.market == market,
                IncomeScore.normalized_symbol == resolved.normalized_symbol,
            )
            .order_by(IncomeScore.updated_at.desc(), IncomeScore.id.desc())
        )
        if item is None:
            return None
        catalog_name = None
        if market == "CN":
            catalog_name = db.scalar(
                select(StockCatalog.name).where(
                    StockCatalog.market == "CN",
                    StockCatalog.normalized_symbol == item.normalized_symbol,
                )
            )
        return self._serialize(item, catalog_name)


income_score_service = IncomeScoreService()
