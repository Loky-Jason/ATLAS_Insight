"""Gap analysis service — Phase 1c.

Détection d'écarts entre l'offre SCAP et le marché concurrentiel.
Deux passes :
  1. Closure  : cours SCAP menacés par l'offre concurrente.
  2. Creation : formations marché non couvertes par SCAP.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.db import AsyncSession
from app.models.audit_log import AuditLog
from app.models.course import Course
from app.models.course_proposal import CourseProposal
from app.models.gap_recommendation import GapRecommendation
from app.models.school_course import SchoolCourse
from app.services.certification_service import suggest_certifications
from app.services.estimation_service import estimate_hours

logger = logging.getLogger(__name__)

# Seuil de similarité titre pour considérer deux cours comme liés
_SIMILARITY_THRESHOLD = 0.35

# Seuil de score (0–100) pour créer une recommandation
_SCORE_THRESHOLD = 40


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"\w+")


def _token_set(text: str) -> set[str]:
    """Mots normalisés (minuscules) d'une chaîne."""
    return set(_WORD_RE.findall(text.lower()))


def _token_similarity(tokens_a: set[str], tokens_b: set[str]) -> float:
    """Similarité Dice entre deux ensembles de tokens."""
    if not tokens_a and not tokens_b:
        return 1.0
    if not tokens_a or not tokens_b:
        return 0.0
    common = len(tokens_a & tokens_b)
    return 2.0 * common / (len(tokens_a) + len(tokens_b))


def _compute_similarity(a: str, b: str) -> float:
    """Similarité [0,1] par recouvrement de tokens (rapport de Sørensen–Dice).

    Plus rapide que SequenceMatcher sur des titres de cours tout en
    conservant un seuil de 0.35 comparable.
    """
    tokens_a = _token_set(a)
    tokens_b = _token_set(b)
    if not tokens_a and not tokens_b:
        return 1.0
    if not tokens_a or not tokens_b:
        return 0.0
    common = len(tokens_a & tokens_b)
    return 2.0 * common / (len(tokens_a) + len(tokens_b))


