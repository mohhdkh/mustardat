"""
Notification model for in-app notifications.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class NotificationType(str, Enum):
    """Types of notifications sent to users."""
    MATCH_FOUND = "match_found"             # New potential match discovered
    MATCH_CONFIRMED = "match_confirmed"     # Other party confirmed the match
    MATCH_REJECTED = "match_rejected"       # Other party rejected the match
    CONTACT_REVEALED = "contact_revealed"   # Both confirmed, contact info shared
    ITEM_EXPIRED = "item_expired"           # Item listing expired
    SYSTEM = "system"                       # System notifications


class Notification(Base):
    """
    Notification record for tracking in-app notifications.
    """
    __tablename__ = "notifications"
    
    # Primary key - UUID as string for SQLite
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True
    )
    
    # Recipient
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Notification type (stored as string for SQLite)
    notification_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    
    # Content
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Related entities (for context)
    related_item_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True
    )
    related_match_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True
    )
    
    # Delivery status
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    
    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="notifications")
    
    def __repr__(self) -> str:
        return f"<Notification {self.notification_type} to {self.user_id}>"
