from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Stock(Base):
    # 持仓主表保存股票基础信息和最近一次同步得到的缓存字段。
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    normalized_symbol: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    yahoo_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    market: Mapped[str] = mapped_column(String(8), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    last_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    latest_dividend_ttm: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    current_dividend_yield: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    five_year_avg_yield: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    ten_year_avg_yield: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    sync_message: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    transactions = relationship(
        "Transaction",
        back_populates="stock",
        cascade="all, delete-orphan",
        order_by="Transaction.trade_date",
    )
    dividends = relationship(
        "Dividend",
        back_populates="stock",
        cascade="all, delete-orphan",
        order_by="Dividend.year",
    )
