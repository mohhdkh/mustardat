"""
API dependencies for authentication and database access.
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.user import User
from app.services.auth import auth_service


# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user.
    
    Validates the JWT token and returns the user.
    Raises 401 if token is invalid or user not found.
    """
    token = credentials.credentials
    
    # Decode and validate token
    payload = auth_service.decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    user = await auth_service.get_user_by_id(db, payload.sub)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Optional authentication dependency.
    
    Returns the user if authenticated, None otherwise.
    Does not raise exceptions for missing/invalid tokens.
    """
    if credentials is None:
        return None
    
    token = credentials.credentials
    payload = auth_service.decode_token(token)
    
    if payload is None:
        return None
    
    user = await auth_service.get_user_by_id(db, payload.sub)
    
    if user is None or not user.is_active:
        return None
    
    return user


def require_owner(item_user_id: str, current_user: User) -> None:
    """
    Check if the current user owns the resource.
    
    Raises 403 if not the owner.
    """
    if item_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource"
        )
