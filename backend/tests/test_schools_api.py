"""Tests — endpoint `POST /api/v1/schools/test-connection` (test de connexion).

Couvre :
- Accès non auth → 401
- User non-admin → 403
- Succès (2xx) → {"success": True}
- Timeout → message FR « La connexion a expiré (10s). »
- HTTP error → « Erreur HTTP {status}. »
- RequestError → « Impossible de se connecter : ... »
- Exception inattendue → message générique
- Validation URL invalide → 422
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_and_login(
    client, email: str, password: str = "validpass1"
) -> None:
    """Crée un compte puis ouvre la session (cookie httpOnly posé par /auth/login)."""
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    await client.post("/api/v1/auth/login", json={"email": email, "password": password})


def _mock_async_client(get_side_effect=None, resp_status: int = 200):
    """Construit un mock asynchrone d'httpx.AsyncClient() pour patch.

    Utilise ``AsyncMock`` pour que ``__aenter__`` et ``client.get``
    retournent des coroutines compatibles avec ``await``.

    Returns
    -------
    AsyncMock
        Instance à passer comme ``return_value`` de ``patch("httpx.AsyncClient")``.
    """
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None

    if get_side_effect is not None:
        client.get.side_effect = get_side_effect
    else:
        resp = MagicMock()
        resp.status_code = resp_status
        resp.raise_for_status.return_value = None
        client.get.return_value = resp

    return client


# ===================================================================
# Contrôle d'accès
# ===================================================================


@pytest.mark.asyncio
async def test_connection_unauthenticated_returns_401(client):
    """Sans cookie d'accès → 401."""
    resp = await client.post(
        "/api/v1/schools/test-connection",
        json={"url": "https://example.com"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_connection_regular_user_returns_403(client):
    """Un user normal (non-admin) → 403 (require_admin)."""
    # Premier compte = admin bootstrap
    await _register_and_login(client, "admin@test.com")
    await client.post("/api/v1/auth/logout")

    # Second compte = user forcé
    await _register_and_login(client, "user@test.com")
    resp = await client.post(
        "/api/v1/schools/test-connection",
        json={"url": "https://example.com"},
    )
    assert resp.status_code == 403


# ===================================================================
# Cas nominaux et erreurs HTTP
# ===================================================================


@pytest.mark.asyncio
async def test_connection_success(client):
    """URL répondant 200 → {"success": True}."""
    await _register_and_login(client, "admin@test.com")

    mock_client = _mock_async_client(resp_status=200)
    with patch("httpx.AsyncClient", return_value=mock_client):
        resp = await client.post(
            "/api/v1/schools/test-connection",
            json={"url": "https://example.com"},
        )

    assert resp.status_code == 200
    assert resp.json() == {"success": True}


@pytest.mark.asyncio
async def test_connection_timeout(client):
    """httpx.TimeoutException → message FR « La connexion a expiré (10s). »"""
    await _register_and_login(client, "admin@test.com")

    mock_client = _mock_async_client(
        get_side_effect=httpx.TimeoutException("timeout", request=MagicMock()),
    )
    with patch("httpx.AsyncClient", return_value=mock_client):
        resp = await client.post(
            "/api/v1/schools/test-connection",
            json={"url": "https://example.com"},
        )

    assert resp.status_code == 200
    assert resp.json() == {
        "success": False,
        "error_msg": "La connexion a expiré (10s).",
    }


@pytest.mark.asyncio
async def test_connection_http_error(client):
    """HTTP 503 → message « Erreur HTTP 503. »"""
    await _register_and_login(client, "admin@test.com")

    mock_resp = MagicMock()
    mock_resp.status_code = 503
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "HTTP 503",
        request=MagicMock(),
        response=mock_resp,
    )

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get.return_value = mock_resp

    with patch("httpx.AsyncClient", return_value=mock_client):
        resp = await client.post(
            "/api/v1/schools/test-connection",
            json={"url": "https://example.com"},
        )

    assert resp.status_code == 200
    assert resp.json() == {
        "success": False,
        "error_msg": "Erreur HTTP 503.",
    }


@pytest.mark.asyncio
async def test_connection_request_error(client):
    """Erreur de connexion (DNS/refus) → « Impossible de se connecter : ... »"""
    await _register_and_login(client, "admin@test.com")

    mock_client = _mock_async_client(
        get_side_effect=httpx.RequestError(
            "Connection refused", request=MagicMock()
        ),
    )
    with patch("httpx.AsyncClient", return_value=mock_client):
        resp = await client.post(
            "/api/v1/schools/test-connection",
            json={"url": "https://example.com"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "Impossible de se connecter" in data["error_msg"]
    assert "Connection refused" in data["error_msg"]


@pytest.mark.asyncio
async def test_connection_unexpected_exception(client):
    """Exception non-httpx → message générique « Erreur inattendue lors du test. »"""
    await _register_and_login(client, "admin@test.com")

    mock_client = _mock_async_client(get_side_effect=ValueError("something broke"))
    with patch("httpx.AsyncClient", return_value=mock_client):
        resp = await client.post(
            "/api/v1/schools/test-connection",
            json={"url": "https://example.com"},
        )

    assert resp.status_code == 200
    assert resp.json() == {
        "success": False,
        "error_msg": "Erreur inattendue lors du test.",
    }


# ===================================================================
# Validation Pydantic (via validate_external_url)
# ===================================================================


@pytest.mark.asyncio
async def test_connection_invalid_scheme_returns_422(client):
    """Schéma non http/https → 422."""
    await _register_and_login(client, "admin@test.com")
    resp = await client.post(
        "/api/v1/schools/test-connection",
        json={"url": "ftp://example.com"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_connection_localhost_returns_422(client):
    """Hôte localhost → 422."""
    await _register_and_login(client, "admin@test.com")
    resp = await client.post(
        "/api/v1/schools/test-connection",
        json={"url": "http://localhost:8080/test"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_connection_private_ip_returns_422(client):
    """IP privée (10.x.x.x) → 422."""
    await _register_and_login(client, "admin@test.com")
    resp = await client.post(
        "/api/v1/schools/test-connection",
        json={"url": "http://10.0.0.1/test"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_connection_empty_url_returns_422(client):
    """URL vide → 422."""
    await _register_and_login(client, "admin@test.com")
    resp = await client.post(
        "/api/v1/schools/test-connection",
        json={"url": ""},
    )
    assert resp.status_code == 422
