"""Secure ownership verification and recovery workflow routes."""

import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.item import Item, ItemStatus
from app.models.match import Match
from app.models.notification import Notification, NotificationType
from app.models.recovery import (
    OwnershipChallenge,
    RecoveryMessage,
    RecoveryRequest,
    RecoveryStatus,
)
from app.models.user import User
from app.schemas.recovery import (
    OwnershipChallengeResponse,
    OwnershipChallengeUpsert,
    RecoveryMessageCreate,
    RecoveryMessageResponse,
    RecoveryProofSubmit,
    RecoveryRequestResponse,
    RecoveryReview,
)
from app.services.sensitive_data import sensitive_data_service


router = APIRouter(tags=["Recovery"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _reference_code() -> str:
    return f"MS-{uuid.uuid4().hex[:8].upper()}"


async def _load_match_items(
    db: AsyncSession, match_id: str
) -> tuple[Match, Item, Item]:
    match = (
        await db.execute(select(Match).where(Match.id == match_id))
    ).scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    source = (
        await db.execute(select(Item).where(Item.id == match.source_item_id))
    ).scalar_one_or_none()
    target = (
        await db.execute(select(Item).where(Item.id == match.target_item_id))
    ).scalar_one_or_none()
    if not source or not target:
        raise HTTPException(status_code=404, detail="Matched item not found")
    if {source.lost_or_found, target.lost_or_found} != {"lost", "found"}:
        raise HTTPException(
            status_code=400,
            detail="Recovery requires one lost report and one found report",
        )
    lost_item = source if source.lost_or_found == "lost" else target
    found_item = source if source.lost_or_found == "found" else target
    return match, lost_item, found_item


async def _get_case(
    db: AsyncSession, recovery_id: str, current_user: User
) -> RecoveryRequest:
    recovery = (
        await db.execute(
            select(RecoveryRequest).where(RecoveryRequest.id == recovery_id)
        )
    ).scalar_one_or_none()
    if not recovery:
        raise HTTPException(status_code=404, detail="Recovery request not found")
    if current_user.id not in {
        recovery.claimant_user_id,
        recovery.finder_user_id,
    }:
        raise HTTPException(status_code=403, detail="Not allowed to access this recovery")
    return recovery


async def _challenge_for_case(
    db: AsyncSession, recovery: RecoveryRequest
) -> OwnershipChallenge:
    challenge = (
        await db.execute(
            select(OwnershipChallenge).where(
                OwnershipChallenge.id == recovery.challenge_id
            )
        )
    ).scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Ownership challenge not found")
    return challenge


def _case_response(
    recovery: RecoveryRequest,
    challenge: OwnershipChallenge,
    current_user: User,
) -> RecoveryRequestResponse:
    is_claimant = current_user.id == recovery.claimant_user_id
    can_view_proof = is_claimant or (
        current_user.id == recovery.finder_user_id
        and recovery.status != RecoveryStatus.AWAITING_PROOF.value
    )
    return RecoveryRequestResponse(
        id=recovery.id,
        reference_code=recovery.reference_code,
        match_id=recovery.match_id,
        lost_item_id=recovery.lost_item_id,
        found_item_id=recovery.found_item_id,
        claimant_user_id=recovery.claimant_user_id,
        finder_user_id=recovery.finder_user_id,
        current_user_role="claimant" if is_claimant else "finder",
        status=recovery.status,
        challenge_question=challenge.question,
        private_reference_details=(
            sensitive_data_service.decrypt(challenge.private_details_encrypted)
            if current_user.id == recovery.finder_user_id
            else None
        ),
        proof_answer=(
            sensitive_data_service.decrypt(recovery.proof_encrypted)
            if can_view_proof
            else None
        ),
        reviewer_note=sensitive_data_service.decrypt(
            recovery.reviewer_note_encrypted
        ),
        claimant_confirmed_delivery=recovery.claimant_confirmed_delivery,
        finder_confirmed_delivery=recovery.finder_confirmed_delivery,
        proof_submitted_at=recovery.proof_submitted_at,
        reviewed_at=recovery.reviewed_at,
        delivery_arranged_at=recovery.delivery_arranged_at,
        completed_at=recovery.completed_at,
        created_at=recovery.created_at,
        updated_at=recovery.updated_at,
    )


def _notify(
    db: AsyncSession,
    user_id: str,
    subject: str,
    body: str,
    item_id: str,
    match_id: str,
) -> None:
    db.add(
        Notification(
            user_id=user_id,
            notification_type=NotificationType.SYSTEM.value,
            subject=subject,
            body=body,
            related_item_id=item_id,
            related_match_id=match_id,
        )
    )


@router.put(
    "/items/{item_id}/ownership-challenge",
    response_model=OwnershipChallengeResponse,
)
async def upsert_ownership_challenge(
    item_id: str,
    payload: OwnershipChallengeUpsert,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OwnershipChallengeResponse:
    item = (
        await db.execute(select(Item).where(Item.id == item_id))
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the report owner can set this challenge")
    if item.lost_or_found != "found":
        raise HTTPException(
            status_code=400,
            detail="Ownership challenges can only be added to found-item reports",
        )

    challenge = (
        await db.execute(
            select(OwnershipChallenge).where(
                OwnershipChallenge.found_item_id == item_id
            )
        )
    ).scalar_one_or_none()
    encrypted_details = sensitive_data_service.encrypt(payload.private_details)
    if challenge:
        challenge.question = payload.question
        challenge.private_details_encrypted = encrypted_details
    else:
        challenge = OwnershipChallenge(
            found_item_id=item_id,
            question=payload.question,
            private_details_encrypted=encrypted_details,
        )
        db.add(challenge)
    await db.commit()
    await db.refresh(challenge)
    return OwnershipChallengeResponse(
        id=challenge.id,
        found_item_id=challenge.found_item_id,
        question=challenge.question,
        has_private_details=True,
        created_at=challenge.created_at,
        updated_at=challenge.updated_at,
    )


@router.get(
    "/items/{item_id}/ownership-challenge",
    response_model=OwnershipChallengeResponse,
)
async def get_ownership_challenge(
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OwnershipChallengeResponse:
    item = (
        await db.execute(select(Item).where(Item.id == item_id))
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    challenge = (
        await db.execute(
            select(OwnershipChallenge).where(
                OwnershipChallenge.found_item_id == item_id
            )
        )
    ).scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Ownership challenge not configured")

    if item.user_id != current_user.id:
        user_items = select(Item.id).where(Item.user_id == current_user.id)
        related_match = (
            await db.execute(
                select(Match.id).where(
                    or_(
                        (Match.source_item_id == item_id)
                        & (Match.target_item_id.in_(user_items)),
                        (Match.target_item_id == item_id)
                        & (Match.source_item_id.in_(user_items)),
                    )
                )
            )
        ).first()
        if not related_match:
            raise HTTPException(status_code=403, detail="Not allowed to view this challenge")

    return OwnershipChallengeResponse(
        id=challenge.id,
        found_item_id=challenge.found_item_id,
        question=challenge.question,
        has_private_details=True,
        created_at=challenge.created_at,
        updated_at=challenge.updated_at,
    )


@router.post(
    "/matches/{match_id}/recovery-requests",
    response_model=RecoveryRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_recovery_request(
    match_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecoveryRequestResponse:
    match, lost_item, found_item = await _load_match_items(db, match_id)
    if match.status == "rejected":
        raise HTTPException(status_code=400, detail="Rejected matches cannot be recovered")
    if lost_item.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the owner of the lost-item report can request recovery",
        )
    if lost_item.user_id == found_item.user_id:
        raise HTTPException(
            status_code=400,
            detail="Recovery verification requires two different users",
        )
    existing = (
        await db.execute(
            select(RecoveryRequest).where(RecoveryRequest.match_id == match_id)
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="A recovery request already exists")
    challenge = (
        await db.execute(
            select(OwnershipChallenge).where(
                OwnershipChallenge.found_item_id == found_item.id
            )
        )
    ).scalar_one_or_none()
    if not challenge:
        raise HTTPException(
            status_code=400,
            detail="The finder has not configured an ownership question yet",
        )

    recovery = RecoveryRequest(
        reference_code=_reference_code(),
        match_id=match_id,
        challenge_id=challenge.id,
        lost_item_id=lost_item.id,
        found_item_id=found_item.id,
        claimant_user_id=lost_item.user_id,
        finder_user_id=found_item.user_id,
        status=RecoveryStatus.AWAITING_PROOF.value,
    )
    db.add(recovery)
    _notify(
        db,
        found_item.user_id,
        "طلب إثبات ملكية جديد",
        "وصل طلب استرداد جديد. ستصلك إجابة المالك للمراجعة دون كشف بيانات التواصل.",
        found_item.id,
        match_id,
    )
    await db.commit()
    await db.refresh(recovery)
    return _case_response(recovery, challenge, current_user)


@router.get(
    "/recovery-requests",
    response_model=List[RecoveryRequestResponse],
)
async def list_recovery_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[RecoveryRequestResponse]:
    recoveries = (
        await db.execute(
            select(RecoveryRequest)
            .where(
                or_(
                    RecoveryRequest.claimant_user_id == current_user.id,
                    RecoveryRequest.finder_user_id == current_user.id,
                )
            )
            .order_by(RecoveryRequest.created_at.desc())
        )
    ).scalars().all()
    responses = []
    for recovery in recoveries:
        challenge = await _challenge_for_case(db, recovery)
        responses.append(_case_response(recovery, challenge, current_user))
    return responses


@router.get(
    "/recovery-requests/{recovery_id}",
    response_model=RecoveryRequestResponse,
)
async def get_recovery_request(
    recovery_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecoveryRequestResponse:
    recovery = await _get_case(db, recovery_id, current_user)
    challenge = await _challenge_for_case(db, recovery)
    return _case_response(recovery, challenge, current_user)


@router.post(
    "/recovery-requests/{recovery_id}/proof",
    response_model=RecoveryRequestResponse,
)
async def submit_ownership_proof(
    recovery_id: str,
    payload: RecoveryProofSubmit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecoveryRequestResponse:
    recovery = await _get_case(db, recovery_id, current_user)
    if current_user.id != recovery.claimant_user_id:
        raise HTTPException(status_code=403, detail="Only the claimant can submit proof")
    if recovery.status != RecoveryStatus.AWAITING_PROOF.value:
        raise HTTPException(status_code=400, detail="Proof cannot be submitted in this state")
    recovery.proof_encrypted = sensitive_data_service.encrypt(payload.answer)
    recovery.proof_submitted_at = _now()
    recovery.status = RecoveryStatus.PROOF_SUBMITTED.value
    _notify(
        db,
        recovery.finder_user_id,
        "إثبات الملكية جاهز للمراجعة",
        f"تم إرسال إجابة طلب الاسترداد {recovery.reference_code} للمراجعة.",
        recovery.found_item_id,
        recovery.match_id,
    )
    await db.commit()
    await db.refresh(recovery)
    return _case_response(recovery, await _challenge_for_case(db, recovery), current_user)


@router.post(
    "/recovery-requests/{recovery_id}/review",
    response_model=RecoveryRequestResponse,
)
async def review_ownership_proof(
    recovery_id: str,
    payload: RecoveryReview,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecoveryRequestResponse:
    recovery = await _get_case(db, recovery_id, current_user)
    if current_user.id != recovery.finder_user_id:
        raise HTTPException(status_code=403, detail="Only the finder can review proof")
    if recovery.status != RecoveryStatus.PROOF_SUBMITTED.value:
        raise HTTPException(status_code=400, detail="No submitted proof is awaiting review")
    recovery.reviewer_note_encrypted = (
        sensitive_data_service.encrypt(payload.note) if payload.note else None
    )
    recovery.reviewed_at = _now()
    if payload.approved:
        recovery.status = RecoveryStatus.OWNERSHIP_VERIFIED.value
        lost_item = await db.get(Item, recovery.lost_item_id)
        found_item = await db.get(Item, recovery.found_item_id)
        if lost_item:
            lost_item.status = ItemStatus.MATCHED.value
        if found_item:
            found_item.status = ItemStatus.MATCHED.value
        subject = "تم تأكيد الملكية"
        body = f"تم قبول إثبات الملكية للطلب {recovery.reference_code}. يمكنكما التواصل داخل مستردات."
    else:
        recovery.status = RecoveryStatus.REJECTED.value
        subject = "تعذر تأكيد الملكية"
        body = f"لم يتم قبول إثبات الملكية للطلب {recovery.reference_code}."
    _notify(
        db,
        recovery.claimant_user_id,
        subject,
        body,
        recovery.lost_item_id,
        recovery.match_id,
    )
    await db.commit()
    await db.refresh(recovery)
    return _case_response(recovery, await _challenge_for_case(db, recovery), current_user)


@router.post(
    "/recovery-requests/{recovery_id}/arrange-delivery",
    response_model=RecoveryRequestResponse,
)
async def arrange_delivery(
    recovery_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecoveryRequestResponse:
    recovery = await _get_case(db, recovery_id, current_user)
    if recovery.status not in {
        RecoveryStatus.OWNERSHIP_VERIFIED.value,
        RecoveryStatus.DELIVERY_ARRANGED.value,
    }:
        raise HTTPException(status_code=400, detail="Ownership must be verified first")
    recovery.status = RecoveryStatus.DELIVERY_ARRANGED.value
    recovery.delivery_arranged_at = recovery.delivery_arranged_at or _now()
    await db.commit()
    await db.refresh(recovery)
    return _case_response(recovery, await _challenge_for_case(db, recovery), current_user)


@router.post(
    "/recovery-requests/{recovery_id}/confirm-delivery",
    response_model=RecoveryRequestResponse,
)
async def confirm_delivery(
    recovery_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecoveryRequestResponse:
    recovery = await _get_case(db, recovery_id, current_user)
    if recovery.status not in {
        RecoveryStatus.OWNERSHIP_VERIFIED.value,
        RecoveryStatus.DELIVERY_ARRANGED.value,
    }:
        raise HTTPException(status_code=400, detail="Delivery cannot be confirmed in this state")
    now = _now()
    if current_user.id == recovery.claimant_user_id:
        recovery.claimant_confirmed_delivery = True
        recovery.claimant_confirmed_at = now
    else:
        recovery.finder_confirmed_delivery = True
        recovery.finder_confirmed_at = now

    if recovery.claimant_confirmed_delivery and recovery.finder_confirmed_delivery:
        recovery.status = RecoveryStatus.DELIVERED.value
        recovery.completed_at = now
        lost_item = await db.get(Item, recovery.lost_item_id)
        found_item = await db.get(Item, recovery.found_item_id)
        if lost_item:
            lost_item.status = ItemStatus.RESOLVED.value
        if found_item:
            found_item.status = ItemStatus.RESOLVED.value
        for user_id, item_id in (
            (recovery.claimant_user_id, recovery.lost_item_id),
            (recovery.finder_user_id, recovery.found_item_id),
        ):
            _notify(
                db,
                user_id,
                "تم استرداد الغرض بنجاح 🎉",
                f"اكتمل طلب الاسترداد {recovery.reference_code} بعد تأكيد الطرفين.",
                item_id,
                recovery.match_id,
            )
    await db.commit()
    await db.refresh(recovery)
    return _case_response(recovery, await _challenge_for_case(db, recovery), current_user)


@router.get(
    "/recovery-requests/{recovery_id}/messages",
    response_model=List[RecoveryMessageResponse],
)
async def list_recovery_messages(
    recovery_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[RecoveryMessageResponse]:
    recovery = await _get_case(db, recovery_id, current_user)
    messages = (
        await db.execute(
            select(RecoveryMessage)
            .where(RecoveryMessage.recovery_request_id == recovery.id)
            .order_by(RecoveryMessage.created_at.asc())
        )
    ).scalars().all()
    return [
        RecoveryMessageResponse(
            id=message.id,
            recovery_request_id=recovery.id,
            sender_user_id=message.sender_user_id,
            sender_role=(
                "claimant"
                if message.sender_user_id == recovery.claimant_user_id
                else "finder"
            ),
            body=sensitive_data_service.decrypt(message.body_encrypted) or "",
            created_at=message.created_at,
        )
        for message in messages
    ]


@router.post(
    "/recovery-requests/{recovery_id}/messages",
    response_model=RecoveryMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_recovery_message(
    recovery_id: str,
    payload: RecoveryMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecoveryMessageResponse:
    recovery = await _get_case(db, recovery_id, current_user)
    if recovery.status not in {
        RecoveryStatus.OWNERSHIP_VERIFIED.value,
        RecoveryStatus.DELIVERY_ARRANGED.value,
    }:
        raise HTTPException(status_code=400, detail="Chat opens after ownership is verified")
    message = RecoveryMessage(
        recovery_request_id=recovery.id,
        sender_user_id=current_user.id,
        body_encrypted=sensitive_data_service.encrypt(payload.body),
    )
    db.add(message)
    other_user_id = (
        recovery.finder_user_id
        if current_user.id == recovery.claimant_user_id
        else recovery.claimant_user_id
    )
    _notify(
        db,
        other_user_id,
        "رسالة جديدة في طلب الاسترداد",
        f"لديك رسالة جديدة في الطلب {recovery.reference_code}.",
        recovery.found_item_id,
        recovery.match_id,
    )
    await db.commit()
    await db.refresh(message)
    return RecoveryMessageResponse(
        id=message.id,
        recovery_request_id=recovery.id,
        sender_user_id=message.sender_user_id,
        sender_role=(
            "claimant"
            if message.sender_user_id == recovery.claimant_user_id
            else "finder"
        ),
        body=payload.body,
        created_at=message.created_at,
    )
