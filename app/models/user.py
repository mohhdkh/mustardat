"""
User model for authentication and item ownership.
"""

import uuid
from datetime import datetime
from typing import List, TYPE_CHECKING

from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.item import Item
    from app.models.notification import Notification


class User(Base):
    """
    User account model.
    
    Stores user credentials and profile information.
    Personal contact info is only revealed after mutual match confirmation.
    """
    __tablename__ = "users"
    
    # Primary key - UUID as string for SQLite compatibility
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True
    )
    
    # Authentication
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    
    # Profile (revealed only after match confirmation)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=True)
    
    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    
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
    last_login: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Relationships
    items: Mapped[List["Item"]] = relationship(
        "Item",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User {self.email}>"
