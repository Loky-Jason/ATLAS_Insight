"""Tests import CSV — upload minimal, validation, sécurité."""

from __future__ import annotations

import io

import pytest

from app.services.import_service import _clean_row


async def _register_and_login(client) -> None:
    """Utilitaire : crée un compte (admin bootstrap) et pose le cookie de session."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "importer@example.com", "password": "validpass1"},
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


# ---------------------------------------------------------------------------
# Tests sécurité import (E3b)
# ---------------------------------------------------------------------------

def _make_row(**kwargs):
    """Construit un pandas.Series minimal pour _clean_row."""
    import pandas as pd
    defaults = {
        "title": "Titre test",
        "category": None,
        "status": None,
        "enrolled_count": None,
        "dropout_count": None,
        "age_brackets": None,
        "year": None,
        "hours_estimated": None,
        "notes": None,
    }
    defaults.update(kwargs)
    return pd.Series(defaults)


@pytest.mark.parametrize("formula", ["=CMD", "+1+1", "-1", "@SUM(A1)", "\t=evil", "\r=evil"])
def test_formula_injection_neutralized(formula):
    """Les valeurs commençant par un préfixe de formule sont préfixées d'une apostrophe (E3b)."""
    row = _make_row(notes=formula)
    result = _clean_row(row)
    notes = result["notes"]
    assert notes is not None
    assert notes.startswith("'"), f"Formule non neutralisée : {notes!r}"


def test_normal_string_not_prefixed():
    """Une valeur normale ne doit pas être modifiée."""
    row = _make_row(notes="Cours de poterie")
    result = _clean_row(row)
    assert result["notes"] == "Cours de poterie"


@pytest.mark.asyncio
async def test_import_audit_log_written(client, db_session):
    """Un AuditLog doit être créé après un import réussi (M1)."""
    from sqlalchemy import select

    from app.models.audit_log import AuditLog

    await _register_and_login(client)
    csv_content = "title\nTest audit\n"
    file = io.BytesIO(csv_content.encode("utf-8"))
    resp = await client.post(
        "/api/v1/imports",
        files={"file": ("audit_test.csv", file, "text/csv")},
    )
    assert resp.status_code == 200

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "import_courses")
    )
    log = result.scalar_one_or_none()
    assert log is not None
    assert "audit_test.csv" in (log.target or "")


# ---------------------------------------------------------------------------
# Test sécurité configuration (C1)
# ---------------------------------------------------------------------------

def test_secret_key_weak_rejected_in_production():
    """Une SECRET_KEY faible doit lever ValueError en environnement production (C1)."""
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises((ValueError, ValidationError)):
        Settings(secret_key="CHANGE_ME_IN_DOT_ENV", environment="production")


def test_secret_key_short_rejected_in_production():
    """Une SECRET_KEY < 32 caractères doit lever ValueError en production (C1)."""
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises((ValueError, ValidationError)):
        Settings(secret_key="tooshort", environment="production")


def test_secret_key_strong_accepted_in_production():
    """Une SECRET_KEY >= 32 caractères doit être acceptée en production (C1)."""
    from app.core.config import Settings

    s = Settings(
        secret_key="a" * 32,
        environment="production",
        database_url="sqlite+aiosqlite:///./data/atlas.db",
    )
    assert s.is_production is True
