from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi import status

from app.models import Stock, StockPrice
from tests.conftest import login_user, register_user


# ─── Auth Requirement ─────────────────────────────────────

class TestStocksAuth:
    def test_search_requires_auth(self, client):
        response = client.get("/api/v1/stocks?q=台積")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_requires_auth(self, client):
        response = client.get("/api/v1/stocks")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_quote_requires_auth(self, client):
        response = client.get("/api/v1/stocks/2330/quotes/latest")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_history_requires_auth(self, client):
        response = client.get("/api/v1/stocks/2330/prices")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_sync_requires_auth(self, client):
        response = client.post("/api/v1/stocks/2330/sync")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ─── Search ───────────────────────────────────────────────

class TestStockSearch:
    def test_search_by_symbol(self, auth_client, sample_stocks):
        response = auth_client.get("/api/v1/stocks?q=2330")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["symbol"] == "2330"
        assert data[0]["name"] == "台積電"

    def test_search_by_name(self, auth_client, sample_stocks):
        response = auth_client.get("/api/v1/stocks?q=台積")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["symbol"] == "2330"

    def test_search_no_results(self, auth_client, sample_stocks):
        response = auth_client.get("/api/v1/stocks?q=XYZ")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_search_empty_query(self, auth_client):
        response = auth_client.get("/api/v1/stocks?q=")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_search_case_insensitive(self, auth_client, sample_stocks):
        response = auth_client.get("/api/v1/stocks?q=tsmc")
        assert response.status_code == status.HTTP_200_OK
        # Should not find anything since our sample uses Chinese names
        assert response.json() == []

    def test_search_inactive_stock_not_shown(self, auth_client, sample_stocks, db_session):
        stock = db_session.query(Stock).filter(Stock.symbol == "2330").first()
        stock.is_active = False
        db_session.commit()
        response = auth_client.get("/api/v1/stocks?q=2330")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []


# ─── List Stocks ──────────────────────────────────────────

class TestListStocks:
    def test_list_stocks(self, auth_client, sample_stocks):
        response = auth_client.get("/api/v1/stocks")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 3
        symbols = {s["symbol"] for s in data}
        assert symbols == {"2330", "2317", "2454"}

    def test_list_stocks_pagination(self, auth_client, sample_stocks):
        response = auth_client.get("/api/v1/stocks?limit=2")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 2

    def test_list_stocks_offset(self, auth_client, sample_stocks):
        response = auth_client.get("/api/v1/stocks?offset=1&limit=1")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1


class TestGetStock:
    def test_get_stock(self, auth_client, sample_stocks):
        response = auth_client.get("/api/v1/stocks/2330")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["symbol"] == "2330"
        assert data["name"] == "台積電"

    def test_get_inactive_stock_not_found(self, auth_client, sample_stocks, db_session):
        stock = db_session.query(Stock).filter(Stock.symbol == "2330").first()
        stock.is_active = False
        db_session.commit()

        response = auth_client.get("/api/v1/stocks/2330")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_stock_not_found(self, auth_client):
        response = auth_client.get("/api/v1/stocks/9999")
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ─── Quote ────────────────────────────────────────────────

class TestStockQuote:
    @patch("app.services.stock_data.twstock.realtime.get")
    def test_get_quote_success(self, mock_get, auth_client, sample_stocks):
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
        response = auth_client.get("/api/v1/stocks/2330/quotes/latest")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["symbol"] == "2330"
        assert data["name"] == "台積電"
        assert Decimal(data["price"]) == Decimal("850.00")
        assert Decimal(data["open"]) == Decimal("845.00")
        assert Decimal(data["high"]) == Decimal("855.00")
        assert Decimal(data["low"]) == Decimal("840.00")
        assert data["volume"] == 50000
        assert Decimal(data["change"]) == Decimal("10.00")

    @patch("app.services.stock_data.twstock.realtime.get")
    def test_get_quote_source_failure(self, mock_get, auth_client, sample_stocks):
        mock_get.return_value = {"success": False}
        response = auth_client.get("/api/v1/stocks/2330/quotes/latest")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    def test_get_quote_stock_not_found(self, auth_client):
        response = auth_client.get("/api/v1/stocks/9999/quotes/latest")
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ─── History ──────────────────────────────────────────────

