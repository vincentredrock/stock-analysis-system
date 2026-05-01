import pytest
from pydantic import ValidationError

from app.schemas import (
    LoginRequest,
    RefreshRequest,
    StockBase,
    TokenPair,
    TokenPayload,
    UserBase,
    UserCreate,
    UserRead,
    WatchlistBase,
)


class TestUserCreate:
    def test_valid_user(self):
        user = UserCreate(
            username="testuser",
            email="test@example.com",
            password="Password123!",
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.password == "Password123!"

    @pytest.mark.parametrize(
        "password,expected_error",
        [
            ("short1!", "String should have at least 8 characters"),
            ("alllowercase1!", "Password must contain at least one uppercase letter"),
            ("ALLUPPERCASE1!", "Password must contain at least one lowercase letter"),
            ("NoDigitsHere!", "Password must contain at least one digit"),
            ("NoSpecial123", "Password must contain at least one special character"),
        ],
    )
    def test_password_complexity(self, password, expected_error):
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="testuser",
                email="test@example.com",
                password=password,
            )
        assert expected_error in str(exc_info.value)

    def test_username_too_short(self):
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="ab",
                email="test@example.com",
                password="Password123!",
            )
        assert "String should have at least 3 characters" in str(exc_info.value)

    def test_username_too_long(self):
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="a" * 51,
                email="test@example.com",
                password="Password123!",
            )
        assert "String should have at most 50 characters" in str(exc_info.value)

    def test_password_too_long(self):
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="P" + "a" * 127 + "1!",
            )
        assert "String should have at most 128 characters" in str(exc_info.value)

    def test_invalid_email(self):
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="testuser",
                email="not-an-email",
                password="Password123!",
            )
        assert "value is not a valid email address" in str(exc_info.value)


class TestTokenPair:
    def test_default_token_type(self):
        pair = TokenPair(access_token="abc", refresh_token="def")
        assert pair.token_type == "bearer"

    def test_custom_token_type(self):
        pair = TokenPair(access_token="abc", refresh_token="def", token_type="basic")
        assert pair.token_type == "basic"


class TestLoginRequest:
    def test_valid_login(self):
        req = LoginRequest(username="user", password="pass")
        assert req.username == "user"
        assert req.password == "pass"


class TestRefreshRequest:
    def test_valid_refresh(self):
        req = RefreshRequest(refresh_token="sometoken")
        assert req.refresh_token == "sometoken"


class TestTokenPayload:
    def test_optional_fields(self):
        payload = TokenPayload()
        assert payload.sub is None
        assert payload.jti is None
        assert payload.type is None
        assert payload.exp is None

    def test_with_values(self):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        payload = TokenPayload(sub=1, jti="uuid", type="access", exp=now)
        assert payload.sub == 1
        assert payload.jti == "uuid"
        assert payload.type == "access"


class TestUserBase:
    def test_valid(self):
        user = UserBase(username="testuser", email="test@example.com")
        assert user.username == "testuser"
        assert user.email == "test@example.com"

    def test_username_too_short(self):
        with pytest.raises(ValidationError) as exc_info:
            UserBase(username="ab", email="test@example.com")
        assert "String should have at least 3 characters" in str(exc_info.value)

    def test_username_too_long(self):
        with pytest.raises(ValidationError) as exc_info:
            UserBase(username="a" * 51, email="test@example.com")
        assert "String should have at most 50 characters" in str(exc_info.value)

    def test_invalid_email(self):
        with pytest.raises(ValidationError) as exc_info:
            UserBase(username="testuser", email="not-an-email")
        assert "value is not a valid email address" in str(exc_info.value)


class TestStockBase:
    def test_valid_twse(self):
        stock = StockBase(symbol="2330", name="台積電", market="TWSE", industry="半導體業")
        assert stock.market == "TWSE"

    def test_valid_tpex(self):
        stock = StockBase(symbol="8080", name="測試", market="TPEx")
        assert stock.market == "TPEx"

    def test_invalid_market(self):
        with pytest.raises(ValidationError) as exc_info:
            StockBase(symbol="2330", name="台積電", market="NYSE")
        assert "String should match pattern" in str(exc_info.value)

    def test_symbol_too_long(self):
        with pytest.raises(ValidationError) as exc_info:
            StockBase(symbol="a" * 11, name="台積電", market="TWSE")
        assert "String should have at most 10 characters" in str(exc_info.value)

    def test_empty_name(self):
        with pytest.raises(ValidationError) as exc_info:
            StockBase(symbol="2330", name="", market="TWSE")
        assert "String should have at least 1 character" in str(exc_info.value)

    def test_industry_max_length(self):
        with pytest.raises(ValidationError) as exc_info:
            StockBase(symbol="2330", name="台積電", market="TWSE", industry="x" * 51)
        assert "String should have at most 50 characters" in str(exc_info.value)


class TestWatchlistBase:
    def test_valid(self):
        wl = WatchlistBase(name="My List")
        assert wl.name == "My List"

    def test_empty_name(self):
        with pytest.raises(ValidationError) as exc_info:
            WatchlistBase(name="")
        assert "String should have at least 1 character" in str(exc_info.value)

    def test_name_too_long(self):
        with pytest.raises(ValidationError) as exc_info:
            WatchlistBase(name="x" * 101)
        assert "String should have at most 100 characters" in str(exc_info.value)
