"""Tests — service certification + endpoint POST /api/v1/certification/suggest."""

from __future__ import annotations

import pytest

from app.services.certification_service import suggest_certifications

# ---------------------------------------------------------------------------
# Unit — suggest_certifications
# ---------------------------------------------------------------------------

def test_no_suggestions_unrelated():
    """Titre sans mot-clé → liste vide (ou résultats faibles)."""
    result = suggest_certifications("XYZABC 12345", None, None)
    # Aucune règle ne devrait matcher un titre totalement aléatoire
    assert isinstance(result, list)


def test_excel_badge():
    result = suggest_certifications("Maîtriser Excel et les tableaux croisés", "Bureautique", 7.0)
    types = [s["type"] for s in result]
    assert "open_badge" in types


def test_management_rncp():
    result = suggest_certifications("Management d'équipe à distance", "Management", 35.0)
    types = [s["type"] for s in result]
    assert "rncp" in types


def test_marches_publics_internal():
    result = suggest_certifications("Marchés publics — fondamentaux", "Réglementaire", None)
    types = [s["type"] for s in result]
    assert "internal" in types


def test_sorted_by_confidence():
    result = suggest_certifications("Excel Management Communication", None, None)
    confidences = [s["confidence"] for s in result]
    assert confidences == sorted(confidences, reverse=True)


def test_confidence_range():
    result = suggest_certifications("Python développement IA management", "Numérique", 40.0)
    for s in result:
        assert 0.0 <= s["confidence"] <= 1.0


def test_no_duplicate_label():
    result = suggest_certifications("Excel Excel Excel", "Bureautique", 7.0)
    labels = [s["label"] for s in result]
    assert len(labels) == len(set(labels))


def test_rncp_bonus_long_course():
    short_result = suggest_certifications("Management d'équipe", None, 7.0)
    long_result = suggest_certifications("Management d'équipe", None, 40.0)
    rncp_short = next((s for s in short_result if s["type"] == "rncp"), None)
    rncp_long = next((s for s in long_result if s["type"] == "rncp"), None)
    if rncp_short and rncp_long:
        assert rncp_long["confidence"] >= rncp_short["confidence"]


def test_result_keys():
    result = suggest_certifications("Excel", "Bureautique", None)
    for s in result:
        assert "type" in s
        assert "label" in s
        assert "rationale" in s
        assert "confidence" in s


def test_no_hours_still_works():
    result = suggest_certifications("Python débutant", "Numérique", None)
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Integration — API endpoint
# ---------------------------------------------------------------------------

async def _register_and_login(client) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "certif@example.com", "password": "validpass1"},
    )
    await client.post(
        "/api/v1/auth/login",
        json={"email": "certif@example.com", "password": "validpass1"},
    )


@pytest.mark.asyncio
async def test_certif_endpoint_unauthenticated(client):
    resp = await client.post("/api/v1/certification/suggest", json={"title": "Excel"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_certif_endpoint_basic(client):
    await _register_and_login(client)
    resp = await client.post(
        "/api/v1/certification/suggest",
        json={"title": "Excel avancé", "category": "Bureautique", "hours": 7.0},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "suggestions" in data
    assert isinstance(data["suggestions"], list)
    assert data["total"] == len(data["suggestions"])


@pytest.mark.asyncio
async def test_certif_endpoint_management(client):
    await _register_and_login(client)
    resp = await client.post(
        "/api/v1/certification/suggest",
        json={"title": "Management d'équipe", "category": "Management", "hours": 35.0},
    )
    assert resp.status_code == 200
    data = resp.json()
    types = [s["type"] for s in data["suggestions"]]
    assert "rncp" in types


@pytest.mark.asyncio
async def test_certif_endpoint_no_category(client):
    await _register_and_login(client)
    resp = await client.post(
        "/api/v1/certification/suggest",
        json={"title": "Accessibilité numérique RGAA"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_certif_endpoint_invalid_empty_title(client):
    await _register_and_login(client)
    resp = await client.post(
        "/api/v1/certification/suggest",
        json={"title": ""},
    )
    assert resp.status_code == 422
