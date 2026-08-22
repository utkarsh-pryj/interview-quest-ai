"""
Authentication & User Management API Routes.
Conforms to Blueprint Section 16 & 18.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.db.session import get_async_db
from app.models.user import User
from app.schemas.auth import UserRegisterRequest, UserLoginRequest, TokenResponse, UserResponse
from app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token, oauth2_scheme

router = APIRouter(prefix="/auth", tags=["Authentication"])

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_db)
) -> User:
    """Dependency for authenticating JWT token and fetching user."""
    payload = decode_access_token(token)
    if not payload.sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    stmt = select(User).filter_by(id=payload.sub)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return user

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: UserRegisterRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """Register a new user with Argon2id hashed password."""
    # Check if user already exists
    stmt = select(User).filter_by(email=payload.email.lower())
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists."
        )

    user_id = str(uuid.uuid4())
    hashed_pwd = get_password_hash(payload.password)
    user = User(
        id=user_id,
        email=payload.email.lower(),
        password_hash=hashed_pwd,
        full_name=payload.full_name,
        is_active=True
    )
    db.add(user)
    await db.commit()

    token = create_access_token(subject=user.id, email=user.email)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        full_name=user.full_name
    )

@router.post("/login", response_model=TokenResponse)
async def login_user(
    payload: UserLoginRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """Authenticate user and return JWT access token."""
    stmt = select(User).filter_by(email=payload.email.lower())
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )

    token = create_access_token(subject=user.id, email=user.email)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        full_name=user.full_name
    )

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Get authenticated user profile."""
    return current_user
