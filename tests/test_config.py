import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.config import Settings


class TestSettingsDefaults:
    def test_default_app_name(self):
        s = Settings()
        assert s.app_name == "Auth Service"

    def test_default_environment(self):
        s = Settings()
        assert s.environment == "development"

    def test_default_debug(self):
        s = Settings()
        assert s.debug is False

    def test_default_algorithm(self):
        s = Settings()
        assert s.algorithm == "HS256"

    def test_default_token_expirations(self):
        s = Settings()
        assert s.access_token_expire_minutes == 15
        assert s.refresh_token_expire_days == 7

    def test_secret_key_has_reasonable_length(self):
        s = Settings()
        assert len(s.secret_key) >= 16


class TestSettingsEnvOverride:
    def test_env_override_app_name(self):
        with patch.dict(os.environ, {"APP_NAME": "Test App"}, clear=False):
            s = Settings()
            assert s.app_name == "Test App"

    def test_env_override_token_expiry(self):
        with patch.dict(os.environ, {"ACCESS_TOKEN_EXPIRE_MINUTES": "30"}, clear=False):
            s = Settings()
            assert s.access_token_expire_minutes == 30

    def test_env_override_database_url(self):
        with patch.dict(os.environ, {"DATABASE_URL": "sqlite:///./test.db"}, clear=False):
            s = Settings()
            assert s.database_url == "sqlite:///./test.db"

    def test_env_override_cors_origins(self):
        with patch.dict(os.environ, {"CORS_ORIGINS": "http://localhost:3000,http://localhost:8080"}, clear=False):
            s = Settings()
            assert s.cors_origins == "http://localhost:3000,http://localhost:8080"


class TestSettingsValidation:
    def test_invalid_token_expiry_type(self):
        with patch.dict(os.environ, {"ACCESS_TOKEN_EXPIRE_MINUTES": "not_a_number"}, clear=False):
            with pytest.raises(ValidationError):
                Settings()

    def test_invalid_debug_type(self):
        with patch.dict(os.environ, {"DEBUG": "not_a_bool"}, clear=False):
            with pytest.raises(ValidationError):
                Settings()
