"""Tests CRUD favorites — isolation par utilisateur."""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _register_and_login(client, email: str, password: str = "validpass1") -> None:
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    await client.post("/api/v1/auth/login", json={"email": email, "password": password})


async def _create_course(client) -> int:
    """Crée un cours SCAP et retourne son id."""
    resp = await client.post(
        "/api/v1/courses",
        json={"title": "Cours test", "category": "Informatique", "year": 2024},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_market_course(client) -> int:
    """Crée un market course et retourne son id."""
    resp = await client.post(
        "/api/v1/market-courses",
        json={"title": "Formation marché", "status": "candidate"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Validation payload
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_favorite_without_any_id_rejected(client):
    """Un favori sans course_id ni market_course_id doit être rejeté (422)."""
    await _register_and_login(client, "admin@test.com")
    resp = await client.post("/api/v1/favorites", json={})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Favoris sur cours SCAP
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_favorite_course(client):
    await _register_and_login(client, "admin@test.com")
    course_id = await _create_course(client)
    resp = await client.post("/api/v1/favorites", json={"course_id": course_id})
    assert resp.status_code == 201
    data = resp.json()
    assert data["course_id"] == course_id
    assert data["market_course_id"] is None


@pytest.mark.asyncio
async def test_create_favorite_market_course(client):
    await _register_and_login(client, "admin@test.com")
    mc_id = await _create_market_course(client)
    resp = await client.post("/api/v1/favorites", json={"market_course_id": mc_id})
    assert resp.status_code == 201
    data = resp.json()
    assert data["market_course_id"] == mc_id
    assert data["course_id"] is None


@pytest.mark.asyncio
async def test_create_favorite_duplicate_rejected(client):
    """Double favori sur le même cours → 409."""
    await _register_and_login(client, "admin@test.com")
    course_id = await _create_course(client)
    await client.post("/api/v1/favorites", json={"course_id": course_id})
    resp = await client.post("/api/v1/favorites", json={"course_id": course_id})
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Isolation par utilisateur
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_user_sees_only_own_favorites(client):
    """User A ne voit pas les favoris de User B."""
    # Admin (user A) crée un cours et l'ajoute en favori
    await _register_and_login(client, "admin@test.com")
    course_id = await _create_course(client)
    await client.post("/api/v1/favorites", json={"course_id": course_id})
    # Vérification : admin voit son favori
    resp_admin = await client.get("/api/v1/favorites")
    assert len(resp_admin.json()) == 1

    # Logout + login en tant que user B
    await client.post("/api/v1/auth/logout")
    await _register_and_login(client, "user_b@test.com")
    # User B ne doit voir aucun favori
    resp_b = await client.get("/api/v1/favorites")
    assert resp_b.status_code == 200
    assert resp_b.json() == []


@pytest.mark.asyncio
async def test_user_cannot_delete_other_user_favorite(client):
    """User B ne peut pas supprimer un favori appartenant à User A."""
    # Admin crée un favori
    await _register_and_login(client, "admin@test.com")
    course_id = await _create_course(client)
    fav_resp = await client.post("/api/v1/favorites", json={"course_id": course_id})
    fav_id = fav_resp.json()["id"]

    # Logout + login en tant que user B
    await client.post("/api/v1/auth/logout")
    await _register_and_login(client, "user_b@test.com")
    resp = await client.delete(f"/api/v1/favorites/{fav_id}")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Delete par le propriétaire
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_own_favorite(client):
    await _register_and_login(client, "admin@test.com")
    course_id = await _create_course(client)
    fav_resp = await client.post("/api/v1/favorites", json={"course_id": course_id})
    fav_id = fav_resp.json()["id"]
    resp = await client.delete(f"/api/v1/favorites/{fav_id}")
    assert resp.status_code == 204
    # Plus dans la liste
    list_resp = await client.get("/api/v1/favorites")
    assert list_resp.json() == []


# ---------------------------------------------------------------------------
# Auth requise
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_favorites_unauthenticated(client):
    resp = await client.get("/api/v1/favorites")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_favorite_unauthenticated(client):
    resp = await client.post("/api/v1/favorites", json={"course_id": 1})
    assert resp.status_code == 401
