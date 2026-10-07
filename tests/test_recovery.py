"""End-to-end tests for the secure ownership verification workflow."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item import Item
from app.models.match import Match
from app.models.recovery import RecoveryMessage, RecoveryRequest
from app.models.user import User
from app.services.auth import auth_service


@pytest.mark.asyncio
async def test_secure_recovery_journey(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    auth_headers: dict,
):
    finder = User(
        id=str(uuid4()),
        email="finder@example.com",
        hashed_password=auth_service.hash_password("finder-password"),
        full_name="Finder",
        phone_number="+970590000001",
        is_active=True,
        is_verified=True,
    )
    db_session.add(finder)
    await db_session.flush()

    event_date = datetime.now(timezone.utc)
    lost_item = Item(
        user_id=test_user.id,
        item_type="phone",
        lost_or_found="lost",
        title="Lost phone",
        event_date=event_date,
        status="active",
    )
    found_item = Item(
        user_id=finder.id,
        item_type="phone",
        lost_or_found="found",
        title="Found phone",
        event_date=event_date,
        status="active",
    )
    db_session.add_all([lost_item, found_item])
    await db_session.flush()

    match = Match(
        source_item_id=lost_item.id,
        target_item_id=found_item.id,
        overall_score=0.82,
        vector_similarity=0.85,
        phash_similarity=0.80,
        orb_match_score=0.75,
        status="pending",
    )
    db_session.add(match)
    await db_session.commit()
    await db_session.refresh(match)

    finder_headers = {
        "Authorization": f"Bearer {auth_service.create_access_token(finder.id)}"
    }
    challenge_response = await client.put(
        f"/api/v1/items/{found_item.id}/ownership-challenge",
        headers=finder_headers,
        json={
            "question": "ما العلامة المميزة الموجودة خلف الجهاز؟",
            "private_details": "خدش صغير أسفل العدسة الثانية",
        },
    )
    assert challenge_response.status_code == 200
    assert "private_details" not in challenge_response.json()

    # Legacy mutually-confirmed matches must no longer reveal personal contact data.
    match.status = "both_confirmed"
    await db_session.commit()
    private_match = await client.get(
        f"/api/v1/matches/{match.id}", headers=auth_headers
    )
    assert private_match.status_code == 200
    assert private_match.json()["contact_info"] is None
    match.status = "pending"
    await db_session.commit()

    legacy_confirm = await client.post(
        f"/api/v1/matches/{match.id}/confirm",
        headers=auth_headers,
        json={"confirmed": True},
    )
    assert legacy_confirm.status_code == 409

    create_response = await client.post(
        f"/api/v1/matches/{match.id}/recovery-requests",
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    recovery = create_response.json()
    recovery_id = recovery["id"]
    assert recovery["status"] == "awaiting_proof"
    assert recovery["current_user_role"] == "claimant"
    assert recovery["private_reference_details"] is None
    assert recovery["reference_code"].startswith("MS-")

    proof_text = "يوجد خدش صغير أسفل العدسة الثانية وجراب أسود"
    proof_response = await client.post(
        f"/api/v1/recovery-requests/{recovery_id}/proof",
        headers=auth_headers,
        json={"answer": proof_text},
    )
    assert proof_response.status_code == 200
    assert proof_response.json()["status"] == "proof_submitted"

    finder_case = await client.get(
        f"/api/v1/recovery-requests/{recovery_id}", headers=finder_headers
    )
    assert finder_case.status_code == 200
    assert finder_case.json()["proof_answer"] == proof_text
    assert finder_case.json()["private_reference_details"] == "خدش صغير أسفل العدسة الثانية"

    review_response = await client.post(
        f"/api/v1/recovery-requests/{recovery_id}/review",
        headers=finder_headers,
        json={"approved": True, "note": "الوصف مطابق"},
    )
    assert review_response.status_code == 200
    assert review_response.json()["status"] == "ownership_verified"

    message_response = await client.post(
        f"/api/v1/recovery-requests/{recovery_id}/messages",
        headers=auth_headers,
        json={"body": "يمكننا اللقاء في مكان عام غدًا"},
    )
    assert message_response.status_code == 201

    messages_response = await client.get(
        f"/api/v1/recovery-requests/{recovery_id}/messages",
        headers=finder_headers,
    )
    assert messages_response.status_code == 200
    assert messages_response.json()[0]["body"] == "يمكننا اللقاء في مكان عام غدًا"

    arrange_response = await client.post(
        f"/api/v1/recovery-requests/{recovery_id}/arrange-delivery",
        headers=finder_headers,
    )
    assert arrange_response.status_code == 200
    assert arrange_response.json()["status"] == "delivery_arranged"

    claimant_confirmation = await client.post(
        f"/api/v1/recovery-requests/{recovery_id}/confirm-delivery",
        headers=auth_headers,
    )
    assert claimant_confirmation.status_code == 200
    assert claimant_confirmation.json()["claimant_confirmed_delivery"] is True
    assert claimant_confirmation.json()["status"] == "delivery_arranged"

    finder_confirmation = await client.post(
        f"/api/v1/recovery-requests/{recovery_id}/confirm-delivery",
        headers=finder_headers,
    )
    assert finder_confirmation.status_code == 200
    assert finder_confirmation.json()["status"] == "delivered"

    stored_recovery = (
        await db_session.execute(
            select(RecoveryRequest).where(RecoveryRequest.id == recovery_id)
        )
    ).scalar_one()
    stored_message = (
        await db_session.execute(
            select(RecoveryMessage).where(
                RecoveryMessage.recovery_request_id == recovery_id
            )
        )
    ).scalar_one()
    assert proof_text not in stored_recovery.proof_encrypted
    assert "مكان عام" not in stored_message.body_encrypted

    await db_session.refresh(lost_item)
    await db_session.refresh(found_item)
    assert lost_item.status == "resolved"
    assert found_item.status == "resolved"
