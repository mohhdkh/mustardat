"""
User management routes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.services.auth import auth_service
from app.api.deps import get_current_user


router = APIRouter(prefix="/users", tags=["Users"])


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new user",
    description="Register a new user account."
)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Create a new user account.
    
    - **email**: Unique email address
    - **password**: Password (min 8 characters)
    - **full_name**: Optional full name
    - **phone_number**: Optional phone for SMS notifications
    
    Returns the created user (without password).
    """
    # Check if email already exists
    existing_user = await auth_service.get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = auth_service.hash_password(user_data.password)
    
    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        phone_number=user_data.phone_number
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return UserResponse.model_validate(user)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get the currently authenticated user's profile."
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """
    Get the current authenticated user's profile.
    
    Requires authentication.
    """
    return UserResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user",
    description="Update the current user's profile."
)
async def update_current_user(
    full_name: str = None,
    phone_number: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Update the current user's profile.
    
    Only provided fields will be updated.
    """
    if full_name is not None:
        current_user.full_name = full_name
    
    if phone_number is not None:
        current_user.phone_number = phone_number
    
    await db.commit()
    await db.refresh(current_user)
    
    return UserResponse.model_validate(current_user)


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete current user",
    description="Delete the current user's account and all associated data."
)
async def delete_current_user(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Delete the current user's account.
    
    This will also delete all items, images, and matches associated with the user.
    This action is irreversible.
    """
    await db.delete(current_user)
    await db.commit()