class TestStockHistory:
    def test_get_history(self, auth_client, sample_stocks, db_session):
        stock = db_session.query(Stock).filter(Stock.symbol == "2330").first()
        prices = [
            StockPrice(
                stock_id=stock.id,
                date=date(2024, 1, 1),
                open_price=Decimal("800.00"),
                high_price=Decimal("810.00"),
                low_price=Decimal("795.00"),
                close_price=Decimal("805.00"),
                volume=100000,
            ),
            StockPrice(
                stock_id=stock.id,
                date=date(2024, 1, 2),
                open_price=Decimal("805.00"),
                high_price=Decimal("815.00"),
                low_price=Decimal("800.00"),
                close_price=Decimal("810.00"),
                volume=120000,
            ),
        ]
        for p in prices:
            db_session.add(p)
        db_session.commit()

        response = auth_client.get("/api/v1/stocks/2330/prices")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["date"] == "2024-01-02"
        assert data[1]["date"] == "2024-01-01"

    def test_get_history_with_date_range(self, auth_client, sample_stocks, db_session):
        stock = db_session.query(Stock).filter(Stock.symbol == "2330").first()
        prices = [
            StockPrice(
                stock_id=stock.id,
                date=date(2024, 1, 1),
                open_price=Decimal("800.00"),
                high_price=Decimal("810.00"),
                low_price=Decimal("795.00"),
                close_price=Decimal("805.00"),
                volume=100000,
            ),
            StockPrice(
                stock_id=stock.id,
                date=date(2024, 1, 15),
                open_price=Decimal("850.00"),
                high_price=Decimal("860.00"),
                low_price=Decimal("845.00"),
                close_price=Decimal("855.00"),
                volume=150000,
            ),
        ]
        for p in prices:
            db_session.add(p)
        db_session.commit()

        response = auth_client.get("/api/v1/stocks/2330/prices?start=2024-01-01&end=2024-01-10")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["date"] == "2024-01-01"

    def test_get_history_empty(self, auth_client, sample_stocks):
        response = auth_client.get("/api/v1/stocks/2330/prices")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_get_history_stock_not_found(self, auth_client):
        response = auth_client.get("/api/v1/stocks/9999/prices")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_history_invalid_date_format(self, auth_client, sample_stocks):
        response = auth_client.get("/api/v1/stocks/2330/prices?start=01-01-2024")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_history_start_only(self, auth_client, sample_stocks, db_session):
        stock = db_session.query(Stock).filter(Stock.symbol == "2330").first()
        prices = [
            StockPrice(
                stock_id=stock.id,
                date=date(2024, 1, 1),
                open_price=Decimal("800.00"),
                high_price=Decimal("810.00"),
                low_price=Decimal("795.00"),
                close_price=Decimal("805.00"),
                volume=100000,
            ),
            StockPrice(
                stock_id=stock.id,
                date=date(2024, 1, 15),
                open_price=Decimal("850.00"),
                high_price=Decimal("860.00"),
                low_price=Decimal("845.00"),
                close_price=Decimal("855.00"),
                volume=150000,
            ),
        ]
        for p in prices:
            db_session.add(p)
        db_session.commit()

        response = auth_client.get("/api/v1/stocks/2330/prices?start=2024-01-10")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["date"] == "2024-01-15"

    def test_get_history_end_only(self, auth_client, sample_stocks, db_session):
        stock = db_session.query(Stock).filter(Stock.symbol == "2330").first()
        prices = [
            StockPrice(
                stock_id=stock.id,
                date=date(2024, 1, 1),
                open_price=Decimal("800.00"),
                high_price=Decimal("810.00"),
                low_price=Decimal("795.00"),
                close_price=Decimal("805.00"),
                volume=100000,
            ),
            StockPrice(
                stock_id=stock.id,
                date=date(2024, 1, 15),
                open_price=Decimal("850.00"),
                high_price=Decimal("860.00"),
                low_price=Decimal("845.00"),
                close_price=Decimal("855.00"),
                volume=150000,
            ),
        ]
        for p in prices:
            db_session.add(p)
        db_session.commit()

        response = auth_client.get("/api/v1/stocks/2330/prices?end=2024-01-10")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["date"] == "2024-01-01"


# ─── Sync ─────────────────────────────────────────────────

