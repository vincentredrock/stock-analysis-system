import asyncio
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Optional
from zoneinfo import ZoneInfo

from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

import twstock

from app.config import settings
from app.models import Stock, StockPrice, StockSyncStatus


# ─── Helpers ──────────────────────────────────────────────

def _to_decimal(value, precision=2) -> Optional[Decimal]:
    if value is None or value == "-":
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return None


def _to_int(value) -> Optional[int]:
    if value is None or value == "-":
        return None
    try:
        return int(str(value).replace(",", ""))
    except Exception:
        return None


_rate_limit_lock: Optional[threading.Lock] = None


def set_rate_limit_lock(lock: Optional[threading.Lock]) -> None:
    """Set a global lock to coordinate rate limiting across threads."""
    global _rate_limit_lock
    _rate_limit_lock = lock


def _rate_limit():
    """Throttle historical data source requests."""
    if _rate_limit_lock is not None:
        with _rate_limit_lock:
            time.sleep(settings.stock_sync_rate_limit_seconds)
    else:
        time.sleep(settings.stock_sync_rate_limit_seconds)


def _taipei_today() -> date:
    return datetime.now(ZoneInfo("Asia/Taipei")).date()


def _parse_date(value: Optional[str], fallback: date) -> date:
    if not value:
        return fallback
    return date.fromisoformat(value)


def _iter_months(start: date, end: date) -> Iterable[tuple[int, int]]:
    current = date(start.year, start.month, 1)
    final = date(end.year, end.month, 1)
    while current <= final:
        yield current.year, current.month
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)


@dataclass
class StockSyncResult:
    symbol: str
    start: date
    end: date
    records_upserted: int
    records_skipped: int
    months_requested: int

    @property
    def message(self) -> str:
        return (
            f"Synced {self.records_upserted} price records for {self.symbol} "
            f"from {self.start.isoformat()} to {self.end.isoformat()}"
        )


def _get_or_create_sync_status(db: Session, stock: Stock) -> StockSyncStatus:
    status = db.query(StockSyncStatus).filter(StockSyncStatus.stock_id == stock.id).first()
    if status:
        return status

    status = StockSyncStatus(stock_id=stock.id, status="pending", records_upserted=0)
    db.add(status)
    db.flush()
    return status


# ─── Stock List Sync ──────────────────────────────────────

# Security types that twstock.realtime supports and we want to expose
_SUPPORTED_TYPES = {
    "股票",
    "ETF",
    "特別股",
    "臺灣存託憑證(TDR)",
    "受益證券-不動產投資信託",
    "創新板",
}


def sync_stock_list(db: Session) -> int:
    """Sync stocks table from twstock.codes. Returns count of added or updated stocks."""
    changed = 0
    seen_symbols = set()
    for code, info in twstock.codes.items():
        # Only include TWSE and TPEx listed stocks
        if info.market not in ("上市", "上櫃"):
            continue
        # Skip warrants, ETNs, and other unsupported securities
        if info.type not in _SUPPORTED_TYPES:
            continue
        market_map = {"上市": "TWSE", "上櫃": "TPEx"}
        values = {
            "name": info.name,
            "market": market_map.get(info.market, "TWSE"),
            "industry": info.group if info.group else None,
            "is_active": True,
        }
        seen_symbols.add(code)
        existing = db.query(Stock).filter(Stock.symbol == code).first()
        if existing:
            if any(getattr(existing, key) != value for key, value in values.items()):
                for key, value in values.items():
                    setattr(existing, key, value)
                changed += 1
            continue

        db.add(Stock(symbol=code, **values))
        changed += 1

    inactive_count = (
        db.query(Stock)
        .filter(Stock.is_active == True, Stock.symbol.notin_(seen_symbols))
        .update({Stock.is_active: False}, synchronize_session=False)
        if seen_symbols
        else 0
    )
    changed += inactive_count
    db.commit()
    return changed


# ─── Historical Price Sync ────────────────────────────────

