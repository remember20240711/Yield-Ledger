from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Dividend(Base):
    # 年度分红缓存表，用来支撑股息详情弹窗和平均股息率计算。
    __tablename__ = "dividends"
    __table_args__ = (UniqueConstraint("stock_id", "year", name="uq_dividend_stock_year"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True)
    year: Mapped[int] = mapped_column(nullable=False)
    dividend_per_share: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    dividend_yield: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    close_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="cache")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    stock = relationship("Stock", back_populates="dividends")
