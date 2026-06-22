"""Tests auth : register + login."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_register_success(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "alice@example.com", "password": "supersecret1", "role": "user"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "alice@example.com"
    assert data["role"] == "user"
    assert "id" in data
    # Le hash ne doit jamais être exposé
    assert "password_hash" not in data
    assert "password" not in data


@pytest.mark.asyncio
async def test_register_duplicate(client):
    payload = {"email": "bob@example.com", "password": "supersecret1", "role": "user"}
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_short_password(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "carol@example.com", "password": "abc", "role": "user"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "dave@example.com", "password": "validpass1", "role": "user"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "dave@example.com", "password": "validpass1"},
    )
    assert resp.status_code == 200
    # Le cookie httpOnly doit être posé
    assert "access_token" in resp.cookies


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "eve@example.com", "password": "validpass1", "role": "user"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "eve@example.com", "password": "wrongpass"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_unauthenticated(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_authenticated(client):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "frank@example.com", "password": "validpass1", "role": "user"},
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
        json={"email": "grace@example.com", "password": "validpass1", "role": "user"},
    )
    await client.post(
        "/api/v1/auth/login",
        json={"email": "grace@example.com", "password": "validpass1"},
    )
    resp = await client.post("/api/v1/auth/logout")
    assert resp.status_code == 204
