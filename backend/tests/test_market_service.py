"""Tests — service market (StubProvider + scoring + persistance) + endpoint POST /api/v1/market/scan."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.course import Course
from app.models.market_course import MarketCourse
from app.services.market_service import (
    StubMarketProvider,
    _compute_relevance,
    run_market_scan,
)


# ---------------------------------------------------------------------------
# Unit — StubMarketProvider
# ---------------------------------------------------------------------------

def test_stub_provider_returns_list():
    provider = StubMarketProvider()
    results = provider.search("formations Paris")
    assert isinstance(results, list)
    assert len(results) > 0


def test_stub_provider_result_keys():
    provider = StubMarketProvider()
    results = provider.search("test")
    for r in results:
        assert "title" in r
        assert "school" in r
        assert "source_url" in r
        assert "summary" in r


def test_stub_provider_deterministic():
    """Deux appels → mêmes données."""
    provider = StubMarketProvider()
    r1 = provider.search("q")
    r2 = provider.search("q")
    assert [x["title"] for x in r1] == [x["title"] for x in r2]


# ---------------------------------------------------------------------------
# Unit — _compute_relevance
# ---------------------------------------------------------------------------

def test_relevance_new_category_high():
    """Catégorie absente du catalogue SCAP mais tendance → score neutre."""
    score = _compute_relevance(
        {"title": "Formation IA", "school": "X", "source_url": "", "summary": "", "category": "IA"},
        existing_titles=[],
        existing_categories=[],
    )
    assert 0.0 <= score <= 1.0


def test_relevance_existing_category_boosts():
    """Catégorie déjà présente chez SCAP → bonus."""
    score_with = _compute_relevance(
        {"title": "Excel avancé", "school": "X", "source_url": "", "summary": "", "category": "Bureautique"},
        existing_titles=[],
        existing_categories=["Bureautique"],
    )
    score_without = _compute_relevance(
        {"title": "Excel avancé", "school": "X", "source_url": "", "summary": "", "category": "Bureautique"},
        existing_titles=[],
        existing_categories=[],
    )
    assert score_with > score_without


def test_relevance_duplicate_title_penalizes():
    """Titre très similaire déjà en base → pénalité."""
    score_dup = _compute_relevance(
        {"title": "Excel avancé", "school": "X", "source_url": "", "summary": "", "category": None},
        existing_titles=["Excel avancé"],
        existing_categories=[],
    )
    score_new = _compute_relevance(
        {"title": "Excel avancé", "school": "X", "source_url": "", "summary": "", "category": None},
        existing_titles=[],
        existing_categories=[],
    )
    assert score_dup < score_new


def test_relevance_bounded():
    """Le score doit rester dans [0, 1]."""
    score = _compute_relevance(
        {"title": "Formation X", "school": "Y", "source_url": "", "summary": "", "category": "Cat"},
        existing_titles=["Formation X"],
        existing_categories=["Cat"],
    )
    assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# Integration — run_market_scan
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_market_scan_inserts_market_courses(db_session):
    inserted_count = 0
    result = await run_market_scan(db_session, user_id=1)
    inserted_count = result["inserted"]
    assert inserted_count > 0
    assert result["provider"] == "StubMarketProvider"

    # Vérifie en base
    mc_result = await db_session.execute(
        select(MarketCourse).where(MarketCourse.status == "candidate")
    )
    mcs = mc_result.scalars().all()
    assert len(mcs) == inserted_count


@pytest.mark.asyncio
async def test_market_scan_no_duplicate(db_session):
    """Deux scans successifs → pas de doublons."""
    result1 = await run_market_scan(db_session, user_id=1)
    result2 = await run_market_scan(db_session, user_id=1)
    assert result2["inserted"] == 0
    assert result2["skipped"] == result1["inserted"]


@pytest.mark.asyncio
async def test_market_scan_sets_relevance_score(db_session):
    await run_market_scan(db_session, user_id=1)
    mc_result = await db_session.execute(select(MarketCourse))
    for mc in mc_result.scalars().all():
        assert mc.relevance_score is not None
        assert 0.0 <= mc.relevance_score <= 1.0


@pytest.mark.asyncio
async def test_market_scan_with_existing_scap(db_session):
    """Un cours SCAP similaire à un résultat stub → score plus bas."""
    db_session.add(Course(
        title="Excel avancé — tableaux croisés dynamiques",
        category="Bureautique",
        status="active",
        hours_estimated=14.0,
    ))
    await db_session.flush()

    result = await run_market_scan(db_session, user_id=1)
    mc_result = await db_session.execute(
        select(MarketCourse).where(
            MarketCourse.title == "Excel avancé — tableaux croisés dynamiques"
        )
    )
    excel_mc = mc_result.scalar_one_or_none()
    assert excel_mc is not None
    # Score pénalisé car doublon SCAP
    assert excel_mc.relevance_score < 0.5


# ---------------------------------------------------------------------------
# Integration — API endpoint /api/v1/market/scan
# ---------------------------------------------------------------------------

async def _register_and_login_admin(client) -> None:
    """Premier compte = admin bootstrap."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "admin@example.com", "password": "validpass1"},
    )
    await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "validpass1"},
    )


async def _register_and_login_user(client, email: str = "user@example.com") -> None:
    """Crée un second compte non-admin."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "validpass1"},
    )
    await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "validpass1"},
    )


@pytest.mark.asyncio
async def test_market_scan_endpoint_unauthenticated(client):
    resp = await client.post("/api/v1/market/scan")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_market_scan_endpoint_non_admin_forbidden(client):
    # Enregistrer admin d'abord (bootstrap), puis un user normal
    await _register_and_login_admin(client)
    await client.post("/api/v1/auth/logout")
    await _register_and_login_user(client, "regular@example.com")

    resp = await client.post("/api/v1/market/scan")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_market_scan_endpoint_admin_success(client, db_session):
    await _register_and_login_admin(client)
    resp = await client.post("/api/v1/market/scan")
    assert resp.status_code == 201
    data = resp.json()
    assert "inserted" in data
    assert "skipped" in data
    assert "provider" in data
    assert "results" in data
    assert isinstance(data["results"], list)
    assert data["inserted"] > 0


@pytest.mark.asyncio
async def test_market_scan_endpoint_audit_log(client, db_session):
    await _register_and_login_admin(client)
    await client.post("/api/v1/market/scan")

    # Vérifier qu'un AuditLog a été créé
    audit_result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "market_scan")
    )
    logs = audit_result.scalars().all()
    assert len(logs) >= 1
    assert logs[0].target is not None


@pytest.mark.asyncio
async def test_market_scan_endpoint_idempotent(client, db_session):
    """Deux appels consécutifs → second scan insère 0."""
    await _register_and_login_admin(client)
    resp1 = await client.post("/api/v1/market/scan")
    resp2 = await client.post("/api/v1/market/scan")
    assert resp1.status_code == 201
    assert resp2.status_code == 201
    assert resp2.json()["inserted"] == 0


@pytest.mark.asyncio
async def test_market_scan_endpoint_custom_query(client):
    await _register_and_login_admin(client)
    resp = await client.post("/api/v1/market/scan?query=formation+management+Paris")
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_market_scan_endpoint_invalid_query(client):
    await _register_and_login_admin(client)
    # query trop courte (< 3 chars)
    resp = await client.post("/api/v1/market/scan?query=ab")
    assert resp.status_code == 422
