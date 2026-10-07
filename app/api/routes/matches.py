"""
Match management routes for confirming/rejecting matches.
"""

import json
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, or_, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.models.user import User
from app.models.item import Item, ItemStatus
from app.models.match import Match, MatchStatus
from app.schemas.match import MatchResponse, MatchConfirmRequest
from app.schemas.item import ItemResponse
from app.schemas.user import UserContactInfo
from app.services.notification import notification_service
from app.api.deps import get_current_user


router = APIRouter(prefix="/matches", tags=["Matches"])


@router.get(
    "",
    response_model=List[MatchResponse],
    summary="List matches",
    description="List all matches for the current user's items."
)
async def list_matches(
    status_filter: Optional[MatchStatus] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[MatchResponse]:
    """
    List all matches involving the current user's items.
    
    Returns matches where the user is either the source or target item owner.
    """
    try:
        # Get user's item IDs
        items_result = await db.execute(
            select(Item.id).where(Item.user_id == current_user.id)
        )
        user_item_ids = [row[0] for row in items_result.fetchall()]
        
        if not user_item_ids:
            print(f"No items found for user {current_user.id}")
            return []
        
        # Query matches involving user's items
        query = select(Match).where(
            or_(
                Match.source_item_id.in_(user_item_ids),
                Match.target_item_id.in_(user_item_ids)
            )
        )
        
        if status_filter:
            query = query.where(Match.status == status_filter)
        
        query = query.order_by(Match.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await db.execute(query)
        matches = result.scalars().all()
        
        print(f"Found {len(matches)} matches for user {current_user.id}")
        
        # If no matches, return empty list immediately
        if not matches:
            return []
        
        # Build responses with related items
        responses = []
        for match in matches:
            try:
                # Load source and target items
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
                
                # Check if contact should be revealed
                contact_info = None
                if match.status == MatchStatus.BOTH_CONFIRMED.value:
                    # Determine which user's contact to show
                    if source_item and source_item.user_id == current_user.id:
                        # Current user owns source, show target owner's contact
                        other_user_result = await db.execute(
                            select(User).where(User.id == target_item.user_id)
                        )
                        other_user = other_user_result.scalar_one_or_none()
                    else:
                        # Current user owns target, show source owner's contact
                        other_user_result = await db.execute(
                            select(User).where(User.id == source_item.user_id)
                        )
                        other_user = other_user_result.scalar_one_or_none()
                    
                    if other_user:
                        contact_info = UserContactInfo(
                            full_name=other_user.full_name,
                            email=other_user.email,
                            phone_number=other_user.phone_number
                        )
                
                # Never expose personal contact details from match endpoints.
                contact_info = None
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
                    source_confirmed_at=match.source_confirmed_at,
                    target_confirmed_at=match.target_confirmed_at,
                    rejected_at=match.rejected_at,
                    rejected_by=match.rejected_by,
                    rejection_reason=match.rejection_reason,
                    source_item=ItemResponse.model_validate(source_item) if source_item else None,
                    target_item=ItemResponse.model_validate(target_item) if target_item else None,
                    contact_info=contact_info
                )
                responses.append(response)
            except Exception as e:
                print(f"Error processing match {match.id}: {e}")
                continue
        
        return responses
    except Exception as e:
        print(f"Error in list_matches: {e}")
        return []


@router.get(
    "/{match_id}",
    response_model=MatchResponse,
    summary="Get match",
    description="Get details of a specific match."
)
async def get_match(
    match_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MatchResponse:
    """
    Get details of a specific match.
    
    Only accessible to owners of either the source or target item.
    """
    result = await db.execute(
        select(Match).where(Match.id == match_id)
    )
    match = result.scalar_one_or_none()
    
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )
    
    # Verify user owns one of the items
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
    
    user_owns_source = source_item and source_item.user_id == current_user.id
    user_owns_target = target_item and target_item.user_id == current_user.id
    
    if not (user_owns_source or user_owns_target):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this match"
        )
    
    # Check if contact should be revealed
    contact_info = None
    if match.status == MatchStatus.BOTH_CONFIRMED.value:
        if user_owns_source:
            other_user_result = await db.execute(
                select(User).where(User.id == target_item.user_id)
            )
        else:
            other_user_result = await db.execute(
                select(User).where(User.id == source_item.user_id)
            )
        other_user = other_user_result.scalar_one_or_none()
        
        if other_user:
            contact_info = UserContactInfo(
                full_name=other_user.full_name,
                email=other_user.email,
                phone_number=other_user.phone_number
            )
    
    # Approved recoveries communicate through the encrypted in-app chat.
    contact_info = None
    return MatchResponse(
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
        source_confirmed_at=match.source_confirmed_at,
        target_confirmed_at=match.target_confirmed_at,
        rejected_at=match.rejected_at,
        rejected_by=match.rejected_by,
        rejection_reason=match.rejection_reason,
        source_item=ItemResponse.model_validate(source_item) if source_item else None,
        target_item=ItemResponse.model_validate(target_item) if target_item else None,
        contact_info=contact_info
    )


