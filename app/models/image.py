"""
Image model for storing uploaded images and their metadata.
"""

import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.item import Item
    from app.models.embedding import ImageEmbedding


class Image(Base):
    """
    Uploaded image for a lost/found item.
    
    Stores:
    - Local storage paths (original and processed)
    - EXIF metadata extracted from the image
    - Processing status
    """
    __tablename__ = "images"
    
    # Primary key - UUID as string for SQLite
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True
    )
    
    # Parent item reference
    item_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Storage paths (local file paths)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path_original: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        unique=True  # Path to original uploaded image
    )
    file_path_processed: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True  # Path to processed/cropped image
    )
    file_path_thumbnail: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True  # Path to thumbnail
    )
    
    # Image metadata
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # bytes
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # EXIF metadata (extracted from image, stored as JSON string)
    exif_data_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Extracted EXIF metadata as JSON string"
    )
    
    # EXIF-derived location (if available)
    exif_latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    exif_longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    exif_datetime: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Processing status
    is_processed: Mapped[bool] = mapped_column(default=False)
    processing_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Order in item's image gallery (1-6)
    display_order: Mapped[int] = mapped_column(Integer, default=1)
    
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
    item: Mapped["Item"] = relationship("Item", back_populates="images")
    embedding: Mapped[Optional["ImageEmbedding"]] = relationship(
        "ImageEmbedding",
        back_populates="image",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Image {self.original_filename}>"


