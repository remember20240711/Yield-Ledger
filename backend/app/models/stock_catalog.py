from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StockCatalog(Base):
    # 本地股票目录缓存，只给候选搜索和名称回填使用。
    __tablename__ = "stock_catalog"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    normalized_symbol: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    pinyin_full: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, index=True)
    pinyin_initials: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    market: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    last_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="catalog")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