@router.post(
    "/{match_id}/confirm",
    response_model=MatchResponse,
    summary="Confirm match",
    description="Reject a potential match. Direct confirmation is disabled in favor of ownership verification."
)
async def confirm_match(
    match_id: str,
    request: MatchConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MatchResponse:
    """
    Legacy endpoint retained for rejection compatibility.

    Positive confirmation now requires the secure recovery workflow and never
    reveals personal contact details.
    """
    if request.confirmed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Direct confirmation is disabled. Start the secure ownership "
                "verification process instead."
            ),
        )
    result = await db.execute(
        select(Match).where(Match.id == match_id)
    )
    match = result.scalar_one_or_none()
    
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )
    
    # Check if already resolved
    if match.status in [MatchStatus.BOTH_CONFIRMED.value, MatchStatus.REJECTED.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Match already {match.status}"
        )
    
    # Get items to verify ownership
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
    
    user_owns_source = source_item and source_item.user_id == current_user.id
    user_owns_target = target_item and target_item.user_id == current_user.id
    
    if not (user_owns_source or user_owns_target):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to confirm this match"
        )
    
    now = datetime.utcnow()
    
    if request.confirmed:
        # Handle confirmation
        if user_owns_source:
            match.source_confirmed_at = now
            if match.status == MatchStatus.TARGET_CONFIRMED.value:
                match.status = MatchStatus.BOTH_CONFIRMED.value
            else:
                match.status = MatchStatus.SOURCE_CONFIRMED.value
        else:
            match.target_confirmed_at = now
            if match.status == MatchStatus.SOURCE_CONFIRMED.value:
                match.status = MatchStatus.BOTH_CONFIRMED.value
            else:
                match.status = MatchStatus.TARGET_CONFIRMED.value
        
        # If both confirmed, update item statuses and notify
        if match.status == MatchStatus.BOTH_CONFIRMED.value:
            source_item.status = ItemStatus.MATCHED
            target_item.status = ItemStatus.MATCHED
            
            # Get both users for notification
            source_user_result = await db.execute(
                select(User).where(User.id == source_item.user_id)
            )
            source_user = source_user_result.scalar_one_or_none()
            
            target_user_result = await db.execute(
                select(User).where(User.id == target_item.user_id)
            )
            target_user = target_user_result.scalar_one_or_none()
            
            # Notify both users
            if source_user and target_user:
                await notification_service.notify_contact_revealed(
                    db, source_user, target_user, match
                )
                await notification_service.notify_contact_revealed(
                    db, target_user, source_user, match
                )
        else:
            # Notify the other party
            if user_owns_source and target_item:
                other_user_result = await db.execute(
                    select(User).where(User.id == target_item.user_id)
                )
                other_user = other_user_result.scalar_one_or_none()
                if other_user:
                    await notification_service.notify_match_confirmed(
                        db, other_user, match, current_user.full_name or "Someone"
                    )
            elif source_item:
                other_user_result = await db.execute(
                    select(User).where(User.id == source_item.user_id)
                )
                other_user = other_user_result.scalar_one_or_none()
                if other_user:
                    await notification_service.notify_match_confirmed(
                        db, other_user, match, current_user.full_name or "Someone"
                    )
    else:
        # Handle rejection
        match.status = MatchStatus.REJECTED.value
        match.rejected_at = now
        match.rejected_by = "source" if user_owns_source else "target"
        match.rejection_reason = request.rejection_reason
    
    await db.commit()
    await db.refresh(match)
    
    # Re-fetch items with images to avoid lazy loading issues after commit
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
    
    # Build response
    contact_info = None
    if match.status == MatchStatus.BOTH_CONFIRMED.value:
        if user_owns_source:
            other_user_result = await db.execute(
                select(User).where(User.id == target_item.user_id)
            )
        else:
            other_user_result = await db.execute(
                select(User).where(User.id == source_item.user_id)
            )
        other_user = other_user_result.scalar_one_or_none()
        
        if other_user:
            contact_info = UserContactInfo(
                full_name=other_user.full_name,
                email=other_user.email,
                phone_number=other_user.phone_number
            )
    
    contact_info = None
    return MatchResponse(
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
        source_confirmed_at=match.source_confirmed_at,
        target_confirmed_at=match.target_confirmed_at,
        rejected_at=match.rejected_at,
        rejected_by=match.rejected_by,
        rejection_reason=match.rejection_reason,
        source_item=ItemResponse.model_validate(source_item) if source_item else None,
        target_item=ItemResponse.model_validate(target_item) if target_item else None,
        contact_info=contact_info
    )


@router.post(
    "/{match_id}/reject",
    response_model=MatchResponse,
    summary="Reject match",
    description="Reject a potential match (shortcut for confirm with confirmed=False)."
)
async def reject_match(
    match_id: str,
    rejection_reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MatchResponse:
    """
    Reject a potential match.
    
    This is a convenience endpoint equivalent to POST /confirm with confirmed=False.
    """
    return await confirm_match(
        match_id=match_id,
        request=MatchConfirmRequest(confirmed=False, rejection_reason=rejection_reason),
        current_user=current_user,
        db=db
    )
