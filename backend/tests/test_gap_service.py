"""Tests Phase 1c — gap_service.

Couvre les bugs latents corrigés non vus par les autres suites :
  - B1 : les recommandations "creation" ne s'écrasent plus en une seule ligne
         (clé d'identité `creation_key`) + idempotence sur ré-analyse.
  - B2 : comparaison de dates tz-safe (naïf SQLite vs aware) ne lève pas.
  - B3 : reject_recommendation change le statut et crée un AuditLog.
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.models.course import Course
from app.models.course_proposal import CourseProposal
from app.models.gap_recommendation import GapRecommendation
from app.models.school_course import SchoolCourse
from app.models.school_registry import SchoolRegistry
from app.services import gap_service


async def _seed_two_creation_clusters(db) -> None:
    """1 cours SCAP + 2 SchoolCourse à titres distincts et éloignés de SCAP.

    → 2 clusters de création attendus (aucun équivalent SCAP).
    """
    db.add(Course(title="Comptabilité publique", status="active", category="Gestion"))

    school = SchoolRegistry(
        name="École Pro Test", url="https://ecole-test.example", scraper_strategy="stub"
    )
    db.add(school)
    await db.flush()

    db.add_all(
        [
            SchoolCourse(
                school_registry_id=school.id,
                external_id="A1",
                title="Charpente bois",
                category="Artisanat",
            ),
            SchoolCourse(
                school_registry_id=school.id,
                external_id="B1",
                title="Sophrologie",
                category="Bien-être",
            ),
        ]
    )
    await db.flush()


@pytest.mark.asyncio
async def test_creation_recommendations_do_not_collapse(db_session):
    """B1 : deux opportunités de création → deux lignes distinctes."""
    await _seed_two_creation_clusters(db_session)

    result = await gap_service.run_gap_analysis(db_session)

    assert len(result["creation"]) == 2, "chaque cluster doit produire sa recommandation"

    count = await db_session.scalar(
        select(func.count(GapRecommendation.id)).where(
            GapRecommendation.recommendation_type == "creation"
        )
    )
    assert count == 2

    keys = await db_session.scalars(
        select(GapRecommendation.creation_key).where(
            GapRecommendation.recommendation_type == "creation"
        )
    )
    assert all(k for k in keys.all()), "creation_key doit être renseigné (idempotence)"


@pytest.mark.asyncio
async def test_creation_analysis_is_idempotent(db_session):
    """B1 : ré-analyse ne duplique pas les recommandations (upsert par clé)."""
    await _seed_two_creation_clusters(db_session)

    await gap_service.run_gap_analysis(db_session)
    await gap_service.run_gap_analysis(db_session)  # second passage

    count = await db_session.scalar(
        select(func.count(GapRecommendation.id)).where(
            GapRecommendation.recommendation_type == "creation"
        )
    )
    assert count == 2, "le second passage doit mettre à jour, pas dupliquer"


@pytest.mark.asyncio
async def test_gap_analysis_runs_without_tz_error(db_session):
    """B2 : aucune TypeError naïf/aware lors de la passe création."""
    await _seed_two_creation_clusters(db_session)
    # Ne doit pas lever (comparaison first_seen_at >= cutoff_30d normalisée UTC).
    summary = await gap_service.run_gap_analysis(db_session)
    assert "closure" in summary and "creation" in summary


# ---------------------------------------------------------------------------
# B3 — reject_recommendation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reject_recommendation_success(db_session):
    """B3 : reject_recommendation → status='rejected' + AuditLog créé."""
    rec = GapRecommendation(
        recommendation_type="closure",
        score=80.0,
        status="draft",
        rationale="Test reject",
    )
    db_session.add(rec)
    await db_session.flush()
    rec_id = rec.id

    result = await gap_service.reject_recommendation(db_session, rec_id, user_id=1)

    assert result == {"id": rec_id, "type": "closure", "status": "rejected"}

    # Vérifie le statut en base
    await db_session.refresh(rec)
    assert rec.status == "rejected"

    # Vérifie l'AuditLog
    from app.models.audit_log import AuditLog

    stmt = select(AuditLog).where(AuditLog.action == "reject_recommendation")
    audit_result = await db_session.execute(stmt)
    logs = audit_result.scalars().all()
    assert len(logs) == 1
    assert logs[0].user_id == 1
    assert logs[0].target == f"gap_recommendation:{rec_id}:closure"


@pytest.mark.asyncio
async def test_reject_recommendation_not_found(db_session):
    """B3 : id inexistant → ValueError."""
    with pytest.raises(ValueError, match="Recommandation.*introuvable"):
        await gap_service.reject_recommendation(db_session, rec_id=99999, user_id=1)


# ---------------------------------------------------------------------------
# Approve recommendation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approve_creation_creates_proposal(db_session):
    """approve_recommendation creation → CourseProposal brouillon + AuditLog."""
    rec = GapRecommendation(
        recommendation_type="creation",
        score=75.0,
        status="draft",
        rationale="Formation IA générative",
        suggested_hours=21.0,
        certification_suggestions='["Certif IA"]',
        score_breakdown='{"representative_title": "IA Générative", "weighted_score": 0.75}',
    )
    db_session.add(rec)
    await db_session.flush()
    rec_id = rec.id

    result = await gap_service.approve_recommendation(db_session, rec_id, user_id=2)

    assert result == {
        "id": rec_id,
        "type": "creation",
        "status": "approved",
        "action": "created_proposal_1",
    }

    await db_session.refresh(rec)
    assert rec.status == "approved"

    proposal_result = await db_session.execute(select(CourseProposal))
    proposals = proposal_result.scalars().all()
    assert len(proposals) == 1
    assert proposals[0].title == "IA Générative"
    assert proposals[0].status == "draft"
    assert proposals[0].hours_estimated == 21.0

    from app.models.audit_log import AuditLog

    stmt = select(AuditLog).where(AuditLog.action == "approve_recommendation")
    audit_result = await db_session.execute(stmt)
    logs = audit_result.scalars().all()
    assert len(logs) == 1
    assert logs[0].user_id == 2
    assert logs[0].target == f"gap_recommendation:{rec_id}:creation"


@pytest.mark.asyncio
async def test_approve_closure_archives_course(db_session):
    """approve_recommendation closure → cours SCAP archivé + AuditLog."""
    course = Course(title="Cours à fermer", status="active", category="Test")
    db_session.add(course)
    await db_session.flush()

    rec = GapRecommendation(
        recommendation_type="closure",
        score=90.0,
        status="draft",
        rationale="Cours obsolète",
        scap_course_id=course.id,
    )
    db_session.add(rec)
    await db_session.flush()
    rec_id = rec.id

    result = await gap_service.approve_recommendation(db_session, rec_id, user_id=3)

    assert result["id"] == rec_id
    assert result["type"] == "closure"
    assert result["status"] == "approved"
    assert result["action"] == f"archived_course_{course.id}"

    await db_session.refresh(rec)
    await db_session.refresh(course)
    assert rec.status == "approved"
    assert course.status == "archived"

    from app.models.audit_log import AuditLog

    stmt = select(AuditLog).where(AuditLog.action == "approve_recommendation")
    audit_result = await db_session.execute(stmt)
    logs = audit_result.scalars().all()
    assert len(logs) == 1
    assert logs[0].user_id == 3
    assert logs[0].target == f"gap_recommendation:{rec_id}:closure"


@pytest.mark.asyncio
async def test_approve_recommendation_not_found(db_session):
    """approve_recommendation id inexistant → ValueError."""
    with pytest.raises(ValueError, match="Recommandation.*introuvable"):
        await gap_service.approve_recommendation(db_session, rec_id=99999, user_id=1)


@pytest.mark.asyncio
async def test_approve_recommendation_non_draft_raises(db_session):
    """approve_recommendation sur statut non draft → ValueError."""
    rec = GapRecommendation(
        recommendation_type="creation",
        score=50.0,
        status="rejected",
        rationale="Déjà rejetée",
    )
    db_session.add(rec)
    await db_session.flush()

    with pytest.raises(ValueError, match="n'est pas modifiable"):
        await gap_service.approve_recommendation(db_session, rec.id, user_id=1)


@pytest.mark.asyncio
async def test_reject_recommendation_non_draft_raises(db_session):
    """reject_recommendation sur statut non draft → ValueError."""
    rec = GapRecommendation(
        recommendation_type="closure",
        score=50.0,
        status="approved",
        rationale="Déjà approuvée",
    )
    db_session.add(rec)
    await db_session.flush()

    with pytest.raises(ValueError, match="n'est pas modifiable"):
        await gap_service.reject_recommendation(db_session, rec.id, user_id=1)
