from unittest.mock import MagicMock, patch

import pytest

from app.scheduler import _daily_stock_sync_job, start_scheduler, stop_scheduler


class TestStartScheduler:
    def test_starts_when_enabled(self):
        with patch("app.scheduler.settings") as mock_settings, patch("app.scheduler.BackgroundScheduler") as mock_scheduler_class:
            mock_settings.stock_daily_sync_enabled = True
            start_scheduler()
            mock_scheduler_class.return_value.start.assert_called_once()
            stop_scheduler()

    def test_idempotent(self):
        with patch("app.scheduler.settings") as mock_settings, patch("app.scheduler.BackgroundScheduler") as mock_scheduler_class:
            mock_settings.stock_daily_sync_enabled = True
            start_scheduler()
            start_scheduler()
            mock_scheduler_class.return_value.start.assert_called_once()
            stop_scheduler()

    def test_noop_when_disabled(self):
        with patch("app.scheduler.settings") as mock_settings, patch("app.scheduler.BackgroundScheduler") as mock_scheduler_class:
            mock_settings.stock_daily_sync_enabled = False
            start_scheduler()
            mock_scheduler_class.return_value.start.assert_not_called()


class TestStopScheduler:
    def test_shutdown(self):
        with patch("app.scheduler.settings") as mock_settings, patch("app.scheduler.BackgroundScheduler") as mock_scheduler_class:
            mock_settings.stock_daily_sync_enabled = True
            start_scheduler()
            stop_scheduler()
            mock_scheduler_class.return_value.shutdown.assert_called_once_with(wait=False)

    def test_idempotent(self):
        stop_scheduler()
        # Should not raise


class TestDailyStockSyncJob:
    def test_calls_sync_and_closes_db(self):
        mock_db = MagicMock()
        with patch("app.scheduler.SessionLocal", return_value=mock_db), patch("app.scheduler.sync_recent_prices_for_active_stocks") as mock_sync:
            _daily_stock_sync_job()
            mock_sync.assert_called_once_with(mock_db)
            mock_db.close.assert_called_once()
