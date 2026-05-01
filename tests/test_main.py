import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app


class TestHealth:
    def test_health_check(self):
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == status.HTTP_200_OK
            assert response.json() == {"status": "healthy"}


class TestStartup:
    def test_scheduler_does_not_start_in_test_environment(self):
        with patch("app.main.start_scheduler") as mock_start_scheduler:
            with TestClient(app):
                pass
            mock_start_scheduler.assert_not_called()


class TestFrontendFallback:
    def test_serves_existing_file(self):
        with patch("os.path.exists", return_value=True), patch("os.path.isfile", return_value=True), patch("app.main.FileResponse") as mock_file:
            mock_file.return_value = {"mock": "response"}
            with TestClient(app) as client:
                response = client.get("/assets/app.js")
                assert response.status_code == status.HTTP_200_OK

    def test_fallback_to_index_html(self):
        with patch("os.path.exists", return_value=False), patch("app.main.FileResponse") as mock_file:
            mock_file.return_value = {"mock": "index"}
            with TestClient(app) as client:
                response = client.get("/some-route")
                assert response.status_code == status.HTTP_200_OK

    def test_api_routes_do_not_fallback_to_frontend(self):
        with patch("app.main.FileResponse") as mock_file:
            with TestClient(app) as client:
                response = client.get("/api/v1/missing")
                assert response.status_code == status.HTTP_404_NOT_FOUND
                assert response.json() == {"detail": "API endpoint not found"}
                mock_file.assert_not_called()

    def test_api_bare_path_does_not_fallback_to_frontend(self):
        with patch("app.main.FileResponse") as mock_file:
            with TestClient(app) as client:
                response = client.get("/api")
                assert response.status_code == status.HTTP_404_NOT_FOUND
                assert response.json() == {"detail": "API endpoint not found"}
                mock_file.assert_not_called()
