from typing import Optional
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.database import SessionLocal
from app.services.stock_data import sync_recent_prices_for_active_stocks


_scheduler: Optional[BackgroundScheduler] = None


def _daily_stock_sync_job() -> None:
    db = SessionLocal()
    try:
        sync_recent_prices_for_active_stocks(db)
    finally:
        db.close()


def start_scheduler() -> None:
    global _scheduler
    if not settings.stock_daily_sync_enabled or _scheduler is not None:
        return

    timezone = ZoneInfo("Asia/Taipei")
    scheduler = BackgroundScheduler(timezone=timezone)
    scheduler.add_job(
        _daily_stock_sync_job,
        trigger="cron",
        hour=settings.stock_daily_sync_hour,
        minute=settings.stock_daily_sync_minute,
        id="daily_stock_price_sync",
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return

    _scheduler.shutdown(wait=False)
    _scheduler = None