class TestStockSync:
    @patch("app.services.stock_data.twstock.Stock")
    def test_sync_success(self, mock_stock_class, auth_client, sample_stocks, db_session):
        from collections import namedtuple
        Data = namedtuple("Data", ["date", "capacity", "turnover", "open", "high", "low", "close", "change", "transaction"])
        mock_instance = mock_stock_class.return_value
        mock_instance.data = [
            Data(date=date(2024, 1, 1), capacity=100000, turnover=80000000, open=800.0, high=810.0, low=795.0, close=805.0, change=5.0, transaction=5000),
        ]
        mock_instance.fetch.return_value = mock_instance.data

        response = auth_client.post("/api/v1/stocks/2330/sync?start=2024-01-01&end=2024-01-31")
        assert response.status_code == status.HTTP_200_OK
        assert "Synced 1 price records for 2330" in response.json()["message"]

    @patch("app.services.stock_data.twstock.Stock")
    def test_sync_ignores_duplicate_prices(self, mock_stock_class, auth_client, sample_stocks, db_session):
        from collections import namedtuple
        Data = namedtuple(
            "Data",
            ["date", "capacity", "turnover", "open", "high", "low", "close", "change", "transaction"],
        )
        stock = db_session.query(Stock).filter(Stock.symbol == "2330").first()
        db_session.add(
            StockPrice(
                stock_id=stock.id,
                date=date(2024, 1, 1),
                open_price=Decimal("800.00"),
                high_price=Decimal("810.00"),
                low_price=Decimal("795.00"),
                close_price=Decimal("805.00"),
                volume=100000,
            )
        )
        db_session.commit()

        mock_instance = mock_stock_class.return_value
        mock_instance.data = [
            Data(
                date=date(2024, 1, 1),
                capacity=100000,
                turnover=80000000,
                open=800.0,
                high=810.0,
                low=795.0,
                close=805.0,
                change=5.0,
                transaction=5000,
            ),
            Data(
                date=date(2024, 1, 2),
                capacity=120000,
                turnover=96000000,
                open=805.0,
                high=815.0,
                low=800.0,
                close=810.0,
                change=5.0,
                transaction=6000,
            ),
            Data(
                date=date(2024, 1, 2),
                capacity=120000,
                turnover=96000000,
                open=805.0,
                high=815.0,
                low=800.0,
                close=810.0,
                change=5.0,
                transaction=6000,
            ),
        ]
        mock_instance.fetch.return_value = mock_instance.data

        response = auth_client.post("/api/v1/stocks/2330/sync?start=2024-01-01&end=2024-01-31")
        assert response.status_code == status.HTTP_200_OK
        assert "Synced 2 price records for 2330" in response.json()["message"]
        assert response.json()["records_skipped"] == 1
        assert db_session.query(StockPrice).filter(StockPrice.stock_id == stock.id).count() == 2

    def test_sync_status_pending(self, auth_client, sample_stocks):
        response = auth_client.get("/api/v1/stocks/2330/sync-status")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "pending"

    def test_sync_stock_not_found(self, auth_client):
        response = auth_client.post("/api/v1/stocks/9999/sync")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("app.routers.stocks.sync_historical_prices")
    def test_sync_bad_date_range(self, mock_sync, auth_client, sample_stocks):
        mock_sync.side_effect = ValueError("Start date cannot be after end date")
        response = auth_client.post("/api/v1/stocks/2330/sync?start=2024-02-01&end=2024-01-01")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("app.routers.stocks.sync_historical_prices")
    def test_sync_generic_exception(self, mock_sync, auth_client, sample_stocks):
        mock_sync.side_effect = Exception("Network failure")
        response = auth_client.post("/api/v1/stocks/2330/sync")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


class TestStockSyncStatus:
    def test_get_sync_status_existing(self, auth_client, sample_stocks, db_session):
        from app.models import StockSyncStatus
        stock = db_session.query(Stock).filter(Stock.symbol == "2330").first()
        status_obj = StockSyncStatus(
            stock_id=stock.id,
            status="success",
            synced_from=date(2024, 1, 1),
            synced_to=date(2024, 1, 31),
            records_upserted=10,
        )
        db_session.add(status_obj)
        db_session.commit()

        response = auth_client.get("/api/v1/stocks/2330/sync-status")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert data["records_upserted"] == 10
        assert data["synced_from"] == "2024-01-01"
        assert data["synced_to"] == "2024-01-31"

    def test_get_sync_status_stock_not_found(self, auth_client):
        response = auth_client.get("/api/v1/stocks/9999/sync-status")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestLegacyStockRoutes:
    @pytest.mark.parametrize(
        "path",
        [
            "/api/v1/stocks/search?q=2330",
            "/api/v1/stocks/2330/quote",
            "/api/v1/stocks/2330/history",
        ],
    )
    def test_action_oriented_stock_routes_are_removed(self, auth_client, path):
        response = auth_client.get(path)
        assert response.status_code == status.HTTP_404_NOT_FOUND
