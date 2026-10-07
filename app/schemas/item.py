"""
Pydantic schemas for Item-related API operations.
"""

from datetime import datetime
from typing import Optional, List, Literal

from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.models.item import ItemType, ItemStatus


class ItemCreate(BaseModel):
    """Schema for creating a new lost/found item."""
    item_type: ItemType = Field(..., description="Category of the item")
    lost_or_found: Literal["lost", "found"] = Field(
        ...,
        description="Whether item was lost or found"
    )
    title: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Brief title for the item"
    )
    description: Optional[str] = Field(
        None,
        max_length=2000,
        description="Detailed description of the item"
    )
    location_name: Optional[str] = Field(None, max_length=255)
    event_date: datetime = Field(
        ...,
        description="Date/time when item was lost or found"
    )
    
    @field_validator("lost_or_found")
    @classmethod
    def validate_lost_or_found(cls, v: str) -> str:
        if v not in ("lost", "found"):
            raise ValueError("Must be 'lost' or 'found'")
        return v
    
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "item_type": "phone",
                "lost_or_found": "lost",
                "title": "Black iPhone 14 Pro",
                "description": "Lost my iPhone 14 Pro with a black case. Has a small scratch on the screen.",
                "location_name": "Central Park, New York",
                "event_date": "2024-01-15T14:30:00Z"
            }
        }
    )


class ItemUpdate(BaseModel):
    """Schema for updating an existing item."""
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    location_name: Optional[str] = Field(None, max_length=255)
    event_date: Optional[datetime] = None
    status: Optional[ItemStatus] = None


class ImageSummary(BaseModel):
    """Brief image info for item response."""
    id: str
    file_path_original: Optional[str] = None
    file_path_thumbnail: Optional[str] = None
    file_path_processed: Optional[str] = None
    display_order: int
    is_processed: bool
    
    model_config = ConfigDict(from_attributes=True)


class ItemResponse(BaseModel):
    """Schema for item response."""
    id: str
    user_id: str
    item_type: str
    lost_or_found: str
    status: str
    title: str
    description: Optional[str] = None
    location_name: Optional[str] = None
    event_date: datetime
    created_at: datetime
    updated_at: datetime
    images: List[ImageSummary] = []
    
    model_config = ConfigDict(from_attributes=True)


class ItemListResponse(BaseModel):
    """Schema for paginated item list response."""
    items: List[ItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [],
                "total": 100,
                "page": 1,
                "page_size": 20,
                "total_pages": 5
            }
        }
    )
