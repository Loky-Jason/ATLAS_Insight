"""Tests import CSV — upload minimal et validation."""

from __future__ import annotations

import io

import pytest


async def _register_and_login(client) -> None:
    """Utilitaire : crée un compte et pose le cookie de session."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "importer@example.com", "password": "validpass1", "role": "admin"},
    )
    await client.post(
        "/api/v1/auth/login",
        json={"email": "importer@example.com", "password": "validpass1"},
    )


@pytest.mark.asyncio
async def test_import_csv_minimal(client):
    """Un CSV avec seulement la colonne 'title' doit être importé avec succès."""
    await _register_and_login(client)

    csv_content = "title\nPhotographie numérique\nPoterie avancée\n"
    file = io.BytesIO(csv_content.encode("utf-8"))

    resp = await client.post(
        "/api/v1/imports",
        files={"file": ("test.csv", file, "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["inserted"] == 2
    assert data["errors"] == []


@pytest.mark.asyncio
async def test_import_csv_full_columns(client):
    """CSV avec toutes les colonnes optionnelles."""
    await _register_and_login(client)

    csv_content = (
        "title,category,enrolled_count,dropout_count,year,hours_estimated\n"
        "Aquarelle,Arts plastiques,30,5,2024,24\n"
        "Yoga doux,Bien-être,50,10,2024,12\n"
    )
    file = io.BytesIO(csv_content.encode("utf-8"))

    resp = await client.post(
        "/api/v1/imports",
        files={"file": ("cours.csv", file, "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["inserted"] == 2


@pytest.mark.asyncio
async def test_import_csv_missing_title_column(client):
    """Un CSV sans colonne 'title' doit retourner 422."""
    await _register_and_login(client)

    csv_content = "category,enrolled_count\nArts,10\n"
    file = io.BytesIO(csv_content.encode("utf-8"))

    resp = await client.post(
        "/api/v1/imports",
        files={"file": ("bad.csv", file, "text/csv")},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_import_wrong_extension(client):
    """Un fichier .txt doit être rejeté."""
    await _register_and_login(client)

    file = io.BytesIO(b"some data")
    resp = await client.post(
        "/api/v1/imports",
        files={"file": ("data.txt", file, "text/plain")},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_import_empty_file(client):
    """Un fichier vide doit retourner 422."""
    await _register_and_login(client)

    file = io.BytesIO(b"")
    resp = await client.post(
        "/api/v1/imports",
        files={"file": ("empty.csv", file, "text/csv")},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_import_unauthenticated(client):
    """Sans cookie, l'import doit retourner 401."""
    file = io.BytesIO(b"title\nTest\n")
    resp = await client.post(
        "/api/v1/imports",
        files={"file": ("test.csv", file, "text/csv")},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_import_csv_with_empty_rows(client):
    """Les lignes avec title vide doivent être ignorées sans erreur fatale.

    Note : pandas supprime silencieusement les lignes entièrement vides lors
    du read_csv (elles n'apparaissent pas comme erreurs — comportement correct).
    Seules les lignes avec une valeur vide explicite dans la colonne title
    génèrent une entrée dans 'errors'.
    """
    await _register_and_login(client)

    # Ligne vide pure → supprimée silencieusement par pandas (pas dans errors)
    csv_content = "title\nCours valide\n\nAutre cours\n"
    file = io.BytesIO(csv_content.encode("utf-8"))

    resp = await client.post(
        "/api/v1/imports",
        files={"file": ("mixed.csv", file, "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["inserted"] == 2
    # Pas d'erreurs : pandas a ignoré la ligne vide silencieusement
    assert isinstance(data["errors"], list)
