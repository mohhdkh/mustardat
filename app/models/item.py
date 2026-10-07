"""
Item model for lost and found items.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import String, Text, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.image import Image
    from app.models.match import Match


class ItemType(str, Enum):
    """
    Predefined item categories for filtering matches.
    Matching only occurs within the same item type.
    """
    PHONE = "phone"
    WALLET = "wallet"
    KEYS = "keys"
    BAG = "bag"
    LAPTOP = "laptop"
    TABLET = "tablet"
    WATCH = "watch"
    JEWELRY = "jewelry"
    GLASSES = "glasses"
    HEADPHONES = "headphones"
    CAMERA = "camera"
    DOCUMENTS = "documents"
    PET = "pet"
    CLOTHING = "clothing"
    ELECTRONICS = "electronics"
    OTHER = "other"


class ItemStatus(str, Enum):
    """Item lifecycle status."""
    ACTIVE = "active"           # Actively searching for match
    MATCHED = "matched"         # Potential match found
    RESOLVED = "resolved"       # Item returned to owner
    EXPIRED = "expired"         # Search period ended
    CANCELLED = "cancelled"     # User cancelled listing


class Item(Base):
    """
    Lost or Found item listing.
    
    Contains metadata about the item and links to uploaded images.
    """
    __tablename__ = "items"
    
    # Primary key - UUID as string for SQLite
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True
    )
    
    # Owner reference
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Item classification (stored as string for SQLite)
    item_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    lost_or_found: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True  # "lost" or "found"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=ItemStatus.ACTIVE.value,
        index=True
    )
    
    # Description
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Location (where item was lost/found)
    location_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True  # Human-readable location
    )
    
    # Date/time when item was lost/found
    event_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="items")
    images: Mapped[List["Image"]] = relationship(
        "Image",
        back_populates="item",
        cascade="all, delete-orphan"
    )
    
    # Matches where this item is the source (searching)
    matches_as_source: Mapped[List["Match"]] = relationship(
        "Match",
        foreign_keys="Match.source_item_id",
        back_populates="source_item",
        cascade="all, delete-orphan"
    )
    
    # Matches where this item is the target (found in search)
    matches_as_target: Mapped[List["Match"]] = relationship(
        "Match",
        foreign_keys="Match.target_item_id",
        back_populates="target_item",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Item {self.title} ({self.lost_or_found})>"
