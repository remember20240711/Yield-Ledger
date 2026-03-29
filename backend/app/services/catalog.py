from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import pandas as pd
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.models.stock_catalog import StockCatalog
from app.models.stock import Stock
from app.services.market import MarketResolver
from app.utils.numbers import as_float, price, to_decimal

try:
    import akshare as ak
except Exception:  # pragma: no cover - runtime dependency fallback
    ak = None


@dataclass
class CatalogItem:
    symbol: str
    normalized_symbol: str
    name: str
    market: str
    currency: str
    last_price: Optional[Decimal]


class StockCatalogService:
    def __init__(self) -> None:
        self.market_resolver = MarketResolver()
        self.cache_ttl = timedelta(days=14)

    @staticmethod
    def _find_column(frame: pd.DataFrame, candidates: list[str]) -> Optional[str]:
        for candidate in candidates:
            if candidate in frame.columns:
                return candidate
        return None

    def _append_item(
        self,
        items: list[CatalogItem],
        seen: set[str],
        symbol: str,
        name: str,
        market: str,
        currency: str,
        last_price: Optional[Decimal] = None,
    ) -> None:
        # 目录库按 normalized_symbol 去重，避免候选重复出现。
        if not symbol or not name:
            return
        resolved = self.market_resolver.resolve(symbol)
        if resolved.normalized_symbol in seen:
            return
        items.append(
            CatalogItem(
                symbol=symbol,
                normalized_symbol=resolved.normalized_symbol,
                name=str(name).strip(),
                market=market,
                currency=currency,
                last_price=price(last_price) if last_price not in (None, "", "-") else None,
            )
        )
        seen.add(resolved.normalized_symbol)

    def _load_a_shares(self, items: list[CatalogItem], seen: set[str]) -> None:
        if ak is None:
            return
        frame = ak.stock_zh_a_spot_em()
        if frame is None or frame.empty:
            return
        code_col = self._find_column(frame, ["code", "代码", "证券代码"])
        name_col = self._find_column(frame, ["name", "名称", "股票简称", "证券简称"])
        price_col = self._find_column(frame, ["最新价", "最新", "当前价", "close"])
        if not code_col or not name_col:
            return
        for _, row in frame.iterrows():
            self._append_item(
                items,
                seen,
                str(row[code_col]).strip(),
                str(row[name_col]).strip(),
                "CN",
                "CNY",
                to_decimal(row[price_col]) if price_col and row[price_col] not in (None, "", "-") else None,
            )

    def _load_hk_stocks(self, items: list[CatalogItem], seen: set[str]) -> None:
        if ak is None:
            return
        frame = ak.stock_hk_spot_em()
        if frame is None or frame.empty:
            return
        code_col = self._find_column(frame, ["代码", "symbol", "code"])
        name_col = self._find_column(frame, ["名称", "name"])
        price_col = self._find_column(frame, ["最新价", "最新", "当前价", "close"])
        if not code_col or not name_col:
            return
        for _, row in frame.iterrows():
            self._append_item(
                items,
                seen,
                str(row[code_col]).strip(),
                str(row[name_col]).strip(),
                "HK",
                "HKD",
                to_decimal(row[price_col]) if price_col and row[price_col] not in (None, "", "-") else None,
            )

    def _load_cn_etfs(self, items: list[CatalogItem], seen: set[str]) -> None:
        if ak is None:
            return
        frame = ak.fund_etf_spot_em()
        if frame is None or frame.empty:
            return
        code_col = self._find_column(frame, ["代码", "symbol", "code"])
        name_col = self._find_column(frame, ["名称", "name"])
        price_col = self._find_column(frame, ["最新价", "最新", "当前价", "close"])
        if not code_col or not name_col:
            return
        for _, row in frame.iterrows():
            self._append_item(
                items,
                seen,
                str(row[code_col]).strip(),
                str(row[name_col]).strip(),
                "CN",
                "CNY",
                to_decimal(row[price_col]) if price_col and row[price_col] not in (None, "", "-") else None,
            )

    def _load_us_stocks(self, items: list[CatalogItem], seen: set[str]) -> None:
        if ak is None:
            return
        frame = ak.stock_us_spot_em()
        if frame is None or frame.empty:
            return
        code_col = self._find_column(frame, ["代码", "symbol", "code"])
        name_col = self._find_column(frame, ["名称", "name"])
        price_col = self._find_column(frame, ["最新价", "最新", "当前价", "close"])
        if not code_col or not name_col:
            return
        for _, row in frame.iterrows():
            raw_symbol = str(row[code_col]).strip()
            symbol = raw_symbol.split(".")[-1].upper()
            self._append_item(
                items,
                seen,
                symbol,
                str(row[name_col]).strip(),
                "US",
                "USD",
                to_decimal(row[price_col]) if price_col and row[price_col] not in (None, "", "-") else None,
            )

    def refresh_catalog(self, db: Session) -> int:
        # 目录刷新是低频任务，平时搜索只读本地库。
        items: list[CatalogItem] = []
        seen: set[str] = set()
        for loader in (self._load_a_shares, self._load_cn_etfs, self._load_hk_stocks, self._load_us_stocks):
            try:
                loader(items, seen)
            except Exception:
                continue

        if not items:
            return 0

        db.execute(delete(StockCatalog))
        for item in items:
            db.add(
                StockCatalog(
                    symbol=item.symbol,
                    normalized_symbol=item.normalized_symbol,
                    name=item.name,
                    market=item.market,
                    currency=item.currency,
                    last_price=item.last_price,
                    source="catalog",
                )
            )
        db.commit()
        return len(items)

    def needs_refresh(self, db: Session) -> bool:
        latest_updated_at = db.scalar(select(func.max(StockCatalog.updated_at)))
        if latest_updated_at is None:
            return True
        if latest_updated_at.tzinfo is None:
            latest_updated_at = latest_updated_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - latest_updated_at > self.cache_ttl

    def search(self, db: Session, query: str, limit: int = 20) -> list[dict]:
        # 搜索阶段不联网，只在本地缓存里模糊匹配。
        keyword = query.strip()
        if not keyword:
            return []

        if not db.scalar(select(StockCatalog.id).limit(1)):
            return []

        lower_keyword = keyword.lower()
        candidates = db.scalars(
            select(StockCatalog)
            .where(
                or_(
                    func.lower(StockCatalog.name).like(f"%{lower_keyword}%"),
                    func.lower(StockCatalog.symbol).like(f"%{lower_keyword}%"),
                    func.lower(StockCatalog.normalized_symbol).like(f"%{lower_keyword}%"),
                )
            )
            .limit(200)
        ).all()

        query_upper = keyword.upper()
        scored: list[tuple[tuple[int, int, str], StockCatalog]] = []
        for item in candidates:
            symbol_upper = item.normalized_symbol.upper()
            short_upper = item.symbol.upper()
            name_upper = item.name.upper()

            if symbol_upper == query_upper or short_upper == query_upper:
                score = (0, len(symbol_upper), item.normalized_symbol)
            elif symbol_upper.startswith(query_upper) or short_upper.startswith(query_upper):
                score = (1, len(symbol_upper), item.normalized_symbol)
            elif name_upper.startswith(query_upper):
                score = (2, len(item.name), item.normalized_symbol)
            elif query_upper in name_upper:
                score = (3, name_upper.find(query_upper), item.normalized_symbol)
            else:
                symbol_pos = symbol_upper.find(query_upper)
                score = (4, symbol_pos if symbol_pos >= 0 else 999, item.normalized_symbol)

            scored.append((score, item))

        scored.sort(key=lambda entry: entry[0])
        target_symbols = [item.normalized_symbol for _, item in scored[:limit]]
        cached_prices = {
            normalized_symbol: last_price
            for normalized_symbol, last_price in db.execute(
                select(Stock.normalized_symbol, Stock.last_price).where(Stock.normalized_symbol.in_(target_symbols))
            ).all()
        }
        return [
            {
                "symbol": item.symbol,
                "normalized_symbol": item.normalized_symbol,
                "name": item.name,
                "market": item.market,
                "currency": item.currency,
                "current_price": as_float(price(cached_prices.get(item.normalized_symbol) or item.last_price))
                if (cached_prices.get(item.normalized_symbol) or item.last_price)
                else None,
            }
            for _, item in scored[:limit]
        ]


stock_catalog_service = StockCatalogService()
