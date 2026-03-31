from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal

from app.core.config import get_settings
from app.models.stock import Stock
from app.models.transaction import Transaction
from app.utils.numbers import as_float, money, pct, price, shares, to_decimal, trade_price


class ExchangeRateService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def rate_to_base(self, currency: str) -> Decimal:
        base = self.settings.base_currency.upper()
        currency = currency.upper()
        if currency == base:
            return Decimal("1")
        if base == "CNY":
            if currency == "USD":
                return to_decimal(self.settings.usd_to_cny)
            if currency == "HKD":
                return to_decimal(self.settings.hkd_to_cny)
        return Decimal("1")


exchange_rate_service = ExchangeRateService()


def latest_full_year_metrics(stock: Stock, current_price: Decimal) -> dict:
    # 上一年固定按上一自然年统计，例如 2026 年展示 2025-01-01 至 2025-12-31。
    target_year = datetime.now().year - 1
    record = next((item for item in stock.dividends if item.year == target_year), None)
    dividend_per_share = price(to_decimal(record.dividend_per_share) if record is not None else 0)
    dividend_yield = pct((dividend_per_share / current_price) * 100 if current_price > 0 else 0)
    return {
        "latest_full_year": target_year,
        "latest_full_year_dividend": as_float(dividend_per_share),
        "latest_full_year_dividend_yield": as_float(dividend_yield),
    }


def summarize_transactions(transactions: Iterable[Transaction]) -> tuple[Decimal, Decimal, Decimal]:
    # 成本口径按加权平均法处理，卖出会冲减剩余持仓成本。
    total_shares = Decimal("0")
    total_cost = Decimal("0")
    ordered_transactions = sorted(transactions, key=lambda item: (item.trade_date, item.id))

    for item in ordered_transactions:
        item_shares = shares(to_decimal(item.shares))
        item_price = trade_price(to_decimal(item.average_price))
        if item.transaction_type == "sell":
            if total_shares <= 0:
                continue
            sell_shares = item_shares if item_shares <= total_shares else total_shares
            average_cost_before_sell = trade_price(total_cost / total_shares) if total_shares > 0 else Decimal("0")
            total_cost -= average_cost_before_sell * sell_shares
            total_shares -= sell_shares
            if total_shares <= 0:
                total_shares = Decimal("0")
                total_cost = Decimal("0")
        else:
            total_shares += item_shares
            total_cost += item_shares * item_price

    total_shares = shares(total_shares)
    total_cost = money(total_cost)
    average_cost = trade_price((total_cost / total_shares) if total_shares > 0 else Decimal("0"))
    return total_shares, average_cost, total_cost


def serialize_stock(stock: Stock) -> dict:
    # 主表需要的展示字段统一在这里汇总，前端不重复计算。
    total_shares, average_cost, total_cost_native = summarize_transactions(stock.transactions)
    buy_transactions = [item for item in stock.transactions if item.transaction_type == "buy"]
    latest_buy_transaction = max(buy_transactions, key=lambda item: (item.trade_date, item.id), default=None)
    latest_buy_price = trade_price(
        to_decimal(latest_buy_transaction.average_price) if latest_buy_transaction else average_cost
    )
    fx_rate = exchange_rate_service.rate_to_base(stock.currency)
    current_price = price(to_decimal(stock.last_price))
    market_value = money(current_price * total_shares * fx_rate)
    total_cost = money(total_cost_native * fx_rate)
    annual_dividend = money(to_decimal(stock.latest_dividend_ttm) * total_shares * fx_rate)
    profit_loss = money(market_value - total_cost)
    full_year_metrics = latest_full_year_metrics(stock, current_price)
    latest_full_year_annual_dividend = money(
        to_decimal(full_year_metrics["latest_full_year_dividend"]) * total_shares * fx_rate
    )
    return {
        "id": stock.id,
        "symbol": stock.symbol,
        "normalized_symbol": stock.normalized_symbol,
        "name": stock.name,
        "market": stock.market,
        "currency": stock.currency,
        "base_currency": get_settings().base_currency.upper(),
        "fx_rate_to_base": as_float(price(fx_rate)),
        "total_shares": as_float(total_shares),
        "current_price": as_float(current_price),
        "market_value": as_float(market_value),
        "average_cost": as_float(average_cost),
        "total_cost": as_float(total_cost),
        "profit_loss": as_float(profit_loss),
        "current_dividend_yield": as_float(pct(to_decimal(stock.current_dividend_yield))),
        "five_year_avg_yield": as_float(pct(to_decimal(stock.five_year_avg_yield))),
        "ten_year_avg_yield": as_float(pct(to_decimal(stock.ten_year_avg_yield))),
        "annual_dividend": as_float(annual_dividend),
        "latest_dividend_ttm": as_float(price(to_decimal(stock.latest_dividend_ttm))),
        "latest_full_year": full_year_metrics["latest_full_year"],
        "latest_full_year_dividend": full_year_metrics["latest_full_year_dividend"],
        "latest_full_year_dividend_yield": full_year_metrics["latest_full_year_dividend_yield"],
        "latest_full_year_annual_dividend": as_float(latest_full_year_annual_dividend),
        "latest_buy_price": as_float(latest_buy_price),
        "last_synced_at": stock.last_synced_at,
        "sync_status": stock.sync_status,
        "sync_message": stock.sync_message,
    }


