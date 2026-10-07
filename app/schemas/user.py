"""
Pydantic schemas for User-related API operations.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Password (min 8 characters)"
    )
    full_name: Optional[str] = Field(
        None,
        max_length=255,
        description="User's full name"
    )
    phone_number: Optional[str] = Field(
        None,
        max_length=20,
        description="Phone number for SMS notifications"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "securepassword123",
                "full_name": "John Doe",
                "phone_number": "+1234567890"
            }
        }
    )


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "securepassword123"
            }
        }
    )


class UserResponse(BaseModel):
    """Schema for user response (public info only)."""
    id: str
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class UserContactInfo(BaseModel):
    """
    Schema for revealing contact info after match confirmation.
    Only returned when both parties confirm a match.
    """
    full_name: Optional[str] = None
    email: EmailStr
    phone_number: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiry in seconds")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800
            }
        }
    )


class TokenPayload(BaseModel):
    """Schema for JWT token payload."""
    sub: str  # User ID
    exp: datetime
    iat: datetime
