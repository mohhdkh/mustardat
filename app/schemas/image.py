"""
Pydantic schemas for Image-related API operations.
"""

from datetime import datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field, ConfigDict


class ImageResponse(BaseModel):
    """Schema for image response."""
    id: str
    item_id: str
    original_filename: str
    file_path_original: str
    file_path_processed: Optional[str] = None
    file_path_thumbnail: Optional[str] = None
    content_type: str
    file_size: int
    width: Optional[int] = None
    height: Optional[int] = None
    exif_data_json: Optional[str] = None
    exif_latitude: Optional[float] = None
    exif_longitude: Optional[float] = None
    exif_datetime: Optional[datetime] = None
    is_processed: bool
    processing_error: Optional[str] = None
    display_order: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ImageUploadResponse(BaseModel):
    """Schema for image upload response."""
    id: str
    original_filename: str
    s3_key_original: str  # Keep name for API compatibility
    file_size: int
    content_type: str
    is_processed: bool
    message: str = "Image uploaded successfully. Processing will begin shortly."


class ImageProcessingStatus(BaseModel):
    """Schema for image processing status."""
    image_id: str
    is_processed: bool
    has_embedding: bool
    detected_class: Optional[str] = None
    detection_confidence: Optional[float] = None
    processing_error: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class EmbeddingInfo(BaseModel):
    """Schema for embedding information (debug/admin use)."""
    image_id: str
    phash: str
    orb_keypoints_count: int
    detected_class: Optional[str] = None
    detection_confidence: Optional[float] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