def serialize_summary(stocks: list[Stock]) -> dict:
    rows = [serialize_stock(stock) for stock in stocks]
    total_market_value = sum(item["market_value"] for item in rows)
    total_annual_dividend = sum(item["annual_dividend"] for item in rows)
    total_latest_full_year_dividend = sum(item["latest_full_year_annual_dividend"] for item in rows)
    overall_yield = (total_annual_dividend / total_market_value * 100) if total_market_value > 0 else 0
    overall_latest_full_year_yield = (
        (total_latest_full_year_dividend / total_market_value * 100) if total_market_value > 0 else 0
    )
    return {
        "total_market_value": round(total_market_value, 2),
        "total_annual_dividend": round(total_annual_dividend, 2),
        "overall_dividend_yield": round(overall_yield, 2),
        "total_latest_full_year_dividend": round(total_latest_full_year_dividend, 2),
        "overall_latest_full_year_yield": round(overall_latest_full_year_yield, 2),
        "base_currency": get_settings().base_currency.upper(),
        "stock_count": len(rows),
    }


def serialize_transactions(stock: Stock) -> dict:
    # 详情弹窗保留每笔交易和当前汇总结果。
    total_shares, average_cost, total_cost = summarize_transactions(stock.transactions)
    return {
        "stock_id": stock.id,
        "symbol": stock.normalized_symbol,
        "name": stock.name,
        "currency": stock.currency,
        "transactions": [
            {
                "id": item.id,
                "transaction_type": item.transaction_type,
                "trade_date": item.trade_date,
                "shares": as_float(shares(to_decimal(item.shares))),
                "average_price": as_float(trade_price(to_decimal(item.average_price))),
                "total_amount": as_float(money(to_decimal(item.total_amount))),
            }
            for item in sorted(stock.transactions, key=lambda tx: tx.trade_date)
        ],
        "total_shares": as_float(total_shares),
        "average_cost": as_float(average_cost),
        "total_cost": as_float(total_cost),
    }


def serialize_dividends(stock: Stock, quarterly_prices: list[dict] | None = None) -> dict:
    # 股息详情页只读本地缓存，避免每次点开都访问外部接口。
    current_price = price(to_decimal(stock.last_price))
    full_year_metrics = latest_full_year_metrics(stock, current_price)
    return {
        "stock_id": stock.id,
        "symbol": stock.normalized_symbol,
        "name": stock.name,
        "currency": stock.currency,
        "latest_dividend_ttm": as_float(price(to_decimal(stock.latest_dividend_ttm))),
        "current_dividend_yield": as_float(pct(to_decimal(stock.current_dividend_yield))),
        "latest_full_year": full_year_metrics["latest_full_year"],
        "latest_full_year_dividend": full_year_metrics["latest_full_year_dividend"],
        "latest_full_year_dividend_yield": full_year_metrics["latest_full_year_dividend_yield"],
        "dividends": [
            {
                "year": item.year,
                "dividend_per_share": as_float(price(to_decimal(item.dividend_per_share))),
                "dividend_yield": as_float(pct(to_decimal(item.dividend_yield))),
                "close_price": as_float(price(to_decimal(item.close_price))),
                "currency": item.currency,
                "source": item.source,
            }
            for item in sorted(stock.dividends, key=lambda dividend: dividend.year)
        ],
        "quarterly_prices": quarterly_prices or [],
    }
