"""
Authentication routes for login and token management.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.user import UserLogin, Token
from app.services.auth import auth_service
from app.config import settings


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=Token,
    summary="User login",
    description="Authenticate with email and password to receive a JWT token."
)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
) -> Token:
    """
    Authenticate user and return JWT token.
    
    - **email**: User's registered email
    - **password**: User's password
    
    Returns a JWT token valid for the configured expiration time.
    """
    user = await auth_service.authenticate_user(
        db, credentials.email, credentials.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()
    
    # Create access token
    access_token = auth_service.create_access_token(user.id)
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh token",
    description="Get a new token using a valid existing token."
)
async def refresh_token(
    credentials: str = Depends(lambda: None),  # Placeholder
    db: AsyncSession = Depends(get_db)
) -> Token:
    """
    Refresh an existing valid token.
    
    Note: This is a simplified implementation.
    In production, use refresh tokens with longer expiry.
    """
    # This would validate the current token and issue a new one
    # For now, this is a placeholder
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Token refresh not implemented. Please login again."
    )
