from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.models import Stock, StockSyncStatus
from app.services.stock_data import (
    StockSyncResult,
    _get_or_create_sync_status,
    _iter_months,
    _parse_date,
    _rate_limit,
    _taipei_today,
    _to_decimal,
    _to_int,
    async_get_realtime_quote,
    get_realtime_quote,
    sync_historical_prices,
    sync_stock_list,
)


class TestToDecimal:
    def test_none_returns_none(self):
        assert _to_decimal(None) is None

    def test_dash_returns_none(self):
        assert _to_decimal("-") is None

    def test_invalid_string_returns_none(self):
        assert _to_decimal("abc") is None

    def test_integer_string(self):
        assert _to_decimal("100") == Decimal("100.00")

    def test_float_string(self):
        assert _to_decimal("100.5") == Decimal("100.50")

    def test_precision(self):
        assert _to_decimal("100.555") == Decimal("100.56")


class TestToInt:
    def test_none_returns_none(self):
        assert _to_int(None) is None

    def test_dash_returns_none(self):
        assert _to_int("-") is None

    def test_with_commas(self):
        assert _to_int("1,000,000") == 1_000_000

    def test_invalid_string_returns_none(self):
        assert _to_int("abc") is None

    def test_plain_integer(self):
        assert _to_int(500) == 500


class TestRateLimit:
    def test_sleeps(self):
        with patch("app.services.stock_data.time.sleep") as mock_sleep:
            _rate_limit()
            mock_sleep.assert_called_once()


class TestTaipeiToday:
    def test_returns_date(self):
        result = _taipei_today()
        assert isinstance(result, date)

    def test_is_today_in_taipei(self):
        result = _taipei_today()
        expected = datetime.now(timezone(timedelta(hours=8))).date()
        assert result == expected


class TestParseDate:
    def test_valid_string(self):
        assert _parse_date("2024-01-15", date(2000, 1, 1)) == date(2024, 1, 15)

    def test_none_returns_fallback(self):
        fallback = date(2010, 1, 1)
        assert _parse_date(None, fallback) == fallback

    def test_empty_string_returns_fallback(self):
        fallback = date(2010, 1, 1)
        assert _parse_date("", fallback) == fallback


class TestIterMonths:
    def test_same_month(self):
        result = list(_iter_months(date(2024, 1, 1), date(2024, 1, 15)))
        assert result == [(2024, 1)]

    def test_multiple_months(self):
        result = list(_iter_months(date(2024, 1, 1), date(2024, 3, 1)))
        assert result == [(2024, 1), (2024, 2), (2024, 3)]

    def test_year_boundary(self):
        result = list(_iter_months(date(2023, 11, 1), date(2024, 2, 1)))
        assert result == [(2023, 11), (2023, 12), (2024, 1), (2024, 2)]


class TestStockSyncResult:
    def test_message_format(self):
        result = StockSyncResult(
            symbol="2330",
            start=date(2024, 1, 1),
            end=date(2024, 1, 31),
            records_upserted=10,
            records_skipped=2,
            months_requested=1,
        )
        assert "Synced 10 price records for 2330" in result.message
        assert "2024-01-01" in result.message
        assert "2024-01-31" in result.message


class TestGetOrCreateSyncStatus:
    def test_creates_new(self, db_session, sample_stocks):
        stock = sample_stocks[0]
        status = _get_or_create_sync_status(db_session, stock)
        assert status.stock_id == stock.id
        assert status.status == "pending"

    def test_returns_existing(self, db_session, sample_stocks):
        stock = sample_stocks[0]
        s1 = _get_or_create_sync_status(db_session, stock)
        s1.status = "success"
        db_session.commit()
        s2 = _get_or_create_sync_status(db_session, stock)
        assert s2.id == s1.id
        assert s2.status == "success"


class TestSyncStockList:
    def test_adds_new_stocks(self, db_session):
        mock_info = SimpleNamespace(
            market="上市",
            name="測試股",
            group="測試業",
            type="股票",
        )
        with patch.dict("app.services.stock_data.twstock.codes", {"9999": mock_info}, clear=False):
            count = sync_stock_list(db_session)
            assert count >= 1
            stock = db_session.query(Stock).filter_by(symbol="9999").first()
            assert stock is not None
            assert stock.name == "測試股"
            assert stock.market == "TWSE"
            assert stock.is_active is True

    def test_skips_unsupported_market(self, db_session):
        mock_info = SimpleNamespace(
            market="興櫃",
            name="測試股",
            group="測試業",
            type="股票",
        )
        with patch.dict("app.services.stock_data.twstock.codes", {"9998": mock_info}, clear=False):
            sync_stock_list(db_session)
            stock = db_session.query(Stock).filter_by(symbol="9998").first()
            assert stock is None

    def test_inactivates_missing_stocks(self, db_session):
        stock = Stock(symbol="ZZZZ", name="Old", market="TWSE", industry="X", is_active=True)
        db_session.add(stock)
        db_session.commit()

        mock_info = SimpleNamespace(market="上市", name="測試股", group="測試業", type="股票")
        with patch.dict("app.services.stock_data.twstock.codes", {"9999": mock_info}, clear=True):
            count = sync_stock_list(db_session)
            db_session.refresh(stock)
            assert stock.is_active is False
            assert count >= 1


