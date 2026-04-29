from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_active_user
from app.models import Stock, StockPrice, StockSyncStatus, User
from app.schemas import (
    StockPriceRead,
    StockQuoteRead,
    StockRead,
    StockSearchResult,
    StockSyncResultRead,
    StockSyncStatusRead,
)
from app.services.stock_data import async_get_realtime_quote, sync_historical_prices

router = APIRouter(prefix="/stocks", tags=["Stocks"])


@router.get("/search", response_model=List[StockSearchResult])
def search_stocks(
    q: str = Query(..., min_length=1, description="Search query for stock name or symbol"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Search stocks by symbol or name."""
    stocks = (
        db.query(Stock)
        .filter(
            (Stock.symbol.ilike(f"%{q}%")) | (Stock.name.ilike(f"%{q}%"))
        )
        .filter(Stock.is_active == True)
        .limit(20)
        .all()
    )
    return stocks


@router.get("", response_model=List[StockRead])
def list_stocks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all available stocks."""
    stocks = db.query(Stock).filter(Stock.is_active == True).offset(skip).limit(limit).all()
    return stocks


@router.get("/{symbol}/quote", response_model=StockQuoteRead)
async def get_stock_quote(
    symbol: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get real-time quote for a stock (delayed data from twstock)."""
    stock = db.query(Stock).filter(Stock.symbol == symbol).first()
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock {symbol} not found",
        )

    quote = await async_get_realtime_quote(symbol)
    if quote is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to fetch real-time quote from data source",
        )

    return StockQuoteRead(**quote)


@router.get("/{symbol}/history", response_model=List[StockPriceRead])
def get_stock_history(
    symbol: str,
    start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get cached historical prices for a stock."""
    stock = db.query(Stock).filter(Stock.symbol == symbol).first()
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock {symbol} not found",
        )

    query = db.query(StockPrice).filter(StockPrice.stock_id == stock.id)

    if start:
        query = query.filter(StockPrice.date >= start)
    if end:
        query = query.filter(StockPrice.date <= end)

    prices = query.order_by(StockPrice.date.desc()).all()
    return prices


@router.get("/{symbol}/sync-status", response_model=StockSyncStatusRead)
def get_stock_sync_status(
    symbol: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get historical price sync status for a stock."""
    stock = db.query(Stock).filter(Stock.symbol == symbol).first()
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock {symbol} not found",
        )

    sync_status = db.query(StockSyncStatus).filter(StockSyncStatus.stock_id == stock.id).first()
    if not sync_status:
        return StockSyncStatusRead(symbol=symbol, status="pending", records_upserted=0)

    return StockSyncStatusRead(
        symbol=symbol,
        status=sync_status.status,
        synced_from=sync_status.synced_from,
        synced_to=sync_status.synced_to,
        last_attempt_at=sync_status.last_attempt_at,
        last_success_at=sync_status.last_success_at,
        last_error=sync_status.last_error,
        records_upserted=sync_status.records_upserted,
    )


@router.post("/{symbol}/sync", response_model=StockSyncResultRead)
def sync_stock_prices(
    symbol: str,
    start: Optional[date] = Query(None, description="Start date (YYYY-MM-DD). Defaults to full backfill or recent refresh."),
    end: Optional[date] = Query(None, description="End date (YYYY-MM-DD). Defaults to today in Asia/Taipei."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Trigger historical price sync for a stock from twstock."""
    stock = db.query(Stock).filter(Stock.symbol == symbol).first()
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock {symbol} not found",
        )

    try:
        result = sync_historical_prices(db, symbol, start=start, end=end)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to sync prices: {str(e)}",
        )

    return StockSyncResultRead(
        message=result.message,
        symbol=result.symbol,
        start=result.start,
        end=result.end,
        records_upserted=result.records_upserted,
        records_skipped=result.records_skipped,
        months_requested=result.months_requested,
    )
