"""Tests CRUD market_courses."""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _register_and_login(client, email: str, password: str = "validpass1") -> None:
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    await client.post("/api/v1/auth/login", json={"email": email, "password": password})


async def _create_admin_session(client) -> None:
    """Premier compte = admin bootstrap."""
    await _register_and_login(client, "admin@test.com")


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_market_courses_empty(client):
    await _create_admin_session(client)
    resp = await client.get("/api/v1/market-courses")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_market_courses_unauthenticated(client):
    resp = await client.get("/api/v1/market-courses")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_market_course(client):
    await _create_admin_session(client)
    payload = {"title": "Python avancé", "school": "École XYZ", "status": "candidate"}
    resp = await client.post("/api/v1/market-courses", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Python avancé"
    assert data["school"] == "École XYZ"
    assert data["status"] == "candidate"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_market_course_invalid_status(client):
    await _create_admin_session(client)
    resp = await client.post(
        "/api/v1/market-courses",
        json={"title": "Test", "status": "invalid_status"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_market_course_invalid_relevance_score(client):
    await _create_admin_session(client)
    resp = await client.post(
        "/api/v1/market-courses",
        json={"title": "Test", "relevance_score": 1.5},  # > 1.0
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Get
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_market_course(client):
    await _create_admin_session(client)
    create_resp = await client.post(
        "/api/v1/market-courses",
        json={"title": "Data Science", "status": "reviewed"},
    )
    mc_id = create_resp.json()["id"]
    resp = await client.get(f"/api/v1/market-courses/{mc_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Data Science"


@pytest.mark.asyncio
async def test_get_market_course_not_found(client):
    await _create_admin_session(client)
    resp = await client.get("/api/v1/market-courses/99999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_market_course(client):
    await _create_admin_session(client)
    create_resp = await client.post(
        "/api/v1/market-courses",
        json={"title": "Old title", "status": "candidate"},
    )
    mc_id = create_resp.json()["id"]
    resp = await client.patch(
        f"/api/v1/market-courses/{mc_id}",
        json={"title": "New title", "status": "reviewed", "relevance_score": 0.8},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "New title"
    assert data["status"] == "reviewed"
    assert data["relevance_score"] == pytest.approx(0.8)


# ---------------------------------------------------------------------------
# Delete (admin only)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_market_course_admin(client):
    await _create_admin_session(client)
    create_resp = await client.post(
        "/api/v1/market-courses",
        json={"title": "To delete", "status": "candidate"},
    )
    mc_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/v1/market-courses/{mc_id}")
    assert resp.status_code == 204
    # Vérification suppression effective
    get_resp = await client.get(f"/api/v1/market-courses/{mc_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_market_course_regular_user_forbidden(client):
    """Un user normal ne peut pas supprimer une formation marché."""
    # Admin crée la ressource
    await _register_and_login(client, "admin2@test.com")
    create_resp = await client.post(
        "/api/v1/market-courses",
        json={"title": "Protected", "status": "candidate"},
    )
    mc_id = create_resp.json()["id"]
    # Logout + login en tant que user normal
    await client.post("/api/v1/auth/logout")
    await _register_and_login(client, "user2@test.com")
    resp = await client.delete(f"/api/v1/market-courses/{mc_id}")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_market_courses_filter_status(client):
    await _create_admin_session(client)
    await client.post("/api/v1/market-courses", json={"title": "A", "status": "candidate"})
    await client.post("/api/v1/market-courses", json={"title": "B", "status": "adopted"})
    resp = await client.get("/api/v1/market-courses?status=candidate")
    assert resp.status_code == 200
    results = resp.json()
    assert all(r["status"] == "candidate" for r in results)
    assert len(results) == 1


@pytest.mark.asyncio
async def test_list_market_courses_filter_search(client):
    await _create_admin_session(client)
    await client.post("/api/v1/market-courses", json={"title": "Python avancé", "status": "candidate"})
    await client.post("/api/v1/market-courses", json={"title": "JavaScript ES2024", "status": "candidate"})
    resp = await client.get("/api/v1/market-courses?search=python")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert "Python" in results[0]["title"]