class TestSyncHistoricalPrices:
    def test_start_after_end_raises(self, db_session, sample_stocks):
        with pytest.raises(ValueError, match="Start date cannot be after end date"):
            sync_historical_prices(db_session, sample_stocks[0].symbol, start=date(2024, 2, 1), end=date(2024, 1, 1))

    def test_stock_not_found_raises(self, db_session):
        with pytest.raises(ValueError, match="Stock 9999 not found"):
            sync_historical_prices(db_session, "9999")

    def test_successful_sync(self, db_session, sample_stocks):
        from collections import namedtuple
        Data = namedtuple(
            "Data",
            ["date", "capacity", "turnover", "open", "high", "low", "close", "change", "transaction"],
        )
        mock_instance = MagicMock()
        mock_instance.data = [
            Data(date=date(2024, 1, 5), capacity=100000, turnover=80000000, open=800.0, high=810.0, low=795.0, close=805.0, change=5.0, transaction=5000),
        ]
        mock_instance.fetch.return_value = mock_instance.data

        with patch("app.services.stock_data.twstock.Stock", return_value=mock_instance):
            result = sync_historical_prices(db_session, sample_stocks[0].symbol, start=date(2024, 1, 1), end=date(2024, 1, 31))
            assert result.records_upserted >= 1
            assert result.symbol == sample_stocks[0].symbol

    def test_failed_sync_updates_status(self, db_session, sample_stocks):
        with patch("app.services.stock_data.twstock.Stock", side_effect=Exception("Network error")):
            with pytest.raises(Exception, match="Network error"):
                sync_historical_prices(db_session, sample_stocks[0].symbol, start=date(2024, 1, 1), end=date(2024, 1, 31))

        status = db_session.query(StockSyncStatus).filter_by(stock_id=sample_stocks[0].id).first()
        assert status is not None
        assert status.status == "failed"
        assert "Network error" in status.last_error


class TestGetRealtimeQuote:
    def test_success(self):
        with patch("app.services.stock_data.twstock.realtime.get") as mock_get:
            mock_get.return_value = {
                "success": True,
                "info": {"code": "2330", "name": "台積電"},
                "realtime": {
                    "latest_trade_price": "850.00",
                    "open": "845.00",
                    "high": "855.00",
                    "low": "840.00",
                    "accumulate_trade_volume": "50000",
                    "price_change": "10.00",
                    "price_change_percent": "1.19",
                },
            }
            quote = get_realtime_quote("2330")
            assert quote["symbol"] == "2330"
            assert quote["name"] == "台積電"
            assert quote["price"] == Decimal("850.00")
            assert quote["volume"] == 50000

    def test_source_failure_returns_none(self):
        with patch("app.services.stock_data.twstock.realtime.get") as mock_get:
            mock_get.return_value = {"success": False}
            assert get_realtime_quote("2330") is None

    def test_calculates_change_percent_when_missing(self):
        with patch("app.services.stock_data.twstock.realtime.get") as mock_get:
            mock_get.return_value = {
                "success": True,
                "info": {"code": "2330", "name": "台積電"},
                "realtime": {
                    "latest_trade_price": "850.00",
                    "open": "845.00",
                    "high": "855.00",
                    "low": "840.00",
                    "accumulate_trade_volume": "50000",
                    "price_change": "10.00",
                    "price_change_percent": "-",
                },
            }
            quote = get_realtime_quote("2330")
            assert quote["change_percent"] is not None


class TestAsyncWrappers:
    def test_async_get_realtime_quote(self):
        with patch("app.services.stock_data.get_realtime_quote", return_value={"symbol": "2330"}) as mock_fn:
            import asyncio
            result = asyncio.run(async_get_realtime_quote("2330"))
            assert result == {"symbol": "2330"}
            mock_fn.assert_called_once_with("2330")
