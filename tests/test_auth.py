import pytest
from fastapi import status

from app.models import User, TokenBlacklist
from app.security import create_access_token, create_refresh_token, get_password_hash


# ─── Helpers ──────────────────────────────────────────────

def register_user(client, username="testuser", email="test@example.com", password="Password123!"):
    return client.post("/api/v1/users", json={
        "username": username,
        "email": email,
        "password": password,
    })


def login_user(client, username="testuser", password="Password123!"):
    return client.post("/api/v1/sessions", json={
        "username": username,
        "password": password,
    })


# ─── Health ───────────────────────────────────────────────

class TestHealth:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "healthy"}


# ─── Register ─────────────────────────────────────────────

class TestRegister:
    def test_register_success(self, client):
        response = register_user(client)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_register_duplicate_username(self, client):
        register_user(client, username="dupeuser", email="a@example.com")
        response = register_user(client, username="dupeuser", email="b@example.com")
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "Username already registered" in response.json()["detail"]

    def test_register_duplicate_email(self, client):
        register_user(client, username="user1", email="same@example.com")
        response = register_user(client, username="user2", email="same@example.com")
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "Email already registered" in response.json()["detail"]

    def test_register_invalid_password_no_uppercase(self, client):
        response = register_user(client, password="lowercase1!")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_invalid_password_no_special(self, client):
        response = register_user(client, password="Password123")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_invalid_email(self, client):
        response = client.post("/api/v1/users", json={
            "username": "testuser",
            "email": "not-an-email",
            "password": "Password123!",
        })
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_short_username(self, client):
        response = client.post("/api/v1/users", json={
            "username": "ab",
            "email": "test@example.com",
            "password": "Password123!",
        })
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_missing_fields(self, client):
        response = client.post("/api/v1/users", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_user_is_active_by_default(self, client, db_session):
        register_user(client)
        user = db_session.query(User).filter(User.username == "testuser").first()
        assert user is not None
        assert user.is_active is True


# ─── Login ────────────────────────────────────────────────

class TestLogin:
    def test_login_success(self, client):
        register_user(client)
        response = login_user(client)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_username(self, client):
        register_user(client)
        response = login_user(client, username="wronguser")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Incorrect username or password" in response.json()["detail"]

    def test_login_invalid_password(self, client):
        register_user(client)
        response = login_user(client, password="WrongPassword123!")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Incorrect username or password" in response.json()["detail"]

    def test_login_inactive_user(self, client, db_session):
        register_user(client)
        user = db_session.query(User).filter(User.username == "testuser").first()
        user.is_active = False
        db_session.commit()

        response = login_user(client)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "User account is inactive" in response.json()["detail"]

    def test_login_missing_fields(self, client):
        response = client.post("/api/v1/sessions", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ─── /me ──────────────────────────────────────────────────

class TestMe:
    def test_get_me_success(self, client):
        register_user(client)
        login_resp = login_user(client)
        token = login_resp.json()["access_token"]

        response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_get_me_no_token(self, client):
        response = client.get("/api/v1/users/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_me_invalid_token(self, client):
        response = client.get("/api/v1/users/me", headers={"Authorization": "Bearer invalidtoken"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_me_blacklisted_token(self, client, db_session):
        register_user(client)
        login_resp = login_user(client)
        token = login_resp.json()["access_token"]

        # Blacklist the token manually
        from jose import jwt
        from app.config import settings
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        blacklist = TokenBlacklist(token_jti=payload["jti"], expires_at=db_session.query(User).first().created_at)
        db_session.add(blacklist)
        db_session.commit()

        response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_me_inactive_user(self, client, db_session):
        register_user(client)
        login_resp = login_user(client)
        token = login_resp.json()["access_token"]

        user = db_session.query(User).filter(User.username == "testuser").first()
        user.is_active = False
        db_session.commit()

        response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ─── Logout ───────────────────────────────────────────────

class TestLogout:
    def test_logout_success(self, client, db_session):
        register_user(client)
        login_resp = login_user(client)
        token = login_resp.json()["access_token"]

        response = client.delete("/api/v1/sessions/current", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.content == b""

        # Verify token is blacklisted
        from jose import jwt
        from app.config import settings
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        blacklisted = db_session.query(TokenBlacklist).filter(TokenBlacklist.token_jti == payload["jti"]).first()
        assert blacklisted is not None

    def test_logout_idempotent(self, client):
        register_user(client)
        login_resp = login_user(client)
        token = login_resp.json()["access_token"]

        resp1 = client.delete("/api/v1/sessions/current", headers={"Authorization": f"Bearer {token}"})
        assert resp1.status_code == status.HTTP_204_NO_CONTENT

        resp2 = client.delete("/api/v1/sessions/current", headers={"Authorization": f"Bearer {token}"})
        assert resp2.status_code == status.HTTP_204_NO_CONTENT
        assert resp2.content == b""

    def test_logout_invalid_token(self, client):
        response = client.delete("/api/v1/sessions/current", headers={"Authorization": "Bearer invalid"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token" in response.json()["detail"]

    def test_logout_no_token(self, client):
        response = client.delete("/api/v1/sessions/current")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_token_without_jti(self, client):
        from jose import jwt
        from app.config import settings
        # Create token without JTI
        token = jwt.encode(
            {"sub": "1", "type": "access", "exp": 9999999999},
            settings.secret_key,
            algorithm=settings.algorithm,
        )
        response = client.delete("/api/v1/sessions/current", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Token missing JTI" in response.json()["detail"]


# ─── Refresh ──────────────────────────────────────────────

class TestRefresh:
    def test_refresh_success(self, client):
        register_user(client)
        login_resp = login_user(client)
        refresh_token = login_resp.json()["refresh_token"]

        response = client.post("/api/v1/token-refreshes", json={"refresh_token": refresh_token})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_invalid_token(self, client):
        response = client.post("/api/v1/token-refreshes", json={"refresh_token": "invalid"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid refresh token" in response.json()["detail"]

    def test_refresh_access_token_instead_of_refresh(self, client):
        register_user(client)
        login_resp = login_user(client)
        access_token = login_resp.json()["access_token"]

        response = client.post("/api/v1/token-refreshes", json={"refresh_token": access_token})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid refresh token" in response.json()["detail"]

    def test_refresh_blacklisted_token(self, client, db_session):
        register_user(client)
        login_resp = login_user(client)
        refresh_token = login_resp.json()["refresh_token"]

        from jose import jwt
        from app.config import settings
        payload = jwt.decode(refresh_token, settings.secret_key, algorithms=[settings.algorithm])
        blacklist = TokenBlacklist(
            token_jti=payload["jti"],
            expires_at=db_session.query(User).first().created_at,
        )
        db_session.add(blacklist)
        db_session.commit()

        response = client.post("/api/v1/token-refreshes", json={"refresh_token": refresh_token})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Refresh token has been revoked" in response.json()["detail"]

    def test_refresh_user_not_found(self, client):
        # Create a token for a non-existent user
        refresh_token = create_refresh_token(user_id=99999)
        response = client.post("/api/v1/token-refreshes", json={"refresh_token": refresh_token})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "User not found or inactive" in response.json()["detail"]

    def test_refresh_inactive_user(self, client, db_session):
        register_user(client)
        login_resp = login_user(client)
        refresh_token = login_resp.json()["refresh_token"]

        user = db_session.query(User).filter(User.username == "testuser").first()
        user.is_active = False
        db_session.commit()

        response = client.post("/api/v1/token-refreshes", json={"refresh_token": refresh_token})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "User not found or inactive" in response.json()["detail"]

    def test_refresh_token_without_sub(self, client):
        from jose import jwt
        from app.config import settings
        token = jwt.encode(
            {"jti": "some-jti", "type": "refresh", "exp": 9999999999},
            settings.secret_key,
            algorithm=settings.algorithm,
        )
        response = client.post("/api/v1/token-refreshes", json={"refresh_token": token})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid refresh token" in response.json()["detail"]

    def test_refresh_token_without_jti(self, client):
        from jose import jwt
        from app.config import settings
        token = jwt.encode(
            {"sub": "1", "type": "refresh", "exp": 9999999999},
            settings.secret_key,
            algorithm=settings.algorithm,
        )
        response = client.post("/api/v1/token-refreshes", json={"refresh_token": token})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid refresh token" in response.json()["detail"]

    def test_refresh_rotates_token(self, client):
        register_user(client)
        login_resp = login_user(client)
        old_refresh_token = login_resp.json()["refresh_token"]

        response = client.post("/api/v1/token-refreshes", json={"refresh_token": old_refresh_token})
        assert response.status_code == status.HTTP_200_OK
        new_refresh_token = response.json()["refresh_token"]

        # Old token should now be blacklisted
        re_response = client.post("/api/v1/token-refreshes", json={"refresh_token": old_refresh_token})
        assert re_response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Refresh token has been revoked" in re_response.json()["detail"]

        # New token should work
        new_response = client.post("/api/v1/token-refreshes", json={"refresh_token": new_refresh_token})
        assert new_response.status_code == status.HTTP_200_OK


# ─── Token blacklist behavior ─────────────────────────────

class TestTokenBlacklist:
    def test_blacklisted_access_token_cannot_access_protected(self, client, db_session):
        register_user(client)
        login_resp = login_user(client)
        access_token = login_resp.json()["access_token"]

        # Logout (blacklist)
        client.delete("/api/v1/sessions/current", headers={"Authorization": f"Bearer {access_token}"})

        # Try to access protected route
        response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_blacklisted_refresh_token_cannot_refresh(self, client, db_session):
        register_user(client)
        login_resp = login_user(client)
        refresh_token = login_resp.json()["refresh_token"]

        # Manually blacklist the refresh token
        from jose import jwt
        from app.config import settings
        payload = jwt.decode(refresh_token, settings.secret_key, algorithms=[settings.algorithm])
        entry = TokenBlacklist(token_jti=payload["jti"], expires_at=db_session.query(User).first().created_at)
        db_session.add(entry)
        db_session.commit()

        response = client.post("/api/v1/token-refreshes", json={"refresh_token": refresh_token})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Refresh token has been revoked" in response.json()["detail"]


class TestLegacyAuthRoutes:
    @pytest.mark.parametrize(
        ("method", "path"),
        [
            ("post", "/api/v1/auth/register"),
            ("post", "/api/v1/auth/login"),
            ("post", "/api/v1/auth/logout"),
            ("post", "/api/v1/auth/refresh"),
            ("get", "/api/v1/auth/me"),
        ],
    )
    def test_action_oriented_auth_routes_are_removed(self, client, method, path):
        response = getattr(client, method)(path)
        assert response.status_code == status.HTTP_404_NOT_FOUND
