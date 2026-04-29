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
