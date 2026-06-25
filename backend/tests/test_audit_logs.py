"""Tests audit_logs — lecture paginée, accès admin uniquement."""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _register_and_login(client, email: str, password: str = "validpass1") -> None:
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    await client.post("/api/v1/auth/login", json={"email": email, "password": password})


# ---------------------------------------------------------------------------
# Contrôle d'accès
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_logs_require_admin(client):
    """Un user normal reçoit 403 sur /audit-logs."""
    # Premier compte = admin
    await _register_and_login(client, "admin@test.com")
    # Deuxième compte = user forcé
    await client.post("/api/v1/auth/logout")
    await _register_and_login(client, "user@test.com")
    resp = await client.get("/api/v1/audit-logs")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_audit_logs_unauthenticated(client):
    resp = await client.get("/api/v1/audit-logs")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Lecture
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_logs_list_empty(client):
    """Admin voit une liste vide si aucune action destructive n'a été loggée."""
    await _register_and_login(client, "admin@test.com")
    resp = await client.get("/api/v1/audit-logs")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_audit_logs_generated_after_destructive_action(client):
    """Un delete de market_course doit produire un audit log."""
    await _register_and_login(client, "admin@test.com")
    # Créer une formation marché
    create_resp = await client.post(
        "/api/v1/market-courses",
        json={"title": "À supprimer", "status": "candidate"},
    )
    mc_id = create_resp.json()["id"]
    # Supprimer (action destructive → AuditLog)
    await client.delete(f"/api/v1/market-courses/{mc_id}")
    # Vérifier la présence du log
    resp = await client.get("/api/v1/audit-logs")
    assert resp.status_code == 200
    logs = resp.json()
    assert len(logs) >= 1
    actions = [log["action"] for log in logs]
    assert "delete_market_course" in actions


@pytest.mark.asyncio
async def test_audit_logs_pagination(client):
    """Paramètres skip/limit fonctionnent."""
    await _register_and_login(client, "admin@test.com")
    # Créer et supprimer 3 market courses → 3 logs
    for i in range(3):
        cr = await client.post(
            "/api/v1/market-courses",
            json={"title": f"MC {i}", "status": "candidate"},
        )
        await client.delete(f"/api/v1/market-courses/{cr.json()['id']}")
    # Vérification pagination
    resp_all = await client.get("/api/v1/audit-logs?limit=10")
    assert resp_all.status_code == 200
    total = len(resp_all.json())
    assert total >= 3
    # limit=1 → 1 résultat
    resp_one = await client.get("/api/v1/audit-logs?limit=1")
    assert len(resp_one.json()) == 1
    # skip=total → liste vide
    resp_skip = await client.get(f"/api/v1/audit-logs?skip={total}")
    assert resp_skip.json() == []


@pytest.mark.asyncio
async def test_audit_logs_filter_action(client):
    """Filtre par action fonctionne."""
    await _register_and_login(client, "admin@test.com")
    # Créer + supprimer un market course
    cr = await client.post(
        "/api/v1/market-courses",
        json={"title": "MC filtre", "status": "candidate"},
    )
    await client.delete(f"/api/v1/market-courses/{cr.json()['id']}")
    resp = await client.get("/api/v1/audit-logs?action=delete_market_course")
    assert resp.status_code == 200
    logs = resp.json()
    assert all(log["action"] == "delete_market_course" for log in logs)
