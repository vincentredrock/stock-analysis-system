import argparse
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from typing import List

from app.config import settings
from app.database import SessionLocal
from app.models import Stock
from app.services.stock_data import (
    set_rate_limit_lock,
    sync_historical_prices,
    sync_stock_list,
)


def _taipei_today() -> date:
    from datetime import datetime
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("Asia/Taipei")).date()


def cmd_sync_list(args: argparse.Namespace) -> int:
    db = SessionLocal()
    try:
        count = sync_stock_list(db)
        print(f"Stock list synced: {count} stocks added/updated.")
        return 0
    finally:
        db.close()


def cmd_backfill(args: argparse.Namespace) -> int:
    end = _taipei_today()
    start = end - timedelta(days=args.days)

    db = SessionLocal()
    try:
        if args.symbols:
            symbols = [s.strip() for s in args.symbols.split(",")]
            stocks = (
                db.query(Stock)
                .filter(Stock.is_active == True, Stock.symbol.in_(symbols))
                .all()
            )
            missing = set(symbols) - {s.symbol for s in stocks}
            if missing:
                print(f"Warning: symbols not found or inactive: {missing}", file=sys.stderr)
        else:
            stocks = db.query(Stock).filter(Stock.is_active == True).all()
    finally:
        db.close()

    if not stocks:
        print("No active stocks to backfill.", file=sys.stderr)
        return 1

    # Override rate limit if requested
    if args.rate_limit is not None:
        settings.stock_sync_rate_limit_seconds = args.rate_limit

    lock = threading.Lock()
    set_rate_limit_lock(lock)

    total_stocks = len(stocks)
    print(f"Backfilling {total_stocks} stocks from {start} to {end} using {args.workers} workers...")

    completed = 0
    failed = 0
    total_upserted = 0

    def _sync_one(stock) -> tuple:
        db = SessionLocal()
        try:
            result = sync_historical_prices(db, stock.symbol, start=start, end=end)
            return (stock.symbol, True, result.records_upserted, None)
        except Exception as exc:
            return (stock.symbol, False, 0, str(exc))
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(_sync_one, stock): stock for stock in stocks}
        for future in as_completed(futures):
            symbol, success, upserted, error = future.result()
            if success:
                completed += 1
                total_upserted += upserted
                print(f"  [{completed}/{total_stocks}] {symbol}: {upserted} records")
            else:
                failed += 1
                print(f"  [{completed + failed}/{total_stocks}] {symbol}: FAILED ({error})", file=sys.stderr)

    print(
        f"\nDone. {completed} succeeded, {failed} failed, {total_upserted} total records upserted."
    )
    set_rate_limit_lock(None)
    return 0 if failed == 0 else 1


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stock Analysis System CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # sync-list
    subparsers.add_parser("sync-list", help="Sync the master stock list from twstock")

    # backfill
    backfill_parser = subparsers.add_parser("backfill", help="Backfill historical prices")
    backfill_parser.add_argument(
        "--days", type=int, default=365, help="Number of days to backfill (default: 365)"
    )
    backfill_parser.add_argument(
        "--workers", type=int, default=4, help="Number of parallel workers (default: 4)"
    )
    backfill_parser.add_argument(
        "--symbols", type=str, default=None, help="Comma-separated symbols to backfill (default: all active)"
    )
    backfill_parser.add_argument(
        "--rate-limit", type=float, default=None, help="Override rate limit seconds between requests"
    )

    args = parser.parse_args(argv)

    if args.command == "sync-list":
        return cmd_sync_list(args)
    if args.command == "backfill":
        return cmd_backfill(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
