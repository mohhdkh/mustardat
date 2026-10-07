"""
ImageEmbedding model for storing vector embeddings and perceptual hashes.
Used for similarity search and matching.
"""

import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Integer, DateTime, ForeignKey, LargeBinary, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.image import Image


# CLIP ViT-B/32 produces 512-dimensional embeddings
EMBEDDING_DIMENSION = 512


class ImageEmbedding(Base):
    """
    Vector embeddings and perceptual features for an image.
    
    Stores:
    - CLIP/ViT embedding vector (for semantic similarity)
    - pHash (perceptual hash for visual similarity)
    - ORB descriptors (keypoints for geometric matching)
    
    Uses JSON-serialized vectors for SQLite compatibility.
    """
    __tablename__ = "image_embeddings"
    
    # Primary key (using String for SQLite UUID compatibility)
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True
    )
    
    # Parent image reference (one-to-one)
    image_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("images.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    
    # ===========================================
    # CLIP/ViT Embedding
    # ===========================================
    # 512-dimensional vector from CLIP ViT-B/32
    # Stored as JSON string for SQLite compatibility
    embedding_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="CLIP embedding vector as JSON array"
    )
    
    # ===========================================
    # Perceptual Hash (pHash)
    # ===========================================
    # 64-bit perceptual hash as hex string
    # Used for near-duplicate detection
    phash: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        index=True,
        comment="Perceptual hash (64-bit hex) for visual similarity"
    )
    
    # Additional hash types for robustness
    dhash: Mapped[Optional[str]] = mapped_column(
        String(16),
        nullable=True,
        comment="Difference hash"
    )
    ahash: Mapped[Optional[str]] = mapped_column(
        String(16),
        nullable=True,
        comment="Average hash"
    )
    
    # ===========================================
    # ORB Descriptors
    # ===========================================
    # Serialized ORB keypoints and descriptors
    # Used for geometric/structural matching
    orb_keypoints_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Number of ORB keypoints detected"
    )
    orb_descriptors: Mapped[Optional[bytes]] = mapped_column(
        LargeBinary,
        nullable=True,
        comment="Serialized ORB descriptors (numpy array as bytes)"
    )
    orb_keypoints: Mapped[Optional[bytes]] = mapped_column(
        LargeBinary,
        nullable=True,
        comment="Serialized ORB keypoint coordinates"
    )
    
    # ===========================================
    # YOLO Detection Info
    # ===========================================
    detected_class: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Primary object class detected by YOLO"
    )
    detection_confidence: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        comment="YOLO detection confidence score"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    
    # Relationship
    image: Mapped["Image"] = relationship("Image", back_populates="embedding")
    
    def __repr__(self) -> str:
        return f"<ImageEmbedding image_id={self.image_id}>"


# Import Float for detection_confidence
from sqlalchemy import Float
