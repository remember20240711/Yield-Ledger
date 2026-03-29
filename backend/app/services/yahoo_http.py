from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import httpx
import pandas as pd

from app.core.config import get_settings


def extract_raw(value: Any) -> Any:
    # Yahoo 的 summary 字段经常包一层 raw/fmt，这里统一拆掉。
    if isinstance(value, dict):
        if "raw" in value:
            return value.get("raw")
        if "fmt" in value:
            return value.get("fmt")
    return value


@dataclass
class YahooHttpQuote:
    # HTTP fallback 只保留当前项目真正会用到的字段。
    name: Optional[str]
    price: Optional[float]


class YahooHttpClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.timeout = settings.sync_timeout_seconds
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "application/json,text/plain,*/*",
        }

    def _get_json(self, url: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        response = httpx.get(
            url,
            params=params,
            headers=self.headers,
            timeout=self.timeout,
            follow_redirects=True,
        )
        response.raise_for_status()
        return response.json()

    def fetch_history_with_dividends(self, symbol: str, years: int = 11) -> tuple[pd.DataFrame, pd.Series]:
        # 返回价格和分红两个序列，供持仓同步和评分模型复用。
        payload = self._get_json(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
            {
                "range": f"{years}y",
                "interval": "1d",
                "includePrePost": "false",
                "events": "div",
            },
        )
        result = (payload.get("chart") or {}).get("result") or []
        if not result:
            raise ValueError(f"Yahoo HTTP history unavailable for {symbol}")
        chart = result[0]
        timestamps = chart.get("timestamp") or []
        closes = (((chart.get("indicators") or {}).get("quote") or [{}])[0]).get("close") or []
        history = pd.DataFrame({"Close": closes}, index=pd.to_datetime(timestamps, unit="s", utc=True))
        history.index = history.index.tz_localize(None)
        history = history.dropna(subset=["Close"]).copy()
        if history.empty:
            raise ValueError(f"Yahoo HTTP empty history for {symbol}")

        raw_dividends = ((chart.get("events") or {}).get("dividends")) or {}
        dividend_map: dict[pd.Timestamp, float] = {}
        for item in raw_dividends.values():
            dividend_date = item.get("date")
            amount = item.get("amount")
            if dividend_date is None or amount in (None, ""):
                continue
            dividend_map[pd.to_datetime(int(dividend_date), unit="s")] = float(amount)
        dividends = pd.Series(dividend_map, dtype="float64").sort_index()
        return history, dividends

    def fetch_quote(self, symbol: str) -> YahooHttpQuote:
        payload = self._get_json(
            "https://query1.finance.yahoo.com/v7/finance/quote",
            {"symbols": symbol},
        )
        result = ((payload.get("quoteResponse") or {}).get("result")) or []
        if not result:
            return YahooHttpQuote(name=None, price=None)
        item = result[0]
        name = item.get("shortName") or item.get("longName") or item.get("displayName")
        price = item.get("regularMarketPrice")
        return YahooHttpQuote(name=name, price=float(price) if price not in (None, "") else None)

    def fetch_quote_summary(self, symbol: str, modules: list[str]) -> dict[str, Any]:
        payload = self._get_json(
            f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}",
            {"modules": ",".join(modules)},
        )
        result = ((payload.get("quoteSummary") or {}).get("result")) or []
        if not result:
            raise ValueError(f"Yahoo HTTP quoteSummary unavailable for {symbol}")
        return result[0]
