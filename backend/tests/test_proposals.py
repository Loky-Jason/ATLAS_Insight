"""Tests CRUD proposals (CourseProposal)."""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _register_and_login(client, email: str, password: str = "validpass1") -> None:
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    await client.post("/api/v1/auth/login", json={"email": email, "password": password})


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_proposals_empty(client):
    await _register_and_login(client, "admin@test.com")
    resp = await client.get("/api/v1/proposals")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_proposals_unauthenticated(client):
    resp = await client.get("/api/v1/proposals")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_proposal(client):
    await _register_and_login(client, "admin@test.com")
    payload = {
        "title": "IA générative en entreprise",
        "description": "Formation complète sur ChatGPT et outils IA.",
        "hours_estimated": 21.5,
        "status": "draft",
    }
    resp = await client.post("/api/v1/proposals", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "IA générative en entreprise"
    assert data["status"] == "draft"
    assert data["hours_estimated"] == pytest.approx(21.5)
    assert "id" in data


@pytest.mark.asyncio
async def test_create_proposal_invalid_status(client):
    await _register_and_login(client, "admin@test.com")
    resp = await client.post(
        "/api/v1/proposals",
        json={"title": "Test", "status": "unknown"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_proposal_negative_hours(client):
    await _register_and_login(client, "admin@test.com")
    resp = await client.post(
        "/api/v1/proposals",
        json={"title": "Test", "hours_estimated": -5},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Get
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_proposal(client):
    await _register_and_login(client, "admin@test.com")
    create_resp = await client.post(
        "/api/v1/proposals",
        json={"title": "Cybersécurité", "status": "proposed"},
    )
    pid = create_resp.json()["id"]
    resp = await client.get(f"/api/v1/proposals/{pid}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Cybersécurité"


@pytest.mark.asyncio
async def test_get_proposal_not_found(client):
    await _register_and_login(client, "admin@test.com")
    resp = await client.get("/api/v1/proposals/99999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_proposal(client):
    await _register_and_login(client, "admin@test.com")
    create_resp = await client.post(
        "/api/v1/proposals",
        json={"title": "Draft", "status": "draft"},
    )
    pid = create_resp.json()["id"]
    resp = await client.patch(
        f"/api/v1/proposals/{pid}",
        json={"status": "proposed", "hours_estimated": 14.0},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "proposed"
    assert data["hours_estimated"] == pytest.approx(14.0)


# ---------------------------------------------------------------------------
# Delete (admin only)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_proposal_admin(client):
    await _register_and_login(client, "admin@test.com")
    create_resp = await client.post(
        "/api/v1/proposals",
        json={"title": "À supprimer", "status": "draft"},
    )
    pid = create_resp.json()["id"]
    resp = await client.delete(f"/api/v1/proposals/{pid}")
    assert resp.status_code == 204
    get_resp = await client.get(f"/api/v1/proposals/{pid}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_proposal_regular_user_forbidden(client):
    """Un user normal ne peut pas supprimer une proposition."""
    await _register_and_login(client, "admin@test.com")
    create_resp = await client.post(
        "/api/v1/proposals",
        json={"title": "Protected", "status": "draft"},
    )
    pid = create_resp.json()["id"]
    await client.post("/api/v1/auth/logout")
    await _register_and_login(client, "user@test.com")
    resp = await client.delete(f"/api/v1/proposals/{pid}")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_proposals_filter_status(client):
    await _register_and_login(client, "admin@test.com")
    await client.post("/api/v1/proposals", json={"title": "A", "status": "draft"})
    await client.post("/api/v1/proposals", json={"title": "B", "status": "exported"})
    resp = await client.get("/api/v1/proposals?status=draft")
    assert resp.status_code == 200
    results = resp.json()
    assert all(r["status"] == "draft" for r in results)
    assert len(results) == 1


@pytest.mark.asyncio
async def test_list_proposals_filter_search(client):
    await _register_and_login(client, "admin@test.com")
    await client.post("/api/v1/proposals", json={"title": "IA générative", "status": "draft"})
    await client.post("/api/v1/proposals", json={"title": "Bureautique", "status": "draft"})
    resp = await client.get("/api/v1/proposals?search=IA")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert "IA" in results[0]["title"]
