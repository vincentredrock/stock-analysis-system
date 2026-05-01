import re
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ─── Shared ──────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str


# ─── User Base ───────────────────────────────────────────

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]~/`\\'\\;]", v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserRead(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Token ───────────────────────────────────────────────

class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Optional[int] = None
    jti: Optional[str] = None
    type: Optional[str] = None
    exp: Optional[datetime] = None


class RefreshRequest(BaseModel):
    refresh_token: str


# ─── Auth ────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


# ─── Stock ───────────────────────────────────────────────

class StockBase(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    name: str = Field(..., min_length=1, max_length=100)
    market: str = Field(..., pattern=r"^(TWSE|TPEx)$")
    industry: Optional[str] = Field(None, max_length=50)


class StockCreate(StockBase):
    pass


class StockRead(StockBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Stock Price ─────────────────────────────────────────

class StockPriceRead(BaseModel):
    date: date
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: int
    change: Optional[Decimal] = None
    change_percent: Optional[Decimal] = None

    model_config = {"from_attributes": True}


class StockSyncStatusRead(BaseModel):
    symbol: str
    status: str
    synced_from: Optional[date] = None
    synced_to: Optional[date] = None
    last_attempt_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    last_error: Optional[str] = None
    records_upserted: int


class StockSyncJobCreate(BaseModel):
    symbol: str
    start: Optional[date] = None
    end: Optional[date] = None


class StockSyncJobRead(BaseModel):
    id: int
    symbol: str
    status: str
    start: Optional[date] = None
    end: Optional[date] = None
    message: Optional[str] = None
    error: Optional[str] = None
    records_upserted: int
    records_skipped: int
    months_requested: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class StockQuoteRead(BaseModel):
    symbol: str
    name: str
    price: Decimal
    open: Decimal
    high: Decimal
    low: Decimal
    close: Optional[Decimal] = None
    volume: int
    change: Optional[Decimal] = None
    change_percent: Optional[Decimal] = None
    last_updated: datetime

    model_config = {"from_attributes": True}


# ─── Watchlist ───────────────────────────────────────────

class WatchlistBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class WatchlistCreate(WatchlistBase):
    pass


class WatchlistUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)


class WatchlistItemCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)


class WatchlistItemRead(BaseModel):
    id: int
    stock: StockRead
    created_at: datetime

    model_config = {"from_attributes": True}


class WatchlistRead(WatchlistBase):
    id: int
    user_id: int
    items: List[StockRead] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WatchlistWithQuotesRead(BaseModel):
    id: int
    name: str
    quotes: List[StockQuoteRead] = []

    model_config = {"from_attributes": True}
