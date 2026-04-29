from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, status

from app.dependencies import get_current_active_user, get_current_user
from app.models import TokenBlacklist, User


class TestGetCurrentUser:
    def test_valid_token(self, db_session):
        user = User(username="depuser", email="dep@example.com", hashed_password="hp")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        from app.security import create_access_token
        token = create_access_token(user_id=user.id)

        result = get_current_user(token=token, db=db_session)
        assert result.id == user.id
        assert result.username == "depuser"

    def test_missing_token_raises_401(self, db_session):
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=None, db=db_session)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_token_raises_401(self, db_session):
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token="not.a.token", db=db_session)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_without_sub_raises_401(self, db_session):
        from jose import jwt
        from app.config import settings
        token = jwt.encode(
            {"jti": "some-jti", "type": "access", "exp": 9999999999},
            settings.secret_key,
            algorithm=settings.algorithm,
        )
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, db=db_session)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_without_jti_raises_401(self, db_session):
        from jose import jwt
        from app.config import settings
        token = jwt.encode(
            {"sub": "1", "type": "access", "exp": 9999999999},
            settings.secret_key,
            algorithm=settings.algorithm,
        )
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, db=db_session)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token_instead_of_access_raises_401(self, db_session):
        from app.security import create_refresh_token
        token = create_refresh_token(user_id=1)
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, db=db_session)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_blacklisted_token_raises_401(self, db_session):
        from app.security import create_access_token
        from jose import jwt
        from app.config import settings

        user = User(username="bluser", email="bl@example.com", hashed_password="hp")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        token = create_access_token(user_id=user.id)
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        blacklist = TokenBlacklist(token_jti=payload["jti"], expires_at=datetime.now(timezone.utc))
        db_session.add(blacklist)
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, db=db_session)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_not_found_raises_401(self, db_session):
        from app.security import create_access_token
        token = create_access_token(user_id=99999)
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, db=db_session)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_inactive_user_raises_401(self, db_session):
        user = User(username="inact", email="inact@example.com", hashed_password="hp", is_active=False)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        from app.security import create_access_token
        token = create_access_token(user_id=user.id)

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, db=db_session)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetCurrentActiveUser:
    def test_returns_user(self, db_session):
        user = User(username="act", email="act@example.com", hashed_password="hp", is_active=True)
        result = get_current_active_user(current_user=user)
        assert result.username == "act"
