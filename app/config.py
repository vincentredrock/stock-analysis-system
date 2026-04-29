import secrets
from datetime import timedelta
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    app_name: str = "Auth Service"
    environment: str = "development"
    debug: bool = False

    # Security
    secret_key: str = secrets.token_urlsafe(32)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Database
    database_url: str = "postgresql://authservice:authservice_password@localhost:5432/auth_db"

    # Stock data sync
    stock_history_start_date: str = "2010-01-01"
    stock_sync_rate_limit_seconds: float = 1.0
    stock_daily_sync_enabled: bool = True
    stock_daily_sync_hour: int = 16
    stock_daily_sync_minute: int = 30
    stock_daily_sync_lookback_days: int = 10

    # CORS
    cors_origins: str = "*"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
