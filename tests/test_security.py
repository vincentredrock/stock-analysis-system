import time
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.config import settings
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_produces_different_values(self):
        password = "SuperSecret123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        assert hash1 != hash2  # bcrypt salts are random

    def test_verify_correct_password(self):
        password = "SuperSecret123!"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_verify_incorrect_password(self):
        password = "SuperSecret123!"
        hashed = get_password_hash(password)
        assert verify_password("WrongPassword123!", hashed) is False

    def test_verify_unicode_password(self):
        password = "パスワード123!"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_verify_empty_password_fails(self):
        password = "SuperSecret123!"
        hashed = get_password_hash(password)
        assert verify_password("", hashed) is False


class TestCreateAccessToken:
    def test_token_contains_expected_claims(self):
        token = create_access_token(user_id=42)
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        assert payload["sub"] == "42"
        assert payload["type"] == "access"
        assert "jti" in payload
        assert "exp" in payload
        assert "iat" in payload

    def test_default_expiration_is_reasonable(self):
        before = datetime.now(timezone.utc)
        token = create_access_token(user_id=1)
        after = datetime.now(timezone.utc)
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        expected_min = before + timedelta(minutes=settings.access_token_expire_minutes) - timedelta(seconds=5)
        expected_max = after + timedelta(minutes=settings.access_token_expire_minutes) + timedelta(seconds=5)
        assert expected_min <= exp <= expected_max

    def test_custom_expiration(self):
        token = create_access_token(user_id=1, expires_delta=timedelta(minutes=5))
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        delta = exp - iat
        assert timedelta(minutes=4, seconds=55) <= delta <= timedelta(minutes=5, seconds=5)

    def test_unique_jti_per_token(self):
        token1 = create_access_token(user_id=1)
        token2 = create_access_token(user_id=1)
        payload1 = jwt.decode(token1, settings.secret_key, algorithms=[settings.algorithm])
        payload2 = jwt.decode(token2, settings.secret_key, algorithms=[settings.algorithm])
        assert payload1["jti"] != payload2["jti"]


class TestCreateRefreshToken:
    def test_token_contains_expected_claims(self):
        token = create_refresh_token(user_id=99)
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        assert payload["sub"] == "99"
        assert payload["type"] == "refresh"
        assert "jti" in payload
        assert "exp" in payload
        assert "iat" in payload

    def test_default_expiration_is_reasonable(self):
        before = datetime.now(timezone.utc)
        token = create_refresh_token(user_id=1)
        after = datetime.now(timezone.utc)
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        expected_min = before + timedelta(days=settings.refresh_token_expire_days) - timedelta(seconds=5)
        expected_max = after + timedelta(days=settings.refresh_token_expire_days) + timedelta(seconds=5)
        assert expected_min <= exp <= expected_max

    def test_custom_expiration(self):
        token = create_refresh_token(user_id=1, expires_delta=timedelta(hours=2))
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        delta = exp - iat
        assert timedelta(hours=1, minutes=59, seconds=55) <= delta <= timedelta(hours=2, seconds=5)


class TestDecodeToken:
    def test_decode_valid_access_token(self):
        token = create_access_token(user_id=1)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "1"
        assert payload["type"] == "access"

    def test_decode_valid_refresh_token(self):
        token = create_refresh_token(user_id=2)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "2"
        assert payload["type"] == "refresh"

    def test_decode_expired_token_returns_none(self):
        token = create_access_token(user_id=1, expires_delta=timedelta(seconds=-1))
        payload = decode_token(token)
        assert payload is None

    def test_decode_malformed_token_returns_none(self):
        assert decode_token("not.a.token") is None

    def test_decode_empty_token_returns_none(self):
        assert decode_token("") is None

    def test_decode_token_with_wrong_secret_returns_none(self):
        token = jwt.encode(
            {"sub": "1", "type": "access"},
            "wrong-secret",
            algorithm=settings.algorithm,
        )
        assert decode_token(token) is None

    def test_decode_token_with_none_returns_none(self):
        assert decode_token(None) is None
