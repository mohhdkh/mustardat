"""
Pydantic schemas for Notification-related API operations.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict

from app.models.notification import NotificationType


class NotificationResponse(BaseModel):
    """Schema for notification response."""
    id: str
    notification_type: str
    subject: str
    body: str
    related_item_id: Optional[str] = None
    related_match_id: Optional[str] = None
    is_sent: bool
    is_read: bool
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    """Schema for paginated notification list."""
    notifications: List[NotificationResponse]
    total: int
    unread_count: int
    page: int
    page_size: int


class NotificationCreate(BaseModel):
    """Internal schema for creating notifications."""
    user_id: str
    notification_type: str
    subject: str
    body: str
    related_item_id: Optional[str] = None
    related_match_id: Optional[str] = None


class MarkReadRequest(BaseModel):
    """Schema for marking notifications as read."""
    notification_ids: List[str]
