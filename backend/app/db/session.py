from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base


settings = get_settings()

# SQLite 适合这个单机项目，连接工厂统一从这里创建。
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    from app.models import dividend, income_score, stock, stock_catalog, transaction  # noqa: F401
    from app.services.catalog import stock_catalog_service

    # 建表之外，顺手兼容历史版本的缺列和缺索引问题。
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        transaction_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(transactions)"))
        }
        if "transaction_type" not in transaction_columns:
            connection.execute(
                text("ALTER TABLE transactions ADD COLUMN transaction_type VARCHAR(8) NOT NULL DEFAULT 'buy'")
            )
        catalog_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(stock_catalog)"))
        }
        if "last_price" not in catalog_columns:
            connection.execute(text("ALTER TABLE stock_catalog ADD COLUMN last_price NUMERIC(18, 4)"))
        if "pinyin_full" not in catalog_columns:
            connection.execute(text("ALTER TABLE stock_catalog ADD COLUMN pinyin_full VARCHAR(256)"))
        if "pinyin_initials" not in catalog_columns:
            connection.execute(text("ALTER TABLE stock_catalog ADD COLUMN pinyin_initials VARCHAR(64)"))
        connection.execute(
            text(
                """
                UPDATE stock_catalog
                SET last_price = (
                    SELECT stocks.last_price
                    FROM stocks
                    WHERE stocks.normalized_symbol = stock_catalog.normalized_symbol
                )
                WHERE last_price IS NULL
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE stocks
                SET name = (
                    SELECT stock_catalog.name
                    FROM stock_catalog
                    WHERE stock_catalog.normalized_symbol = stocks.normalized_symbol
                )
                WHERE market IN ('CN', 'HK')
                  AND EXISTS (
                    SELECT 1
                    FROM stock_catalog
                    WHERE stock_catalog.normalized_symbol = stocks.normalized_symbol
                  )
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE income_scores
                SET name = (
                    SELECT stock_catalog.name
                    FROM stock_catalog
                    WHERE stock_catalog.normalized_symbol = income_scores.normalized_symbol
                )
                WHERE market IN ('CN', 'HK')
                  AND EXISTS (
                    SELECT 1
                    FROM stock_catalog
                    WHERE stock_catalog.normalized_symbol = income_scores.normalized_symbol
                  )
                """
            )
        )
        connection.execute(
            text(
                """
                DELETE FROM income_scores
                WHERE id NOT IN (
                    SELECT MAX(id)
                    FROM income_scores
                    GROUP BY market, normalized_symbol
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_income_score_market_symbol
                ON income_scores (market, normalized_symbol)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_stock_catalog_pinyin_full
                ON stock_catalog (pinyin_full)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_stock_catalog_pinyin_initials
                ON stock_catalog (pinyin_initials)
                """
            )
        )

    # 历史目录库在启动时补齐拼音搜索键，避免必须等下一次全量刷新。
    db = SessionLocal()
    try:
        stock_catalog_service.ensure_search_keys(db)
    finally:
        db.close()


def get_db() -> Generator[Session, None, None]:
    # 每个请求拿独立会话，用完即关，避免状态串掉。
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
