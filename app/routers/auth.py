from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, get_current_active_user
from app.models import User, TokenBlacklist
from app.schemas import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    TokenPair,
    UserCreate,
    UserRead,
)
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    # Check existing username
    existing_user = db.query(User).filter(User.username == user_in.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered",
        )

    # Check existing email
    existing_email = db.query(User).filter(User.email == user_in.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return MessageResponse(message="User registered successfully")


@router.post("/login", response_model=TokenPair)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == credentials.username).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    access_token = create_access_token(user_id=user.id)
    refresh_token = create_refresh_token(user_id=user.id)

    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", response_model=MessageResponse)
def logout(
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    db: Session = Depends(get_db),
):
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    jti = payload.get("jti")
    exp_timestamp = payload.get("exp")

    if jti is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token missing JTI",
        )

    # Check if already blacklisted (idempotent)
    existing = db.query(TokenBlacklist).filter(TokenBlacklist.token_jti == jti).first()
    if existing:
        return MessageResponse(message="Logged out successfully")

    expires_at = datetime.now(timezone.utc) + timedelta(days=1)
    if exp_timestamp:
        try:
            expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        except (ValueError, OSError):
            pass

    blacklist_entry = TokenBlacklist(token_jti=jti, expires_at=expires_at)
    db.add(blacklist_entry)
    db.commit()

    return MessageResponse(message="Logged out successfully")


@router.post("/refresh", response_model=TokenPair)
def refresh(request: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token(request.refresh_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")
    jti = payload.get("jti")
    token_type = payload.get("type")

    if user_id is None or jti is None or token_type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Check blacklist
    blacklisted = db.query(TokenBlacklist).filter(TokenBlacklist.token_jti == jti).first()
    if blacklisted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Rotate refresh token: blacklist old one, issue new pair
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    exp_timestamp = payload.get("exp")
    if exp_timestamp:
        try:
            expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        except (ValueError, OSError):
            pass

    blacklist_entry = TokenBlacklist(token_jti=jti, expires_at=expires_at)
    db.add(blacklist_entry)

    new_access_token = create_access_token(user_id=user.id)
    new_refresh_token = create_refresh_token(user_id=user.id)

    db.commit()

    return TokenPair(access_token=new_access_token, refresh_token=new_refresh_token)


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user
