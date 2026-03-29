from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IncomeScore(Base):
    # 吃息评分榜缓存表，每个市场同一代码只保留一条最新评分。
    __tablename__ = "income_scores"
    __table_args__ = (UniqueConstraint("market", "normalized_symbol", name="uq_income_score_market_symbol"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    normalized_symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    market: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    recommendation: Mapped[str] = mapped_column(String(64), nullable=False, default="待评估")
    verdict: Mapped[str] = mapped_column(String(64), nullable=False, default="待评估")
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    total_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    base_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    bonus_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)

    dividend_yield_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    payout_ratio_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    continuity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    fcf_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    roe_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    debt_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    pe_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)

    current_dividend_yield: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    payout_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dividend_streak_years: Mapped[Optional[int]] = mapped_column(nullable=True)
    dividend_cagr_5y: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fcf_coverage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    roe_avg_3y: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    debt_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pe_percentile_5y: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    management_bonus: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    data_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
