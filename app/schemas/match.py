"""
Pydantic schemas for Match-related API operations.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, ConfigDict

from app.models.match import MatchStatus
from app.schemas.item import ItemResponse
from app.schemas.user import UserContactInfo


class MatchScores(BaseModel):
    """Detailed breakdown of match scores."""
    vector_similarity: float = Field(..., ge=0, le=1, description="CLIP embedding similarity")
    phash_similarity: float = Field(..., ge=0, le=1, description="Perceptual hash similarity")
    orb_match_score: float = Field(..., ge=0, le=1, description="ORB keypoint match score")
    overall_score: float = Field(..., ge=0, le=1, description="Combined weighted score")


class MatchResponse(BaseModel):
    """Schema for match response."""
    id: str
    source_item_id: str
    target_item_id: str
    status: str
    
    # Scores
    overall_score: float
    vector_similarity: float
    phash_similarity: float
    orb_match_score: float
    score_details: Optional[Dict[str, Any]] = None
    
    # Status timestamps
    created_at: datetime
    updated_at: datetime
    source_confirmed_at: Optional[datetime] = None
    target_confirmed_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    rejected_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    
    # Related items (populated when needed)
    source_item: Optional[ItemResponse] = None
    target_item: Optional[ItemResponse] = None
    
    # Contact info (only revealed when both confirmed)
    contact_info: Optional[UserContactInfo] = None
    
    model_config = ConfigDict(from_attributes=True)


class MatchListResponse(BaseModel):
    """Schema for list of matches from search."""
    matches: List[MatchResponse]
    total: int
    search_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters used for the search"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "matches": [],
                "total": 10,
                "search_params": {
                    "item_type": "phone",
                    "time_range_days": 30
                }
            }
        }
    )


class MatchConfirmRequest(BaseModel):
    """Schema for confirming a match."""
    confirmed: bool = Field(..., description="True to confirm, False to reject")
    rejection_reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Reason for rejection (if confirmed=False)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "confirmed": True,
                "rejection_reason": None
            }
        }
    )


class MatchSearchParams(BaseModel):
    """Schema for match search parameters."""
    time_range_days: Optional[int] = Field(
        None,
        ge=1,
        le=365,
        description="Time range in days"
    )
    min_score: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Minimum overall score threshold"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "time_range_days": 30,
                "min_score": 0.5
            }
        }
    )
