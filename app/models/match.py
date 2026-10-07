"""
Match model for tracking potential matches between lost and found items.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Float, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.item import Item


class MatchStatus(str, Enum):
    """Status of a potential match between items."""
    PENDING = "pending"                 # Match found, awaiting review
    SOURCE_CONFIRMED = "source_confirmed"   # Source item owner confirmed
    TARGET_CONFIRMED = "target_confirmed"   # Target item owner confirmed
    BOTH_CONFIRMED = "both_confirmed"       # Both parties confirmed - reveal contact
    REJECTED = "rejected"               # One party rejected the match
    EXPIRED = "expired"                 # Match expired without action


class Match(Base):
    """
    Potential match between a lost item and a found item.
    
    Stores:
    - References to both items
    - Similarity scores from the matching pipeline
    - Confirmation status from both parties
    
    Contact information is only revealed when both parties confirm.
    """
    __tablename__ = "matches"
    
    # Primary key - UUID as string for SQLite
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True
    )
    
    # ===========================================
    # Item References
    # ===========================================
    # Source item (the one that initiated the search)
    source_item_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Target item (found in the search results)
    target_item_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # ===========================================
    # Similarity Scores
    # ===========================================
    # Overall combined score (0-1, higher is better)
    overall_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        index=True
    )
    
    # Individual component scores
    vector_similarity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Cosine similarity of CLIP embeddings (0-1)"
    )
    phash_similarity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="pHash similarity score (0-1, based on hamming distance)"
    )
    orb_match_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="ORB keypoint match score (0-1)"
    )
    # Detailed score breakdown (for debugging/transparency, stored as JSON string)
    score_details_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed breakdown of scoring factors as JSON"
    )
    
    # ===========================================
    # Match Status
    # ===========================================
    status: Mapped[str] = mapped_column(
        String(20),
        default=MatchStatus.PENDING.value,
        index=True
    )
    
    # Confirmation tracking
    source_confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    target_confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    rejected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    rejected_by: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="'source' or 'target'"
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    
    # ===========================================
    # Timestamps
    # ===========================================
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # ===========================================
    # Relationships
    # ===========================================
    source_item: Mapped["Item"] = relationship(
        "Item",
        foreign_keys=[source_item_id],
        back_populates="matches_as_source"
    )
    target_item: Mapped["Item"] = relationship(
        "Item",
        foreign_keys=[target_item_id],
        back_populates="matches_as_target"
    )
    
    def __repr__(self) -> str:
        return f"<Match {self.source_item_id} -> {self.target_item_id} ({self.overall_score:.2f})>"
