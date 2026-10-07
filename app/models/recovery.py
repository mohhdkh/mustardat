"""Secure ownership verification and recovery workflow models."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class RecoveryStatus(str, Enum):
    AWAITING_PROOF = "awaiting_proof"
    PROOF_SUBMITTED = "proof_submitted"
    OWNERSHIP_VERIFIED = "ownership_verified"
    DELIVERY_ARRANGED = "delivery_arranged"
    DELIVERED = "delivered"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class OwnershipChallenge(Base):
    """A public question and encrypted private reference details for a found item."""

    __tablename__ = "ownership_challenges"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    found_item_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    private_details_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RecoveryRequest(Base):
    """A controlled recovery case between the lost-item and found-item owners."""

    __tablename__ = "recovery_requests"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    reference_code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    match_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("matches.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    challenge_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ownership_challenges.id", ondelete="CASCADE"),
        nullable=False,
    )
    lost_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("items.id", ondelete="CASCADE"), nullable=False
    )
    found_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("items.id", ondelete="CASCADE"), nullable=False
    )
    claimant_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    finder_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(30), default=RecoveryStatus.AWAITING_PROOF.value, nullable=False, index=True
    )
    proof_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewer_note_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    claimant_confirmed_delivery: Mapped[bool] = mapped_column(Boolean, default=False)
    finder_confirmed_delivery: Mapped[bool] = mapped_column(Boolean, default=False)
    proof_submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    delivery_arranged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    claimant_confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finder_confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RecoveryMessage(Base):
    """An encrypted message exchanged inside an approved recovery case."""

    __tablename__ = "recovery_messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    recovery_request_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("recovery_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    body_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
