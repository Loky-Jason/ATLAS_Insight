"""Tests — endpoints `/gap-recommendations/{rec_id}` (détail + reject + approve).

Couvre :
- GET /{rec_id}       → 200 + données
- GET /{rec_id}       → 404 si introuvable
- POST /{rec_id}/reject → 200 + {id, type, status: "rejected"}
- POST /{rec_id}/reject → 404 si introuvable / 409 si non draft
- POST /{rec_id}/approve → 200 + {id, type, status: "approved"}
- POST /{rec_id}/approve → 404 si introuvable / 409 si non draft
- Auth : 401 non auth / 403 user non-admin
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.course import Course
from app.models.gap_recommendation import GapRecommendation


async def _register_and_login(
    client: AsyncClient, email: str, password: str = "validpass1"
) -> None:
    """Crée un compte puis ouvre la session (cookie httpOnly posé par /auth/login)."""
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    await client.post("/api/v1/auth/login", json={"email": email, "password": password})


# ===================================================================
# GET /{rec_id}
# ===================================================================


@pytest.mark.asyncio
async def test_get_recommendation_success(client, db_session):
    """GET renvoie la recommandation avec tous les champs."""
    await _register_and_login(client, "admin@test.com")

    rec = GapRecommendation(
        recommendation_type="closure",
        score=85.0,
        status="draft",
        rationale="Test détail",
        score_breakdown='{"schools_offering_count": 0.3}',
        schools_offering='["École A"]',
    )
    db_session.add(rec)
    await db_session.flush()
    rec_id = rec.id

    resp = await client.get(f"/api/v1/gap-recommendations/{rec_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == rec_id
    assert data["recommendation_type"] == "closure"
    assert data["score"] == 85.0
    assert data["status"] == "draft"
    assert data["rationale"] == "Test détail"
    assert data["score_breakdown"] is not None
    assert data["schools_offering"] is not None
    assert "suggested_hours" in data
    assert "certification_suggestions" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_get_recommendation_not_found(client):
    """GET sur un id inexistant → 404."""
    await _register_and_login(client, "admin2@test.com")

    resp = await client.get("/api/v1/gap-recommendations/99999")
    assert resp.status_code == 404
    assert "introuvable" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_get_recommendation_unauthenticated(client):
    """GET sans cookie → 401."""
    resp = await client.get("/api/v1/gap-recommendations/1")
    assert resp.status_code == 401


# ===================================================================
# POST /{rec_id}/reject
# ===================================================================


@pytest.mark.asyncio
async def test_reject_recommendation_success(client, db_session):
    """POST reject → 200 + {id, type, status: rejected}."""
    await _register_and_login(client, "admin3@test.com")

    rec = GapRecommendation(
        recommendation_type="creation",
        score=72.0,
        status="draft",
        rationale="Test reject API",
    )
    db_session.add(rec)
    await db_session.flush()
    rec_id = rec.id

    resp = await client.post(f"/api/v1/gap-recommendations/{rec_id}/reject")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"id": rec_id, "type": "creation", "status": "rejected"}

    # Vérifie que le statut a bien changé en base
    await db_session.refresh(rec)
    assert rec.status == "rejected"


@pytest.mark.asyncio
async def test_reject_recommendation_not_found(client):
    """POST reject sur id inexistant → 404."""
    await _register_and_login(client, "admin4@test.com")

    resp = await client.post("/api/v1/gap-recommendations/99999/reject")
    assert resp.status_code == 404
    assert "introuvable" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_reject_recommendation_unauthenticated(client):
    """POST reject sans cookie → 401."""
    resp = await client.post("/api/v1/gap-recommendations/1/reject")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_reject_recommendation_regular_user_returns_403(client):
    """Un user normal (non-admin) → 403."""
    # Premier compte = admin bootstrap
    await _register_and_login(client, "admin5@test.com")
    await client.post("/api/v1/auth/logout")

    # Second compte = user forcé
    await _register_and_login(client, "user@test.com")
    resp = await client.post("/api/v1/gap-recommendations/1/reject")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_reject_recommendation_non_draft_returns_409(client, db_session):
    """POST reject sur recommandation déjà approuvée → 409."""
    await _register_and_login(client, "admin6@test.com")

    rec = GapRecommendation(
        recommendation_type="creation",
        score=72.0,
        status="approved",
        rationale="Déjà approuvée",
    )
    db_session.add(rec)
    await db_session.flush()

    resp = await client.post(f"/api/v1/gap-recommendations/{rec.id}/reject")
    assert resp.status_code == 409
    assert "pas modifiable" in resp.json()["detail"]


# ===================================================================
# POST /{rec_id}/approve
# ===================================================================


@pytest.mark.asyncio
async def test_approve_recommendation_success(client, db_session):
    """POST approve creation → 200 + {id, type, status: approved}."""
    await _register_and_login(client, "admin7@test.com")

    rec = GapRecommendation(
        recommendation_type="creation",
        score=72.0,
        status="draft",
        rationale="Test approve API",
    )
    db_session.add(rec)
    await db_session.flush()
    rec_id = rec.id

    resp = await client.post(f"/api/v1/gap-recommendations/{rec_id}/approve")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == rec_id
    assert data["type"] == "creation"
    assert data["status"] == "approved"
    assert data["action"].startswith("created_proposal_")


@pytest.mark.asyncio
async def test_approve_recommendation_not_found(client):
    """POST approve sur id inexistant → 404."""
    await _register_and_login(client, "admin8@test.com")

    resp = await client.post("/api/v1/gap-recommendations/99999/approve")
    assert resp.status_code == 404
    assert "introuvable" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_approve_recommendation_non_draft_returns_409(client, db_session):
    """POST approve sur recommandation déjà rejetée → 409."""
    await _register_and_login(client, "admin9@test.com")

    rec = GapRecommendation(
        recommendation_type="creation",
        score=72.0,
        status="rejected",
        rationale="Déjà rejetée",
    )
    db_session.add(rec)
    await db_session.flush()

    resp = await client.post(f"/api/v1/gap-recommendations/{rec.id}/approve")
    assert resp.status_code == 409
    assert "pas modifiable" in resp.json()["detail"]


# ===================================================================
# course_title / course_description (props calculées)
# ===================================================================


@pytest.mark.asyncio
async def test_closure_candidates_serialize_course_title(client, db_session):
    """/closure-candidates expose course_title/description sans crash lazy async.

    Garde-fou : course_title lit rec.scap_course. En SQLAlchemy async, un lazy
    load implicite lèverait MissingGreenlet — l'endpoint DOIT selectinload.
    Ce test échoue si le selectinload est retiré.
    """
    await _register_and_login(client, "closure-title@test.com")

    course = Course(title="Comptabilité publique", category="Finance", hours_estimated=40)
    db_session.add(course)
    await db_session.flush()

    rec = GapRecommendation(
        recommendation_type="closure",
        scap_course_id=course.id,
        score=90.0,
        status="draft",
    )
    db_session.add(rec)
    await db_session.flush()

    resp = await client.get("/api/v1/gap-recommendations/closure-candidates")
    assert resp.status_code == 200
    item = next(r for r in resp.json() if r["id"] == rec.id)
    assert item["course_title"] == "Comptabilité publique"
    assert "Catégorie : Finance" in item["course_description"]


@pytest.mark.asyncio
async def test_creation_has_no_redundant_description(client, db_session):
    """course_description = None pour creation (info déjà affichée par la carte)."""
    rec = GapRecommendation(
        recommendation_type="creation",
        creation_key="charpente bois",
        score=75.0,
        status="draft",
        score_breakdown='{"representative_title": "Charpente bois"}',
        schools_offering='["ORSYS", "Cegos"]',
        suggested_hours=35.0,
    )
    assert rec.course_title == "Charpente bois"
    assert rec.course_description is None
