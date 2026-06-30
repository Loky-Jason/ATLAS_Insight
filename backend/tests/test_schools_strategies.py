"""Tests — endpoint `GET /api/v1/schools/strategies` (liste des scrapers enregistrés)."""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Helpers (alignés sur test_audit_logs.py / test_auth.py)
# ---------------------------------------------------------------------------


async def _register_and_login(
    client, email: str, password: str = "validpass1"
) -> None:
    """Crée un compte puis ouvre la session (cookie httpOnly posé par /auth/login)."""
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    await client.post("/api/v1/auth/login", json={"email": email, "password": password})


# ---------------------------------------------------------------------------
# Contrôle d'accès
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_strategies_unauthenticated_returns_401(client):
    """Sans cookie d'accès → 401 (route protégée par get_current_user)."""
    resp = await client.get("/api/v1/schools/strategies")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Forme de la réponse
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_strategies_returns_list_of_strings(client):
    """La réponse est un JSON array de strings (response_model=list[str])."""
    await _register_and_login(client, "user1@test.com")
    resp = await client.get("/api/v1/schools/strategies")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all(isinstance(item, str) for item in data), (
        f"Tous les éléments doivent être des strings, reçu : {data!r}"
    )


@pytest.mark.asyncio
async def test_strategies_contains_all_five_registered_scrapers(client):
    """La liste contient les 5 scrapers enregistrés dans app/scrapers/."""
    await _register_and_login(client, "user2@test.com")
    resp = await client.get("/api/v1/schools/strategies")
    assert resp.status_code == 200
    names = resp.json()

    expected = {"stub", "SCAP", "ORSYS", "Cegos", "Demos"}
    missing = expected - set(names)
    assert not missing, f"Scrapers manquants dans la réponse : {missing} (reçu : {names})"

    # Et on a bien 5 entrées (pas plus, pas moins via l'API)
    assert len(names) == 5, f"Attendu 5 scrapers, reçu {len(names)} : {names}"


@pytest.mark.asyncio
async def test_strategies_is_sorted_alphabetically(client):
    """L'API retourne sorted(list_scrapers()) — l'endpoint applique le tri."""
    await _register_and_login(client, "user3@test.com")
    resp = await client.get("/api/v1/schools/strategies")
    assert resp.status_code == 200
    names = resp.json()

    assert names == sorted(names), (
        f"La liste doit être triée alphabétiquement. Reçu : {names}"
    )
