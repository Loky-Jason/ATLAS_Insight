"""Tests — service market (StubProvider + scoring + persistance) + endpoint POST /api/v1/market/scan."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.course import Course
from app.models.market_course import MarketCourse
from app.services.market_service import (
    StubMarketProvider,
    WebMarketProvider,
    _compute_relevance,
    get_market_provider,
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
# Unit — WebMarketProvider
# ---------------------------------------------------------------------------

_SAMPLE_HTML_PAGE = """\
<h3>2 r&eacute;sultats</h3>
<div class="accordion" id="accordionElement13769">
    <div class="card-header element-header">
        <div class="card-title">
            <h4> Illustration et narration, projet d&#x27;album jeunesse</h4>
            <p>Dur&eacute;e maximum : 60 heures / Tarif plein : 350&euro;</p>
        </div>
    </div>
    <div id="element13769" class="collapse">
        <div class="card-body element-body">
            <h5>Objectif :</h5>
            <p>Apprendre &agrave; finaliser un projet d&#x27;&eacute;dition.</p>
            <a class="element-folder" href="/Element/Details/13769">Voir la fiche</a>
        </div>
    </div>
</div>
<div class="accordion" id="accordionElement14069">
    <div class="card-header element-header">
        <div class="card-title">
            <h4> Int&eacute;gration de l&#x27;IA g&eacute;n&eacute;rative</h4>
            <p>Dur&eacute;e maximum : 45 heures / Tarif plein : 260&euro;</p>
        </div>
    </div>
    <div id="element14069" class="collapse">
        <div class="card-body element-body">
            <h5>Objectif :</h5>
            <p>Comprendre les concepts fondamentaux de l&#x27;IA.</p>
            <a class="element-folder" href="/Element/Details/14069">Voir la fiche</a>
        </div>
    </div>
</div>
<nav aria-label="Page navigation">
    <ul class="pagination">
        <li class="page-item active">
            <button class="page-link" onclick="changePage(0)">1</button>
        </li>
        <li class="page-item">
            <button class="page-link" onclick="changePage(1)">2</button>
        </li>
        <li class="page-item">
            <button class="page-link" onclick="changePage(2)">3</button>
        </li>
    </ul>
</nav>
"""

_SAMPLE_HTML_LAST_PAGE = """\
<h3>2 r&eacute;sultats</h3>
<div class="accordion" id="accordionElement99999">
    <div class="card-header element-header">
        <div class="card-title">
            <h4> Dernier cours du catalogue</h4>
            <p>Dur&eacute;e maximum : 30 heures / Tarif plein : 200&euro;</p>
        </div>
    </div>
    <div id="element99999" class="collapse">
        <div class="card-body element-body">
            <h5>Objectif :</h5>
            <p>Objectif final.</p>
        </div>
    </div>
</div>
<nav aria-label="Page navigation">
    <ul class="pagination">
        <li class="page-item">
            <button class="page-link" onclick="changePage(0)">1</button>
        </li>
        <li class="page-item active">
            <button class="page-link" onclick="changePage(2)">3</button>
        </li>
    </ul>
</nav>
"""

_SAMPLE_HTML_EMPTY = """\
<h3>0 r&eacute;sultats</h3>
"""


def test_web_provider_parse_page():
    provider = WebMarketProvider(client=MagicMock())
    results = provider._parse_page(_SAMPLE_HTML_PAGE)
    assert len(results) == 2
    assert results[0]["title"] == "Illustration et narration, projet d'album jeunesse"
    assert results[0]["school"] == "SCAP / Cours d'Adultes de Paris"
    assert results[0]["source_url"] == "https://scap.paris.fr/Element/Details/13769"
    assert "finaliser" in results[0]["summary"]
    assert results[0]["category"] is None


def test_web_provider_has_next_true():
    assert WebMarketProvider._has_next(_SAMPLE_HTML_PAGE) is True


def test_web_provider_has_next_false():
    assert WebMarketProvider._has_next(_SAMPLE_HTML_LAST_PAGE) is False


def test_web_provider_has_next_empty():
    assert WebMarketProvider._has_next(_SAMPLE_HTML_EMPTY) is False


def test_web_provider_search_single_page():
    session = MagicMock()
    resp = MagicMock()
    resp.text = _SAMPLE_HTML_LAST_PAGE
    resp.raise_for_status.return_value = None
    session.post.return_value = resp

    provider = WebMarketProvider(client=session)
    results = provider.search("test")
    assert len(results) == 1
    assert results[0]["title"] == "Dernier cours du catalogue"


def test_web_provider_search_multi_page():
    session = MagicMock()
    resp1 = MagicMock()
    resp1.text = _SAMPLE_HTML_PAGE
    resp1.raise_for_status.return_value = None
    resp2 = MagicMock()
    resp2.text = _SAMPLE_HTML_LAST_PAGE
    resp2.raise_for_status.return_value = None
    session.post.side_effect = [resp1, resp2]

    provider = WebMarketProvider(client=session)
    results = provider.search("test")
    assert len(results) == 3  # 2 from page 0 + 1 from page 1
    assert session.post.call_count == 2


def test_web_provider_result_keys():
    session = MagicMock()
    resp = MagicMock()
    resp.text = _SAMPLE_HTML_LAST_PAGE
    resp.raise_for_status.return_value = None
    session.post.return_value = resp

    provider = WebMarketProvider(client=session)
    results = provider.search("test")
    for r in results:
        assert "title" in r
        assert "school" in r
        assert "source_url" in r
        assert "summary" in r
        assert "category" in r


def test_web_provider_search_http_error():
    session = MagicMock()
    resp = MagicMock()
    resp.raise_for_status.side_effect = Exception("HTTP 500")
    session.post.return_value = resp

    provider = WebMarketProvider(client=session)
    with pytest.raises(Exception, match="HTTP 500"):
        provider.search("test")


def test_web_provider_search_empty_page():
    session = MagicMock()
    resp = MagicMock()
    resp.text = _SAMPLE_HTML_EMPTY
    resp.raise_for_status.return_value = None
    session.post.return_value = resp

    provider = WebMarketProvider(client=session)
    results = provider.search("test")
    assert len(results) == 0


def test_web_provider_search_last_page_with_pagination():
    """Dernière page avec pagination (active == max) → s'arrête."""
    session = MagicMock()
    resp = MagicMock()
    resp.text = _SAMPLE_HTML_LAST_PAGE
    resp.raise_for_status.return_value = None
    session.post.return_value = resp

    provider = WebMarketProvider(client=session)
    results = provider.search("test")
    assert len(results) == 1
    assert session.post.call_count == 1


@patch("app.services.market_service.settings")
def test_get_market_provider_web(mock_settings):
    mock_settings.market_provider = "web"
    provider = get_market_provider()
    assert isinstance(provider, WebMarketProvider)


@patch("app.services.market_service.settings")
def test_get_market_provider_stub(mock_settings):
    mock_settings.market_provider = "stub"
    provider = get_market_provider()
    assert isinstance(provider, StubMarketProvider)


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

    await run_market_scan(db_session, user_id=1)
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
