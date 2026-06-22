"""Tests analytics — popularité, top/flop, refresh scores."""

from __future__ import annotations

import pytest

from app.models.course import Course
from app.services.analytics_service import compute_raw_score


# ---------------------------------------------------------------------------
# Unit tests (no DB)
# ---------------------------------------------------------------------------

def test_compute_raw_score_basic():
    assert compute_raw_score(100, 0) == 100.0


def test_compute_raw_score_dropout_penalty():
    # 20 - (10 * 1.5) = 5.0
    assert compute_raw_score(20, 10) == 5.0


def test_compute_raw_score_never_negative():
    # résultat négatif brut → 0
    assert compute_raw_score(5, 10) == 0.0


# ---------------------------------------------------------------------------
# Integration tests (API)
# ---------------------------------------------------------------------------

async def _register_and_login(client) -> None:
    # Premier compte = admin bootstrap (role ignoré dans le schéma)
    await client.post(
        "/api/v1/auth/register",
        json={"email": "analyst@example.com", "password": "validpass1"},
    )
    await client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@example.com", "password": "validpass1"},
    )


async def _create_course(client, title: str, enrolled: int, dropout: int) -> dict:
    resp = await client.post(
        "/api/v1/courses",
        json={
            "title": title,
            "enrolled_count": enrolled,
            "dropout_count": dropout,
        },
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_refresh_scores(client):
    await _register_and_login(client)
    await _create_course(client, "Cours A", enrolled=100, dropout=5)
    await _create_course(client, "Cours B", enrolled=20, dropout=15)

    resp = await client.post("/api/v1/analytics/refresh-scores")
    assert resp.status_code == 200
    data = resp.json()
    assert data["updated"] == 2


@pytest.mark.asyncio
async def test_popularity_top_flop(client):
    await _register_and_login(client)
    await _create_course(client, "Top cours", enrolled=200, dropout=0)
    await _create_course(client, "Flop cours", enrolled=5, dropout=4)
    await client.post("/api/v1/analytics/refresh-scores")

    resp = await client.get("/api/v1/analytics/popularity?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "top" in data
    assert "flop" in data
    # Le top cours doit apparaître en premier
    assert data["top"][0]["title"] == "Top cours"


@pytest.mark.asyncio
async def test_popularity_unauthenticated(client):
    resp = await client.get("/api/v1/analytics/popularity")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_popularity_empty_db(client):
    """Sans cours en base, top et flop doivent être des listes vides."""
    await _register_and_login(client)
    resp = await client.get("/api/v1/analytics/popularity")
    assert resp.status_code == 200
    data = resp.json()
    assert data["top"] == []
    assert data["flop"] == []
