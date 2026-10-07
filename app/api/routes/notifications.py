"""
Notification routes for managing user notifications.
"""

import uuid
from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.user import User
from app.models.notification import Notification
from app.schemas.notification import NotificationResponse, NotificationListResponse, MarkReadRequest
from app.api.deps import get_current_user


router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="List notifications",
    description="Get all notifications for the current user."
)
async def list_notifications(
    unread_only: bool = Query(False, description="Only return unread notifications"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> NotificationListResponse:
    """
    List notifications for the current user.
    
    Supports filtering by read status and pagination.
    """
    # Build query
    query = select(Notification).where(Notification.user_id == current_user.id)
    
    if unread_only:
        query = query.where(Notification.is_read == False)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    
    # Get unread count
    unread_query = select(func.count()).where(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    )
    unread_count = (await db.execute(unread_query)).scalar()
    
    # Apply pagination
    query = query.order_by(Notification.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    notifications = result.scalars().all()
    
    return NotificationListResponse(
        notifications=[NotificationResponse.model_validate(n) for n in notifications],
        total=total,
        unread_count=unread_count,
        page=page,
        page_size=page_size
    )


@router.get(
    "/{notification_id}",
    response_model=NotificationResponse,
    summary="Get notification",
    description="Get a specific notification."
)
async def get_notification(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> NotificationResponse:
    """
    Get a specific notification by ID.
    """
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        )
    )
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    return NotificationResponse.model_validate(notification)


@router.post(
    "/mark-read",
    response_model=dict,
    summary="Mark notifications as read",
    description="Mark one or more notifications as read."
)
async def mark_notifications_read(
    request: MarkReadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Mark notifications as read.
    
    Provide a list of notification IDs to mark as read.
    """
    now = datetime.utcnow()
    updated_count = 0
    
    for notification_id in request.notification_ids:
        result = await db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == current_user.id
            )
        )
        notification = result.scalar_one_or_none()
        
        if notification and not notification.is_read:
            notification.is_read = True
            notification.read_at = now
            updated_count += 1
    
    await db.commit()
    
    return {
        "message": f"Marked {updated_count} notifications as read",
        "updated_count": updated_count
    }


@router.post(
    "/mark-all-read",
    response_model=dict,
    summary="Mark all as read",
    description="Mark all notifications as read."
)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Mark all notifications as read for the current user.
    """
    now = datetime.utcnow()
    
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        )
    )
    notifications = result.scalars().all()
    
    for notification in notifications:
        notification.is_read = True
        notification.read_at = now
    
    await db.commit()
    
    return {
        "message": f"Marked {len(notifications)} notifications as read",
        "updated_count": len(notifications)
    }


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete notification",
    description="Delete a specific notification."
)
async def delete_notification(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Delete a specific notification.
    """
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        )
    )
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    await db.delete(notification)
    await db.commit()
