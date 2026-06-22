"""Tests auth : register + login + sécurité."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_register_first_user_becomes_admin(client):
    """Premier compte créé → rôle admin (bootstrap E1)."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "alice@example.com", "password": "supersecret1"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "alice@example.com"
    assert data["role"] == "admin"  # bootstrap : premier compte = admin
    assert "id" in data
    assert "password_hash" not in data
    assert "password" not in data


@pytest.mark.asyncio
async def test_register_subsequent_user_forced_role_user(client):
    """Les comptes suivants reçoivent 'user' même si le client envoie role=admin (E1)."""
    # Premier compte (admin bootstrap)
    await client.post(
        "/api/v1/auth/register",
        json={"email": "first@example.com", "password": "supersecret1"},
    )
    # Deuxième compte — role envoyé (ignoré par le schéma, forcé à 'user' côté serveur)
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "second@example.com", "password": "supersecret1", "role": "admin"},
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "user"


@pytest.mark.asyncio
async def test_register_duplicate(client):
    payload = {"email": "bob@example.com", "password": "supersecret1"}
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_short_password(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "carol@example.com", "password": "abc"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "dave@example.com", "password": "validpass1"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "dave@example.com", "password": "validpass1"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.cookies


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "eve@example.com", "password": "validpass1"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "eve@example.com", "password": "wrongpass"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email_returns_401(client):
    """Email inexistant doit renvoyer 401 (pas de fuite d'énumération) (E2)."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@example.com", "password": "somepassword"},
    )
    assert resp.status_code == 401
    # Même message que mot de passe incorrect — pas d'énumération
    assert "incorrect" in resp.json()["detail"].lower() or "incorrect" in resp.text.lower()


@pytest.mark.asyncio
async def test_me_unauthenticated(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_authenticated(client):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "frank@example.com", "password": "validpass1"},
    )
    await client.post(
        "/api/v1/auth/login",
        json={"email": "frank@example.com", "password": "validpass1"},
    )
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "frank@example.com"


@pytest.mark.asyncio
async def test_logout(client):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "grace@example.com", "password": "validpass1"},
    )
    await client.post(
        "/api/v1/auth/login",
        json={"email": "grace@example.com", "password": "validpass1"},
    )
    resp = await client.post("/api/v1/auth/logout")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_require_admin_rejects_regular_user(client):
    """Un user normal accédant à une route admin doit recevoir 403 (E1)."""
    # Premier compte = admin bootstrap
    await client.post(
        "/api/v1/auth/register",
        json={"email": "admin@example.com", "password": "validpass1"},
    )
    # Second compte = user forcé
    await client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "validpass1"},
    )
    # Login en tant que user normal
    await client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "validpass1"},
    )
    # Tenter d'accéder à une route admin
    resp = await client.post("/api/v1/analytics/refresh-scores")
    assert resp.status_code == 403
