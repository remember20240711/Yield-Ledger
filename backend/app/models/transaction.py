from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Transaction(Base):
    # 交易流水表只记录事实买卖，不在这里存派生汇总结果。
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_type: Mapped[str] = mapped_column(String(8), nullable=False, default="buy")
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    shares: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    average_price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    stock = relationship("Stock", back_populates="transactions")
