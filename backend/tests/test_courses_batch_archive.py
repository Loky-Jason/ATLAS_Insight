"""Archivage par lot (Phase 2.4).

Contrats vérifiés : `specs/batch-archive.md`. `docs/SPEC.md` §5 classe
l'archivage massif parmi les actions destructives : confirmation + AuditLog.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.course import Course
from app.models.user import User

BATCH_URL = "/api/v1/courses/archive-batch"


async def _register_and_login(client, email: str, password: str = "validpass1") -> None:
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    await client.post("/api/v1/auth/login", json={"email": email, "password": password})


async def _make_courses(db_session, count: int, status: str = "active") -> list[int]:
    """Commit et pas flush : une requête refusée (403) déclenche le rollback de
    `get_db`, qui annulerait des données seulement flushées."""
    courses = [
        Course(title=f"Cours {i}", status=status, enrolled_count=0, dropout_count=0)
        for i in range(count)
    ]
    db_session.add_all(courses)
    await db_session.commit()
    return [course.id for course in courses]


async def _demote_to_user(db_session, email: str) -> None:
    """Le premier compte créé est admin (bootstrap) : on le rétrograde."""
    result = await db_session.execute(select(User).where(User.email == email))
    user = result.scalar_one()
    user.role = "user"
    await db_session.commit()


async def _statuses(db_session, ids: list[int]) -> dict[int, str]:
    result = await db_session.execute(select(Course).where(Course.id.in_(ids)))
    return {course.id: course.status for course in result.scalars().all()}


async def _audit_targets(db_session, action: str) -> list[str]:
    result = await db_session.execute(select(AuditLog).where(AuditLog.action == action))
    return [log.target for log in result.scalars().all()]


# ---------------------------------------------------------------------------
# Cas nominal
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_batch_archives_active_courses(client, db_session):
    await _register_and_login(client, "admin@test.com")
    ids = await _make_courses(db_session, 3)

    resp = await client.post(BATCH_URL, json={"course_ids": ids})

    assert resp.status_code == 200
    assert resp.json() == {"archived": sorted(ids), "skipped": [], "not_found": []}
    assert set((await _statuses(db_session, ids)).values()) == {"archived"}


@pytest.mark.asyncio
async def test_batch_writes_one_audit_log_per_course(client, db_session):
    """Traçabilité individuelle : « qui a archivé ce cours-là », pas « un lot a eu lieu »."""
    await _register_and_login(client, "admin@test.com")
    ids = await _make_courses(db_session, 3)

    await client.post(BATCH_URL, json={"course_ids": ids})

    targets = await _audit_targets(db_session, "archive_course")
    assert sorted(targets) == sorted(f"course:{i}" for i in ids)


# ---------------------------------------------------------------------------
# Réponse partielle
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_batch_reports_skipped_and_not_found(client, db_session):
    """Un id inconnu ou un cours déjà archivé n'annule pas le reste."""
    await _register_and_login(client, "admin@test.com")
    active = await _make_courses(db_session, 2)
    already = await _make_courses(db_session, 1, status="archived")

    resp = await client.post(
        BATCH_URL, json={"course_ids": active + already + [9999]}
    )

    assert resp.status_code == 200
    assert resp.json() == {
        "archived": sorted(active),
        "skipped": already,
        "not_found": [9999],
    }


@pytest.mark.asyncio
async def test_batch_does_not_relog_already_archived(client, db_session):
    await _register_and_login(client, "admin@test.com")
    already = await _make_courses(db_session, 2, status="archived")

    await client.post(BATCH_URL, json={"course_ids": already})

    assert await _audit_targets(db_session, "archive_course") == []


@pytest.mark.asyncio
async def test_batch_is_idempotent(client, db_session):
    """Rejouer le lot n'archive rien de plus et n'écrit aucun journal."""
    await _register_and_login(client, "admin@test.com")
    ids = await _make_courses(db_session, 3)
    await client.post(BATCH_URL, json={"course_ids": ids})

    resp = await client.post(BATCH_URL, json={"course_ids": ids})

    assert resp.json() == {"archived": [], "skipped": sorted(ids), "not_found": []}
    assert len(await _audit_targets(db_session, "archive_course")) == len(ids)


# ---------------------------------------------------------------------------
# Sécurité
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_batch_requires_admin(client, db_session):
    await _register_and_login(client, "admin@test.com")
    ids = await _make_courses(db_session, 2)
    await _demote_to_user(db_session, "admin@test.com")

    resp = await client.post(BATCH_URL, json={"course_ids": ids})

    assert resp.status_code == 403
    # Aucun effet de bord.
    assert set((await _statuses(db_session, ids)).values()) == {"active"}
    assert await _audit_targets(db_session, "archive_course") == []


@pytest.mark.asyncio
async def test_batch_requires_authentication(client):
    resp = await client.post(BATCH_URL, json={"course_ids": [1]})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_batch_rejects_empty_list(client):
    await _register_and_login(client, "admin@test.com")
    resp = await client.post(BATCH_URL, json={"course_ids": []})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_batch_rejects_oversized_list(client):
    """Borne dure : pas de transaction géante sur SQLite."""
    await _register_and_login(client, "admin@test.com")
    resp = await client.post(BATCH_URL, json={"course_ids": list(range(1, 202))})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_batch_accepts_maximum_size(client):
    await _register_and_login(client, "admin@test.com")
    resp = await client.post(BATCH_URL, json={"course_ids": list(range(1, 201))})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_batch_rejects_duplicate_ids(client, db_session):
    """Un doublon fausserait le décompte rendu à l'utilisateur."""
    await _register_and_login(client, "admin@test.com")
    ids = await _make_courses(db_session, 1)

    resp = await client.post(BATCH_URL, json={"course_ids": ids + ids})

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Non-régression
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_single_archive_still_works(client, db_session):
    await _register_and_login(client, "admin@test.com")
    ids = await _make_courses(db_session, 1)

    resp = await client.post(f"/api/v1/courses/{ids[0]}/archive")

    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"


@pytest.mark.asyncio
async def test_batch_bumps_updated_at(client, db_session):
    """Contrat avec la page Archives, qui affiche `updated_at` comme date d'archivage.

    Repose sur `onupdate` du modèle : sans ce test, le retirer casserait la
    colonne « Dernière modification » sans qu'aucune suite ne le signale.
    """
    await _register_and_login(client, "admin@test.com")
    ids = await _make_courses(db_session, 1)
    result = await db_session.execute(select(Course).where(Course.id == ids[0]))
    course = result.scalar_one()
    before = course.updated_at

    await client.post(BATCH_URL, json={"course_ids": ids})
    await db_session.refresh(course)

    assert course.updated_at > before


@pytest.mark.asyncio
async def test_batch_rejects_non_positive_ids(client):
    """Un identifiant nul ou négatif n'existe pas : le refuser plutôt que le
    faire remonter en `not_found`."""
    await _register_and_login(client, "admin@test.com")
    resp = await client.post(BATCH_URL, json={"course_ids": [0]})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_batch_route_not_shadowed_by_course_id_route(client, db_session):
    """`archive-batch` ne doit pas être capté par `/{course_id}/archive`."""
    await _register_and_login(client, "admin@test.com")
    ids = await _make_courses(db_session, 1)

    resp = await client.post(BATCH_URL, json={"course_ids": ids})

    assert resp.status_code == 200
    assert resp.json()["archived"] == ids
