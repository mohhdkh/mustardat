"""
Authentication service with JWT tokens.
"""

from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.schemas.user import TokenPayload


class AuthService:
    """Service for authentication operations."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        # bcrypt has a 72-byte limit, truncate if necessary
        password_bytes = password.encode('utf-8')[:72]
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        # bcrypt has a 72-byte limit, truncate if necessary
        password_bytes = plain_password.encode('utf-8')[:72]
        hashed_bytes = hashed_password.encode('utf-8')
        try:
            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except Exception:
            return False
    
    @staticmethod
    def create_access_token(
        user_id: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token.
        
        Args:
            user_id: User's UUID
            expires_delta: Custom expiration time
        
        Returns:
            Encoded JWT token string
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.access_token_expire_minutes
            )
        
        payload = {
            "sub": str(user_id),
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        
        encoded_jwt = jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )
        
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Optional[TokenPayload]:
        """
        Decode and validate a JWT token.
        
        Args:
            token: JWT token string
        
        Returns:
            TokenPayload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm]
            )
            
            return TokenPayload(
                sub=payload["sub"],
                exp=datetime.fromtimestamp(payload["exp"]),
                iat=datetime.fromtimestamp(payload["iat"])
            )
        except JWTError:
            return None
    
    @staticmethod
    async def authenticate_user(
        db: AsyncSession,
        email: str,
        password: str
    ) -> Optional[User]:
        """
        Authenticate a user by email and password.
        
        Args:
            db: Database session
            email: User's email
            password: Plain text password
        
        Returns:
            User if authenticated, None otherwise
        """
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        if not AuthService.verify_password(password, user.hashed_password):
            return None
        
        return user
    
    @staticmethod
    async def get_user_by_id(
        db: AsyncSession,
        user_id: str
    ) -> Optional[User]:
        """Get a user by their ID."""
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_by_email(
        db: AsyncSession,
        email: str
    ) -> Optional[User]:
        """Get a user by their email."""
        result = await db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()


# Singleton instance
auth_service = AuthService()