def _as_utc(dt: datetime | None) -> datetime | None:
    """Normalise un datetime en aware UTC.

    SQLite/aiosqlite renvoie des datetimes naïfs, Postgres des aware : on
    uniformise pour éviter `TypeError: can't compare naive and aware`.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _cluster_school_courses(
    courses: list[SchoolCourse],
) -> list[tuple[SchoolCourse, set[str], int]]:
    """Regroupe les SchoolCourse par similarité de titre (> seuil).

    Retourne une liste de : (représentant, {noms écoles}, nb_écoles).
    Le représentant est le cours avec la meilleure similarité moyenne au cluster.
    """
    n = len(courses)
    if n == 0:
        return []

    # Précalcule les tokens pour éviter de les recalculer à chaque comparaison
    tokens = [_token_set(c.title) for c in courses]
    assigned = [False] * n
    clusters: list[list[int]] = []

    for i in range(n):
        if assigned[i]:
            continue
        cluster = [i]
        assigned[i] = True
        for j in range(i + 1, n):
            if assigned[j]:
                continue
            # Vérifie la similarité avec n'importe quel membre déjà dans le cluster
            if any(
                _token_similarity(tokens[k], tokens[j]) > _SIMILARITY_THRESHOLD
                for k in cluster
            ):
                cluster.append(j)
                assigned[j] = True
        clusters.append(cluster)

    results: list[tuple[SchoolCourse, set[str], int]] = []
    for cluster in clusters:
        if not cluster:  # ne devrait pas arriver
            continue

        # Meilleur score de similarité moyenne → représentant (centroïde)
        best_idx = cluster[0]
        best_avg = -1.0
        for idx in cluster:
            others = [j for j in cluster if j != idx]
            if not others:
                avg = 1.0
            else:
                avg = sum(
                    _token_similarity(tokens[idx], tokens[o])
                    for o in others
                ) / len(others)
            if avg > best_avg:
                best_avg = avg
                best_idx = idx

        rep = courses[best_idx]

        # Noms d'écoles distincts
        schools: set[str] = set()
        for idx in cluster:
            sc = courses[idx]
            if sc.school_registry and sc.school_registry.name:
                schools.add(sc.school_registry.name)

        results.append((rep, schools, len(schools)))

    return results


async def _upsert_recommendation(
    db: AsyncSession,
    rec_type: str,
    scap_course_id: int | None,
    market_course_id: int | None,
    score: float,
    score_breakdown: str | None = None,
    schools_offering: str | None = None,
    suggested_hours: float | None = None,
    certification_suggestions: str | None = None,
    rationale: str | None = None,
    creation_key: str | None = None,
) -> GapRecommendation:
    """Crée ou met à jour une recommandation existante.

    Identité d'upsert : `scap_course_id` (closure) ou `creation_key`
    (creation). Sans discriminant, on insère systématiquement (pas d'upsert)
    pour éviter un `MultipleResultsFound` sur un filtre trop large.
    """
    stmt = select(GapRecommendation).where(
        GapRecommendation.recommendation_type == rec_type,
    )
    has_discriminator = False
    if scap_course_id is not None:
        stmt = stmt.where(GapRecommendation.scap_course_id == scap_course_id)
        has_discriminator = True
    if market_course_id is not None:
        stmt = stmt.where(GapRecommendation.market_course_id == market_course_id)
        has_discriminator = True
    if creation_key is not None:
        stmt = stmt.where(GapRecommendation.creation_key == creation_key)
        has_discriminator = True

    existing = None
    if has_discriminator:
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

    if existing:
        existing.score = score
        existing.score_breakdown = score_breakdown
        existing.schools_offering = schools_offering
        existing.suggested_hours = suggested_hours
        existing.certification_suggestions = certification_suggestions
        existing.rationale = rationale
        existing.updated_at = datetime.now(UTC)
        db.add(existing)
    else:
        existing = GapRecommendation(
            recommendation_type=rec_type,
            scap_course_id=scap_course_id,
            market_course_id=market_course_id,
            creation_key=creation_key,
            score=score,
            score_breakdown=score_breakdown,
            schools_offering=schools_offering,
            suggested_hours=suggested_hours,
            certification_suggestions=certification_suggestions,
            rationale=rationale,
            status="draft",
        )
        db.add(existing)
        await db.flush()

    return existing


# ---------------------------------------------------------------------------
# Pass 1 — Closure detection
# ---------------------------------------------------------------------------

async def _pass1_closure(db: AsyncSession) -> list[dict[str, Any]]:
    """Détecte les cours SCAP menacés par des offres concurrentes similaires."""
    # Récupère tous les cours SCAP actifs
    result = await db.execute(
        select(Course).where(Course.status == "active")
    )
    scap_courses: list[Course] = list(result.scalars().all())

    if not scap_courses:
        logger.info("Aucun cours SCAP actif — closure analysis ignorée.")
        return []

    # Récupère tous les SchoolCourse non supprimés, avec leur école
    school_result = await db.execute(
        select(SchoolCourse)
        .options(selectinload(SchoolCourse.school_registry))
        .where(SchoolCourse.is_removed.is_(False))
    )
    all_school_courses: list[SchoolCourse] = list(school_result.scalars().all())

    if not all_school_courses:
        logger.info("Aucun SchoolCourse en base — closure analysis ignorée.")
        return []

    created: list[dict[str, Any]] = []

    for course in scap_courses:
        # 1. SchoolCourse avec titre similaire
        similar: list[tuple[SchoolCourse, float]] = []
        for sc in all_school_courses:
            sim = _compute_similarity(course.title, sc.title)
            if sim > _SIMILARITY_THRESHOLD:
                similar.append((sc, sim))

        if not similar:
            continue

        # 2. Écoles distinctes qui proposent ces cours
        school_names: set[str] = set()
        for sc, _ in similar:
            if sc.school_registry and sc.school_registry.name:
                school_names.add(sc.school_registry.name)
        schools_count = len(school_names)

        # 3. Facteurs de score
        max_sim = max(s for _, s in similar)

        # schools_offering_count (30%)
        schools_factor = min(schools_count, 5) / 5.0

        # max_title_similarity (20%)
        sim_factor = max_sim

        # low_popularity (25%)
        if course.popularity_score is not None:
            popularity_factor = max(0.0, 1.0 - (course.popularity_score / 100.0))
        else:
            popularity_factor = 0.5

        # category_has_alternatives (15%)
        cat_factor = 0.0
        if course.category:
            cat_lower = course.category.lower()
            for sc in all_school_courses:
                if sc.category and sc.category.lower() == cat_lower:
                    cat_factor = 1.0
                    break

        # no_enrollment (10%)
        enrollment_factor = 1.0 if course.enrolled_count == 0 else 0.0

        # 4. Score pondéré (0–100)
        weighted = (
            schools_factor * 0.30
            + sim_factor * 0.20
            + popularity_factor * 0.25
            + cat_factor * 0.15
            + enrollment_factor * 0.10
        ) * 100.0

        if weighted < _SCORE_THRESHOLD:
            continue

        breakdown = {
            "schools_offering_count": round(schools_factor, 3),
            "max_title_similarity": round(sim_factor, 3),
            "low_popularity": round(popularity_factor, 3),
            "category_has_alternatives": round(cat_factor, 3),
            "no_enrollment": round(enrollment_factor, 3),
            "weighted_score": round(weighted, 1),
        }

        rationale = (
            f"Ce cours est proposé par {schools_count} écoles concurrentes. "
            f"Popularité faible (score: {course.popularity_score or 'N/D'}/100)."
        )

        rec = await _upsert_recommendation(
            db,
            rec_type="closure",
            scap_course_id=course.id,
            market_course_id=None,
            score=round(weighted, 1),
            score_breakdown=json.dumps(breakdown, ensure_ascii=False),
            schools_offering=json.dumps(list(school_names), ensure_ascii=False),
            rationale=rationale,
        )
        created.append({"id": rec.id, "type": "closure", "score": rec.score})

    return created


# ---------------------------------------------------------------------------
# Pass 2 — Creation detection
# ---------------------------------------------------------------------------

async def _pass2_creation(db: AsyncSession) -> list[dict[str, Any]]:
    """Détecte les formations du marché non couvertes par l'offre SCAP."""
    # Tous les SchoolCourse
    school_result = await db.execute(
        select(SchoolCourse)
        .options(selectinload(SchoolCourse.school_registry))
        .where(SchoolCourse.is_removed.is_(False))
    )
    all_school_courses: list[SchoolCourse] = list(school_result.scalars().all())

    if not all_school_courses:
        logger.info("Aucun SchoolCourse en base — creation analysis ignorée.")
        return []

    # Tous les cours SCAP actifs pour comparaison
    scap_result = await db.execute(
        select(Course).where(Course.status == "active")
    )
    scap_courses: list[Course] = list(scap_result.scalars().all())

    scap_titles = [(c.id, c.title, c.category) for c in scap_courses]
    scap_cat_counts: dict[str, int] = {}
    for c in scap_courses:
        if c.category:
            scap_cat_counts[c.category.lower()] = (
                scap_cat_counts.get(c.category.lower(), 0) + 1
            )

    # Filtre : garder uniquement les SchoolCourse sans équivalent SCAP
    unmatched: list[SchoolCourse] = []
    for sc in all_school_courses:
        max_sim = max(
            (_compute_similarity(sc.title, st) for _, st, _ in scap_titles),
            default=0.0,
        )
        if max_sim < _SIMILARITY_THRESHOLD:
            unmatched.append(sc)

    if not unmatched:
        logger.info("Tous les SchoolCourse ont un équivalent SCAP — creation analysis ignorée.")
        return []

    # Clustering par similarité (CPU-bound : exécuté dans un thread worker
    # pour ne pas bloquer la boucle événementielle du serveur).
    clusters = await asyncio.to_thread(_cluster_school_courses, unmatched)

    created: list[dict[str, Any]] = []
    now = datetime.now(UTC)
    cutoff_30d = now - timedelta(days=30)

    for rep, school_names, schools_count in clusters:
        rep_title = rep.title
        rep_category = rep.category

        # Absence ou faiblesse de la catégorie chez SCAP
        category_absent = True
        category_weak = False
        if rep_category:
            cat_lower = rep_category.lower()
            if cat_lower in scap_cat_counts:
                category_absent = False
                if scap_cat_counts[cat_lower] < 3:
                    category_weak = True

        # Similarité max avec un cours SCAP
        max_scap_sim = max(
            (_compute_similarity(rep_title, st) for _, st, _ in scap_titles),
            default=0.0,
        )

        # Certification potential
        certs = suggest_certifications(rep_title, rep_category, rep.duration_hours)
        cert_confidence = max((c["confidence"] for c in certs), default=0.0)

        # Facteurs de score
        schools_factor = min(schools_count, 5) / 5.0  # 30%

        # category_absent_or_weak (25%)
        if category_absent:
            cat_factor = 1.0
        elif category_weak:
            cat_factor = 0.5
        else:
            cat_factor = 0.0

        cert_factor = cert_confidence  # 15%

        # no_scap_equivalent (15%)
        no_equiv_factor = 1.0 if max_scap_sim < _SIMILARITY_THRESHOLD else 0.0

        # recent_discovery (10%)
        rep_seen = _as_utc(rep.first_seen_at)
        recent_factor = 1.0 if rep_seen and rep_seen >= cutoff_30d else 0.0

        weighted = (
            schools_factor * 0.30
            + cat_factor * 0.25
            + cert_factor * 0.15
            + no_equiv_factor * 0.15
            + recent_factor * 0.10
        ) * 100.0

        if weighted < _SCORE_THRESHOLD:
            continue

        # Estimation heures
        est = await estimate_hours(db, rep_title, rep_category)
        estimated_hours = est.get("estimated_hours")

        breakdown = {
            "schools_validation_count": round(schools_factor, 3),
            "category_absent_or_weak": round(cat_factor, 3),
            "certification_potential": round(cert_factor, 3),
            "no_scap_equivalent": round(no_equiv_factor, 3),
            "recent_discovery": round(recent_factor, 3),
            "weighted_score": round(weighted, 1),
            "representative_title": rep_title,
        }

        category_desc = "absente" if category_absent else "sous-représentée"
        rationale = (
            f"Formation proposée par {schools_count} écoles. "
            f"Catégorie {category_desc} chez SCAP."
        )

        rec = await _upsert_recommendation(
            db,
            rec_type="creation",
            scap_course_id=None,
            market_course_id=None,
            creation_key=rep_title.strip().lower()[:255],
            score=round(weighted, 1),
            score_breakdown=json.dumps(breakdown, ensure_ascii=False),
            schools_offering=json.dumps(list(school_names), ensure_ascii=False),
            suggested_hours=estimated_hours,
            certification_suggestions=json.dumps(certs, ensure_ascii=False) if certs else None,
            rationale=rationale,
        )
        created.append({"id": rec.id, "type": "creation", "score": rec.score})

    return created


# ---------------------------------------------------------------------------
# Orchestrateur
# ---------------------------------------------------------------------------

async def run_gap_analysis(db: AsyncSession, user_id: int | None = None) -> dict[str, Any]:
    """Deux passes d'analyse d'écart marché / offre SCAP.

    Returns
    -------
    dict avec clés "closure" et "creation", chacune étant une liste de
    {id, type, score}.
    """
    closure = await _pass1_closure(db)
    creation = await _pass2_creation(db)
    return {"closure": closure, "creation": creation}


# ---------------------------------------------------------------------------
# Requêtes pour l'UI
# ---------------------------------------------------------------------------

async def get_closure_candidates(db: AsyncSession) -> list[GapRecommendation]:
    """Top 50 recommandations de fermeture."""
    result = await db.execute(
        select(GapRecommendation)
        .options(selectinload(GapRecommendation.scap_course))
        .where(GapRecommendation.recommendation_type == "closure")
        .order_by(GapRecommendation.score.desc())
        .limit(50)
    )
    return list(result.scalars().all())


async def get_creation_suggestions(db: AsyncSession) -> list[GapRecommendation]:
    """Top 50 suggestions de création."""
    result = await db.execute(
        select(GapRecommendation)
        .where(GapRecommendation.recommendation_type == "creation")
        .order_by(GapRecommendation.score.desc())
        .limit(50)
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Actions sur recommandation
# ---------------------------------------------------------------------------

async def approve_recommendation(
    db: AsyncSession, rec_id: int, user_id: int | None = None
) -> dict[str, Any]:
    """Approuve une recommandation et applique l'action correspondante.

    - closure   → archive le cours SCAP + AuditLog
    - creation  → crée une CourseProposal brouillon
    """
    result = await db.execute(
        select(GapRecommendation).where(GapRecommendation.id == rec_id)
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise ValueError(f"Recommandation #{rec_id} introuvable.")
    if rec.status != "draft":
        raise ValueError(f"Recommandation #{rec_id} n'est pas modifiable (statut: {rec.status}).")

    rec.status = "approved"
    db.add(rec)

    action_taken: str | None = None

    if rec.recommendation_type == "creation":
        # Extrait le titre représentatif du score_breakdown
        title = "Nouveau cours"
        if rec.score_breakdown:
            try:
                breakdown = json.loads(rec.score_breakdown)
                title = breakdown.get("representative_title", title)
            except (json.JSONDecodeError, TypeError):
                pass

        proposal = CourseProposal(
            title=title,
            description=f"Proposition générée depuis la recommandation #{rec_id}",
            hours_estimated=rec.suggested_hours,
            certification_suggestions=rec.certification_suggestions,
            based_on=json.dumps([{"recommendation_id": rec_id}], ensure_ascii=False),
            status="draft",
        )
        db.add(proposal)
        await db.flush()
        action_taken = f"created_proposal_{proposal.id}"

    elif rec.recommendation_type == "closure":
        if not rec.scap_course_id:
            raise ValueError(
                f"Recommandation closure #{rec_id} sans scap_course_id — impossible à approuver."
            )
        course_result = await db.execute(
            select(Course).where(Course.id == rec.scap_course_id)
        )
        course = course_result.scalar_one_or_none()
        if not course:
            raise ValueError(
                f"Cours SCAP #{rec.scap_course_id} lié à la recommandation #{rec_id} introuvable."
            )
        course.status = "archived"
        db.add(course)

        audit = AuditLog(
            user_id=user_id,
            action="archive_course",
            target=f"course:{course.id}:{course.title}",
        )
        db.add(audit)
        action_taken = f"archived_course_{course.id}"

    else:
        raise ValueError(
            f"Type de recommandation '{rec.recommendation_type}' non supporté."
        )

    db.add(
        AuditLog(
            user_id=user_id,
            action="approve_recommendation",
            target=f"gap_recommendation:{rec.id}:{rec.recommendation_type}",
        )
    )

    await db.flush()

    return {
        "id": rec.id,
        "type": rec.recommendation_type,
        "status": "approved",
        "action": action_taken,
    }


async def reject_recommendation(
    db: AsyncSession, rec_id: int, user_id: int | None = None
) -> dict[str, Any]:
    """Rejette une recommandation (passe en rejected)."""
    result = await db.execute(
        select(GapRecommendation).where(GapRecommendation.id == rec_id)
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise ValueError(f"Recommandation #{rec_id} introuvable.")
    if rec.status != "draft":
        raise ValueError(f"Recommandation #{rec_id} n'est pas modifiable (statut: {rec.status}).")

    rec.status = "rejected"
    db.add(rec)
    db.add(
        AuditLog(
            user_id=user_id,
            action="reject_recommendation",
            target=f"gap_recommendation:{rec.id}:{rec.recommendation_type}",
        )
    )
    await db.flush()

    return {
        "id": rec.id,
        "type": rec.recommendation_type,
        "status": "rejected",
    }
