"""
Item management routes for lost and found items.
"""

import json
import uuid
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.models.user import User
from app.models.item import Item, ItemType, ItemStatus
from app.models.image import Image
from app.models.embedding import ImageEmbedding
from app.models.match import Match
from app.schemas.item import ItemCreate, ItemUpdate, ItemResponse, ItemListResponse
from app.schemas.image import ImageUploadResponse, ImageResponse
from app.schemas.match import MatchListResponse, MatchResponse
from app.services.storage import storage_service, StorageError
from app.services.matching import matching_engine
from app.api.deps import get_current_user, require_owner
from app.config import settings


router = APIRouter(prefix="/items", tags=["Items"])


@router.post(
    "",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create lost/found item",
    description="Create a new lost or found item listing."
)
async def create_item(
    item_data: ItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ItemResponse:
    """
    Create a new lost or found item.
    """
    item = Item(
        user_id=current_user.id,
        item_type=item_data.item_type.value if hasattr(item_data.item_type, 'value') else item_data.item_type,
        lost_or_found=item_data.lost_or_found,
        title=item_data.title,
        description=item_data.description,
        location_name=item_data.location_name,
        event_date=item_data.event_date,
        status=ItemStatus.ACTIVE.value
    )
    
    db.add(item)
    await db.commit()
    await db.refresh(item, ["images"])  # Eagerly load images relationship
    
    return ItemResponse.model_validate(item)


@router.get(
    "",
    response_model=ItemListResponse,
    summary="List items",
    description="List items with optional filters."
)
async def list_items(
    item_type: Optional[str] = Query(None, description="Filter by item type"),
    lost_or_found: Optional[str] = Query(None, description="Filter by lost or found"),
    item_status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ItemListResponse:
    """
    List items belonging to the current user.
    """
    # Build query
    query = select(Item).where(Item.user_id == current_user.id)
    
    if item_type:
        query = query.where(Item.item_type == item_type)
    if lost_or_found:
        query = query.where(Item.lost_or_found == lost_or_found)
    if item_status:
        query = query.where(Item.status == item_status)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0
    
    # Apply pagination
    query = query.options(selectinload(Item.images))
    query = query.order_by(Item.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    # Debug: print item images info
    for item in items:
        print(f"Item {item.id} has {len(item.images)} images")
        for img in item.images:
            print(f"  Image {img.id}: original={img.file_path_original}, thumbnail={img.file_path_thumbnail}")
    
    return ItemListResponse(
        items=[ItemResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 0
    )


@router.get(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Get item",
    description="Get a specific item by ID."
)
async def get_item(
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ItemResponse:
    """
    Get a specific item by ID.
    """
    result = await db.execute(
        select(Item)
        .options(selectinload(Item.images))
        .where(Item.id == item_id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    require_owner(item.user_id, current_user)
    
    return ItemResponse.model_validate(item)


@router.patch(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Update item",
    description="Update an existing item."
)
async def update_item(
    item_id: str,
    item_data: ItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ItemResponse:
    """
    Update an existing item.
    """
    result = await db.execute(
        select(Item)
        .options(selectinload(Item.images))
        .where(Item.id == item_id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    require_owner(item.user_id, current_user)
    
    # Update fields
    update_data = item_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == 'status' and hasattr(value, 'value'):
            value = value.value
        setattr(item, field, value)
    
    await db.commit()
    # Refresh scalar columns (including the server-managed updated_at value)
    # before loading the relationship used by the response schema.
    await db.refresh(item)
    await db.refresh(item, ["images"])
    
    return ItemResponse.model_validate(item)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete item",
    description="Delete an item and all its images."
)
async def delete_item(
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Delete an item and all associated images.
    """
    result = await db.execute(
        select(Item)
        .options(selectinload(Item.images))
        .where(Item.id == item_id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    require_owner(item.user_id, current_user)
    
    # Delete the known objects before cascading the database rows.
    try:
        image_paths = [
            path
            for image in item.images
            for path in (
                image.file_path_original,
                image.file_path_processed,
                image.file_path_thumbnail,
            )
            if path
        ]
        if storage_service.is_remote:
            await storage_service.delete_images(image_paths)
        else:
            await storage_service.delete_item_images(item_id)
    except StorageError as e:
        print(f"Warning: Failed to delete images: {e}")
    
    await db.delete(item)
    await db.commit()


# ===========================================
# Image Upload Routes
# ===========================================

@router.post(
    "/{item_id}/images",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload image",
    description="Upload an image for an item (max 6 images per item)."
)
async def upload_image(
    item_id: str,
    file: UploadFile = File(..., description="Image file (JPEG, PNG, WebP)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ImageUploadResponse:
    """
    Upload an image for an item.
    """
    # Get item
    result = await db.execute(
        select(Item)
        .options(selectinload(Item.images))
        .where(Item.id == item_id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    require_owner(item.user_id, current_user)
    
    # Check image count limit
    if len(item.images) >= 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 6 images per item"
        )
    
    # Validate content type
    if file.content_type not in settings.allowed_image_types_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {settings.allowed_image_types}"
        )
    
    # Read file content
    content = await file.read()
    
    # Check file size
    if len(content) > settings.max_image_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.max_image_size_mb}MB"
        )
    
    # Generate image ID
    image_id = str(uuid.uuid4())
    
    # Upload to local storage
    try:
        import io
        file_path = await storage_service.upload_image(
            io.BytesIO(content),
            item_id,
            image_id,
            file.content_type,
            "original"
        )
    except StorageError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {e}"
        )
    
    # Create image record
    image = Image(
        id=image_id,
        item_id=item_id,
        original_filename=file.filename or "unknown",
        file_path_original=file_path,
        content_type=file.content_type,
        file_size=len(content),
        display_order=len(item.images) + 1,
        is_processed=False
    )
    
    db.add(image)
    await db.commit()
    await db.refresh(image)
    
    # Process image
    try:
        # Import the heavyweight ML pipeline only when an image is uploaded.
        # This keeps the API and frontend usable without loading PyTorch at startup.
        from app.services.image_processing import image_processor

        processing_result = await image_processor.process_image(content)
        
        # Upload processed image and thumbnail
        file_path_processed = await storage_service.upload_bytes(
            processing_result.processed_image,
            item_id,
            image_id,
            "image/jpeg",
            "processed"
        )
        
        file_path_thumbnail = await storage_service.upload_bytes(
            processing_result.thumbnail,
            item_id,
            image_id,
            "image/jpeg",
            "thumbnail"
        )
        
        # Update image record
        image.file_path_processed = file_path_processed
        image.file_path_thumbnail = file_path_thumbnail
        image.width = processing_result.width
        image.height = processing_result.height
        image.exif_data_json = json.dumps(processing_result.exif_data) if processing_result.exif_data else None
        image.is_processed = True
        
        # Extract GPS from EXIF if available
        if processing_result.exif_data and 'gps' in processing_result.exif_data:
            gps = processing_result.exif_data['gps']
            image.exif_latitude = gps.get('latitude')
            image.exif_longitude = gps.get('longitude')
        
        # Create embedding record
        embedding = ImageEmbedding(
            image_id=image_id,
            embedding_json=json.dumps(processing_result.embedding.tolist()),
            phash=processing_result.phash,
            dhash=processing_result.dhash,
            ahash=processing_result.ahash,
            orb_descriptors=processing_result.orb_descriptors,
            orb_keypoints=processing_result.orb_keypoints,
            orb_keypoints_count=processing_result.orb_keypoints_count,
            detected_class=processing_result.detected_class,
            detection_confidence=processing_result.detection_confidence
        )
        
        db.add(embedding)
        await db.commit()
        
    except Exception as e:
        # Mark as failed but don't fail the upload
        image.processing_error = str(e)
        await db.commit()
        print(f"Image processing error: {e}")
    
    return ImageUploadResponse(
        id=image.id,
        original_filename=image.original_filename,
        s3_key_original=image.file_path_original,
        file_size=image.file_size,
        content_type=image.content_type,
        is_processed=image.is_processed,
        message="Image uploaded successfully. Processing complete." if image.is_processed 
                else "Image uploaded. Processing failed - please try again."
    )


@router.get(
    "/{item_id}/images",
    response_model=List[ImageResponse],
    summary="List item images",
    description="Get all images for an item."
)
async def list_item_images(
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[ImageResponse]:
    """
    Get all images for an item.
    """
    result = await db.execute(
        select(Item).where(Item.id == item_id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    require_owner(item.user_id, current_user)
    
    result = await db.execute(
        select(Image)
        .where(Image.item_id == item_id)
        .order_by(Image.display_order)
    )
    images = result.scalars().all()
    
    return [ImageResponse.model_validate(img) for img in images]


@router.delete(
    "/{item_id}/images/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete image",
    description="Delete a specific image from an item."
)
async def delete_image(
    item_id: str,
    image_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Delete a specific image from an item.
    """
    result = await db.execute(
        select(Item).where(Item.id == item_id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    require_owner(item.user_id, current_user)
    
    result = await db.execute(
        select(Image).where(
            Image.id == image_id,
            Image.item_id == item_id
        )
    )
    image = result.scalar_one_or_none()
    
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    # Delete from local storage
    try:
        if image.file_path_original:
            await storage_service.delete_image(image.file_path_original)
        if image.file_path_processed:
            await storage_service.delete_image(image.file_path_processed)
        if image.file_path_thumbnail:
            await storage_service.delete_image(image.file_path_thumbnail)
    except StorageError as e:
        print(f"Warning: Failed to delete images: {e}")
    
    await db.delete(image)
    await db.commit()


# ===========================================
# Matching Routes
# ===========================================

@router.get(
    "/{item_id}/matches",
    response_model=MatchListResponse,
    summary="Find matches",
    description="Run the matching pipeline to find potential matches for an item."
)
async def find_matches(
    item_id: str,
    time_range_days: Optional[int] = Query(None, ge=1, le=365, description="Time range in days"),
    min_score: Optional[float] = Query(None, ge=0, le=1, description="Minimum match score"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MatchListResponse:
    """
    Find potential matches for an item.
    """
    # Verify item exists and belongs to user
    result = await db.execute(
        select(Item).where(Item.id == item_id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    require_owner(item.user_id, current_user)
    
    # Check if item has processed images
    result = await db.execute(
        select(Image)
        .options(selectinload(Image.embedding))
        .where(Image.item_id == item_id, Image.is_processed == True)
    )
    images = result.scalars().all()
    
    if not images:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item has no processed images. Please upload and wait for processing."
        )
    
    has_embeddings = any(img.embedding for img in images)
    if not has_embeddings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image embeddings not ready. Please wait for processing to complete."
        )
    
    # Run matching pipeline
    try:
        match_results = await matching_engine.find_matches(
            db=db,
            source_item_id=item_id,
            time_range_days=time_range_days,
            min_score=min_score
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Create match records in database (skips existing ones)
    new_matches = await matching_engine.create_matches(db, item_id, match_results)
    
    # Get all matches involving this item, regardless of which side originally
    # started the search.
    all_matches_result = await db.execute(
        select(Match)
        .where(
            or_(
                Match.source_item_id == item_id,
                Match.target_item_id == item_id,
            )
        )
        .order_by(Match.overall_score.desc())
    )
    matches = all_matches_result.scalars().all()
    
    # Build response
    match_responses = []
    for match in matches:
        source_result = await db.execute(
            select(Item)
            .options(selectinload(Item.images))
            .where(Item.id == match.source_item_id)
        )
        source_item = source_result.scalar_one_or_none()

        target_result = await db.execute(
            select(Item)
            .options(selectinload(Item.images))
            .where(Item.id == match.target_item_id)
        )
        target_item = target_result.scalar_one_or_none()
        
        response = MatchResponse(
            id=match.id,
            source_item_id=match.source_item_id,
            target_item_id=match.target_item_id,
            status=match.status,
            overall_score=match.overall_score,
            vector_similarity=match.vector_similarity,
            phash_similarity=match.phash_similarity,
            orb_match_score=match.orb_match_score,
            score_details=json.loads(match.score_details_json) if match.score_details_json else None,
            created_at=match.created_at,
            updated_at=match.updated_at,
            source_item=ItemResponse.model_validate(source_item) if source_item else None,
            target_item=ItemResponse.model_validate(target_item) if target_item else None
        )
        match_responses.append(response)
    
    return MatchListResponse(
        matches=match_responses,
        total=len(match_responses),
        search_params={
            "time_range_days": (
                settings.default_time_range_days
                if time_range_days is None
                else time_range_days
            ),
            "min_score": (
                settings.vector_similarity_threshold
                if min_score is None
                else min_score
            )
        }
    )