def sync_historical_prices(
    db: Session,
    symbol: str,
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> StockSyncResult:
    """Fetch and cache historical prices for a stock from twstock by month."""
    stock = db.query(Stock).filter(Stock.symbol == symbol).first()
    if not stock:
        raise ValueError(f"Stock {symbol} not found")

    today = _taipei_today()
    status = _get_or_create_sync_status(db, stock)
    if end is None:
        end = today
    if start is None:
        latest_price_date = (
            db.query(StockPrice.date)
            .filter(StockPrice.stock_id == stock.id)
            .order_by(StockPrice.date.desc())
            .limit(1)
            .scalar()
        )
        if latest_price_date:
            start = max(
                latest_price_date - timedelta(days=settings.stock_daily_sync_lookback_days),
                date(1900, 1, 1),
            )
        else:
            start = _parse_date(settings.stock_history_start_date, date(2010, 1, 1))
    if start > end:
        raise ValueError("Start date cannot be after end date")

    status.status = "running"
    status.last_attempt_at = datetime.now(timezone.utc)
    status.last_error = None
    db.commit()

    upserted = 0
    skipped = 0
    months_requested = 0
    insert_stmt = (
        postgresql_insert
        if db.get_bind().dialect.name == "postgresql"
        else sqlite_insert
    )
    try:
        tws = twstock.Stock(symbol)
        seen_dates = set()
        for year, month in _iter_months(start, end):
            months_requested += 1
            _rate_limit()
            fetched = tws.fetch(year, month)
            rows = fetched if fetched is not None else tws.data
            for data in rows:
                data_date = data.date.date() if isinstance(data.date, datetime) else data.date
                if data_date < start or data_date > end:
                    continue
                if data_date in seen_dates:
                    skipped += 1
                    continue
                seen_dates.add(data_date)

                open_price = _to_decimal(data.open)
                high_price = _to_decimal(data.high)
                low_price = _to_decimal(data.low)
                close_price = _to_decimal(data.close)
                if None in (open_price, high_price, low_price, close_price):
                    skipped += 1
                    continue

                values = dict(
                    stock_id=stock.id,
                    date=data_date,
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    close_price=close_price,
                    volume=_to_int(data.capacity) or 0,
                    change=_to_decimal(data.change),
                )
                stmt = insert_stmt(StockPrice).values(**values).on_conflict_do_update(
                    index_elements=["stock_id", "date"],
                    set_={
                        "open_price": values["open_price"],
                        "high_price": values["high_price"],
                        "low_price": values["low_price"],
                        "close_price": values["close_price"],
                        "volume": values["volume"],
                        "change": values["change"],
                    },
                )
                result = db.execute(stmt)
                upserted += result.rowcount or 0

        status.status = "success"
        status.synced_from = start if status.synced_from is None else min(status.synced_from, start)
        status.synced_to = end if status.synced_to is None else max(status.synced_to, end)
        status.last_success_at = datetime.now(timezone.utc)
        status.last_error = None
        status.records_upserted = upserted
        db.commit()
    except Exception as exc:
        db.rollback()
        status = _get_or_create_sync_status(db, stock)
        status.status = "failed"
        status.last_attempt_at = datetime.now(timezone.utc)
        status.last_error = str(exc)[:500]
        db.commit()
        raise

    return StockSyncResult(
        symbol=symbol,
        start=start,
        end=end,
        records_upserted=upserted,
        records_skipped=skipped,
        months_requested=months_requested,
    )


def sync_recent_prices_for_active_stocks(db: Session, lookback_days: Optional[int] = None) -> int:
    """Refresh recent history for all active stocks after market close."""
    if lookback_days is None:
        lookback_days = settings.stock_daily_sync_lookback_days
    end = _taipei_today()
    start = end - timedelta(days=lookback_days)
    total = 0
    stocks = db.query(Stock).filter(Stock.is_active == True).all()
    for stock in stocks:
        result = sync_historical_prices(db, stock.symbol, start=start, end=end)
        total += result.records_upserted
    return total


# ─── Real-time Quote ──────────────────────────────────────

def get_realtime_quote(symbol: str) -> Optional[dict]:
    """Get real-time quote from twstock. Returns dict or None if failed."""
    _rate_limit()
    rt = twstock.realtime.get(symbol)
    if not rt.get("success"):
        return None
    info = rt.get("info", {})
    realtime = rt.get("realtime", {})

    price = _to_decimal(realtime.get("latest_trade_price"))
    open_p = _to_decimal(realtime.get("open"))
    high_p = _to_decimal(realtime.get("high"))
    low_p = _to_decimal(realtime.get("low"))
    close_p = _to_decimal(realtime.get("latest_trade_price"))
    volume = _to_int(realtime.get("accumulate_trade_volume"))
    change = _to_decimal(realtime.get("price_change"))
    change_percent = _to_decimal(realtime.get("price_change_percent"))

    # Calculate change_percent if missing
    if change_percent is None and change is not None and open_p and open_p > 0:
        change_percent = (change / open_p * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return {
        "symbol": info.get("code", symbol),
        "name": info.get("name", ""),
        "price": price,
        "open": open_p,
        "high": high_p,
        "low": low_p,
        "close": close_p,
        "volume": volume or 0,
        "change": change,
        "change_percent": change_percent,
        "last_updated": datetime.now(timezone.utc),
    }


# ─── Async Wrappers ───────────────────────────────────────

async def async_get_realtime_quote(symbol: str) -> Optional[dict]:
    """Async wrapper for get_realtime_quote using thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, get_realtime_quote, symbol)


async def async_sync_historical_prices(
    db: Session,
    symbol: str,
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> StockSyncResult:
    """Async wrapper for sync_historical_prices using thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, sync_historical_prices, db, symbol, start, end)


async def async_sync_stock_list(db: Session) -> int:
    """Async wrapper for sync_stock_list using thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, sync_stock_list, db)
