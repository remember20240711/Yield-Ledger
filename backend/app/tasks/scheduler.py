import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.catalog import stock_catalog_service
from app.services.provider import market_data_service


logger = logging.getLogger(__name__)


def run_holdings_refresh_job() -> None:
    # 持仓缓存刷新频率高，优先保证价格和分红视图足够新。
    db = SessionLocal()
    try:
        market_data_service.refresh_all(db)
        logger.info("Holdings refresh completed")
    except Exception as exc:  # pragma: no cover - background job safety
        logger.exception("Holdings refresh failed: %s", exc)
    finally:
        db.close()


def run_catalog_refresh_job() -> None:
    # 候选股票目录变化慢，两周级别刷新即可。
    db = SessionLocal()
    try:
        refreshed = stock_catalog_service.refresh_catalog(db)
        logger.info("Biweekly catalog refresh completed: %s items", refreshed)
    except Exception as exc:  # pragma: no cover - background job safety
        logger.exception("Biweekly catalog refresh failed: %s", exc)
    finally:
        db.close()


def create_scheduler() -> BackgroundScheduler:
    # 所有后台任务统一在这里注册，便于部署时整体开关。
    settings = get_settings()
    scheduler = BackgroundScheduler(timezone=settings.timezone)
    scheduler.add_job(
        run_holdings_refresh_job,
        IntervalTrigger(minutes=settings.holdings_refresh_minutes, start_date=datetime.now() + timedelta(minutes=1)),
        id="holdings_refresh",
        replace_existing=True,
    )
    scheduler.add_job(
        run_holdings_refresh_job,
        CronTrigger(
            hour=settings.holdings_daily_refresh_hour,
            minute=settings.holdings_daily_refresh_minute,
            timezone=settings.timezone,
        ),
        id="holdings_daily_refresh",
        replace_existing=True,
    )
    scheduler.add_job(
        run_catalog_refresh_job,
        IntervalTrigger(days=14, start_date=datetime.now() + timedelta(days=14)),
        id="biweekly_catalog_refresh",
        replace_existing=True,
    )
    return scheduler
