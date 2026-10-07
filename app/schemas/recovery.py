"""Schemas for secure ownership verification and recovery cases."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class OwnershipChallengeUpsert(BaseModel):
    question: str = Field(..., min_length=5, max_length=500)
    private_details: str = Field(..., min_length=3, max_length=2000)


class OwnershipChallengeResponse(BaseModel):
    id: str
    found_item_id: str
    question: str
    has_private_details: bool = True
    created_at: datetime
    updated_at: datetime


class RecoveryProofSubmit(BaseModel):
    answer: str = Field(..., min_length=10, max_length=3000)


class RecoveryReview(BaseModel):
    approved: bool
    note: Optional[str] = Field(None, max_length=1000)


class RecoveryMessageCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=2000)


class RecoveryMessageResponse(BaseModel):
    id: str
    recovery_request_id: str
    sender_user_id: str
    sender_role: Literal["claimant", "finder"]
    body: str
    created_at: datetime


class RecoveryRequestResponse(BaseModel):
    id: str
    reference_code: str
    match_id: str
    lost_item_id: str
    found_item_id: str
    claimant_user_id: str
    finder_user_id: str
    current_user_role: Literal["claimant", "finder"]
    status: str
    challenge_question: str
    private_reference_details: Optional[str] = None
    proof_answer: Optional[str] = None
    reviewer_note: Optional[str] = None
    claimant_confirmed_delivery: bool
    finder_confirmed_delivery: bool
    proof_submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    delivery_arranged_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
