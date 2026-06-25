"""Tests Phase 1c — gap_service.

Couvre les bugs latents corrigés non vus par les autres suites :
  - B1 : les recommandations "creation" ne s'écrasent plus en une seule ligne
         (clé d'identité `creation_key`) + idempotence sur ré-analyse.
  - B2 : comparaison de dates tz-safe (naïf SQLite vs aware) ne lève pas.
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.models.course import Course
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
