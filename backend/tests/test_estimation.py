"""Tests — service estimation heures + endpoint POST /api/v1/estimate/hours."""

from __future__ import annotations

import pytest

from app.models.course import Course
from app.services.estimation_service import _token_overlap, estimate_hours

# ---------------------------------------------------------------------------
# Unit — _token_overlap
# ---------------------------------------------------------------------------

def test_token_overlap_identical():
    assert _token_overlap("Excel avancé", "Excel avancé") == 1.0


def test_token_overlap_partial():
    score = _token_overlap("Excel avancé", "Excel débutant")
    assert 0.0 < score < 1.0


def test_token_overlap_unrelated():
    score = _token_overlap("Python", "Comptabilité générale avancée")
    assert score < 0.4


# ---------------------------------------------------------------------------
# Unit — estimate_hours (service, avec db mock)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_estimate_no_courses(db_session):
    """Sans données → estimated_hours None + raison."""
    result = await estimate_hours(db_session, title="Excel avancé", category="Bureautique")
    assert result["estimated_hours"] is None
    assert result["method"] == "none"
    assert result["basis"] == []
    assert result["reason"] is not None


@pytest.mark.asyncio
async def test_estimate_similarity_same_category(db_session):
    """Cours similaire même catégorie → méthode similarity_same_category."""
    db_session.add(Course(title="Excel avancé", category="Bureautique",
                          hours_estimated=14.0, status="active"))
    db_session.add(Course(title="Excel débutant", category="Bureautique",
                          hours_estimated=7.0, status="active"))
    await db_session.flush()

    result = await estimate_hours(db_session, title="Excel intermédiaire", category="Bureautique")
    assert result["estimated_hours"] is not None
    assert result["method"] == "similarity_same_category"
    assert len(result["basis"]) >= 1


@pytest.mark.asyncio
async def test_estimate_fallback_category_average(db_session):
    """Aucun cours similaire mais même catégorie → category_average."""
    db_session.add(Course(title="Comptabilité générale", category="Finance",
                          hours_estimated=21.0, status="active"))
    db_session.add(Course(title="Fiscalité des entreprises", category="Finance",
                          hours_estimated=35.0, status="active"))
    await db_session.flush()

    # Titre très différent, même catégorie
    result = await estimate_hours(db_session, title="XYZABC", category="Finance")
    assert result["estimated_hours"] == 28.0  # moyenne (21+35)/2
    assert result["method"] == "category_average"


@pytest.mark.asyncio
async def test_estimate_fallback_global_average(db_session):
    """Aucune donnée dans la catégorie → global_average."""
    db_session.add(Course(title="Management d'équipe", category="Management",
                          hours_estimated=28.0, status="active"))
    await db_session.flush()

    result = await estimate_hours(db_session, title="Cours inconnu", category="CategInexistante")
    assert result["estimated_hours"] == 28.0
    assert result["method"] == "global_average"


@pytest.mark.asyncio
async def test_estimate_ignores_archived(db_session):
    """Les cours archivés ne sont pas utilisés dans l'estimation."""
    db_session.add(Course(title="Excel avancé", category="Bureautique",
                          hours_estimated=14.0, status="archived"))
    await db_session.flush()

    result = await estimate_hours(db_session, title="Excel avancé", category="Bureautique")
    assert result["estimated_hours"] is None
    assert result["method"] == "none"


@pytest.mark.asyncio
async def test_estimate_ignores_no_hours(db_session):
    """Les cours sans heures_estimated ne sont pas utilisés."""
    db_session.add(Course(title="Excel avancé", category="Bureautique",
                          hours_estimated=None, status="active"))
    await db_session.flush()

    result = await estimate_hours(db_session, title="Excel avancé", category="Bureautique")
    assert result["estimated_hours"] is None


# ---------------------------------------------------------------------------
# Integration — API endpoint
# ---------------------------------------------------------------------------

async def _register_and_login(client) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "estim@example.com", "password": "validpass1"},
    )
    await client.post(
        "/api/v1/auth/login",
        json={"email": "estim@example.com", "password": "validpass1"},
    )


@pytest.mark.asyncio
async def test_estimate_endpoint_unauthenticated(client):
    resp = await client.post("/api/v1/estimate/hours", json={"title": "Test"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_estimate_endpoint_no_data(client):
    await _register_and_login(client)
    resp = await client.post("/api/v1/estimate/hours", json={"title": "Cours X", "category": "Tech"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["estimated_hours"] is None
    assert data["method"] == "none"
    assert "reason" in data


@pytest.mark.asyncio
async def test_estimate_endpoint_with_data(client, db_session):
    await _register_and_login(client)
    db_session.add(Course(title="Python débutant", category="Numérique",
                          hours_estimated=21.0, status="active"))
    await db_session.flush()
    await db_session.commit()

    resp = await client.post(
        "/api/v1/estimate/hours",
        json={"title": "Python avancé", "category": "Numérique"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["estimated_hours"] is not None
    assert isinstance(data["basis"], list)


@pytest.mark.asyncio
async def test_estimate_endpoint_invalid_title(client):
    await _register_and_login(client)
    resp = await client.post("/api/v1/estimate/hours", json={"title": ""})
    assert resp.status_code == 422
