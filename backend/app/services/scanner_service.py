"""Service scanner — scan d'écoles, diff, métriques tableau de bord."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_scan_run import MarketScanRun
from app.models.school_course import SchoolCourse
from app.models.school_registry import SchoolRegistry
from app.scrapers.base import NormalisedCourse, get_scraper

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compute_hash(course: NormalisedCourse) -> str:
    """SHA-256 du couple title|url pour détecter les modifications."""
    raw = f"{course['title']}|{course.get('url', '') or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _course_to_dict(c: SchoolCourse) -> dict[str, Any]:
    return {
        "id": c.id,
        "external_id": c.external_id,
        "title": c.title,
        "url": c.url,
        "description": c.description,
        "duration_hours": c.duration_hours,
        "price": c.price,
        "category": c.category,
        "format": c.format,
        "certification": c.certification,
        "content_hash": c.content_hash,
        "first_seen_at": c.first_seen_at.isoformat() if c.first_seen_at else None,
        "last_seen_at": c.last_seen_at.isoformat() if c.last_seen_at else None,
        "last_updated_at": c.last_updated_at.isoformat() if c.last_updated_at else None,
        "is_removed": c.is_removed,
        "removed_at": c.removed_at.isoformat() if c.removed_at else None,
    }


# ---------------------------------------------------------------------------
# Scan orchestrator
# ---------------------------------------------------------------------------


async def run_school_scan(
    db: AsyncSession,
    school_registry_id: int,
    user_id: int,
) -> dict[str, Any]:
    """
    Scan complet d'une école : scrape → diff → persistance.

    Returns
    -------
    dict {school_name, status, found, new, modified, removed, scan_run_id}
    """
    school = await db.get(SchoolRegistry, school_registry_id)
    if school is None:
        raise ValueError(f"SchoolRegistry #{school_registry_id} introuvable")

    scraper_cls = get_scraper(school.scraper_strategy)
    scraper = scraper_cls(school_registry_id=school.id)

    scan_run = MarketScanRun(
        school_registry_id=school.id,
        status="running",
    )
    db.add(scan_run)
    await db.flush()

    # Scrap (synchrone → thread)
    try:
        raw_courses: list[NormalisedCourse] = await asyncio.to_thread(
            scraper.fetch_all_courses
        )
    except Exception as exc:
        scan_run.status = "error"
        scan_run.error_msg = str(exc)[:1024]
        scan_run.finished_at = datetime.now(timezone.utc)
        await db.flush()
        scraper.close()
        logger.error("Scan échoué school=%s: %s", school.name, exc)
        return {
            "school_name": school.name,
            "status": "error",
            "found": 0,
            "new": 0,
            "modified": 0,
            "removed": 0,
            "scan_run_id": scan_run.id,
        }

    # Existing active courses indexées par external_id
    result = await db.execute(
        select(SchoolCourse).where(
            SchoolCourse.school_registry_id == school.id,
            SchoolCourse.is_removed == False,
        )
    )
    existing_courses: list[SchoolCourse] = list(result.scalars().all())
    existing_by_ext_id: dict[str, SchoolCourse] = {
        c.external_id: c for c in existing_courses
    }

    now = datetime.now(timezone.utc)
    seen_ids: set[str] = set()
    new_count = 0
    modified_count = 0
    unchanged_count = 0

    for cd in raw_courses:
        ext_id = cd["external_id"]
        ch = _compute_hash(cd)
        seen_ids.add(ext_id)

        existing = existing_by_ext_id.get(ext_id)

        if existing is None:
            # NEW
            db.add(
                SchoolCourse(
                    school_registry_id=school.id,
                    external_id=ext_id,
                    title=cd["title"],
                    url=cd.get("url"),
                    description=cd.get("description"),
                    duration_hours=cd.get("duration_hours"),
                    price=cd.get("price"),
                    category=cd.get("category"),
                    format=cd.get("format"),
                    certification=cd.get("certification"),
                    content_hash=ch,
                    first_seen_at=now,
                    last_seen_at=now,
                )
            )
            new_count += 1
        elif existing.content_hash != ch:
            # MODIFIED
            existing.title = cd["title"]
            existing.url = cd.get("url")
            existing.description = cd.get("description")
            existing.duration_hours = cd.get("duration_hours")
            existing.price = cd.get("price")
            existing.category = cd.get("category")
            existing.format = cd.get("format")
            existing.certification = cd.get("certification")
            existing.content_hash = ch
            existing.last_updated_at = now
            existing.last_seen_at = now
            modified_count += 1
        else:
            # UNCHANGED
            existing.last_seen_at = now
            unchanged_count += 1

    # REMOVED — plus dans les résultats du scrap
    removed_count = 0
    for course in existing_courses:
        if course.external_id not in seen_ids:
            course.is_removed = True
            course.removed_at = now
            removed_count += 1

    # Finalisation scan run
    scan_run.status = "completed"
    scan_run.courses_found = len(raw_courses)
    scan_run.courses_new = new_count
    scan_run.courses_modified = modified_count
    scan_run.courses_removed = removed_count
    scan_run.finished_at = now

    school.last_scanned_at = now

    await db.flush()
    scraper.close()

    logger.info(
        "Scan terminé school=%s found=%d new=%d mod=%d removed=%d",
        school.name,
        len(raw_courses),
        new_count,
        modified_count,
        removed_count,
    )

    return {
        "school_name": school.name,
        "status": "completed",
        "found": len(raw_courses),
        "new": new_count,
        "modified": modified_count,
        "removed": removed_count,
        "scan_run_id": scan_run.id,
    }


# ---------------------------------------------------------------------------
# Diff
# ---------------------------------------------------------------------------


async def get_school_diff(
    db: AsyncSession,
    school_registry_id: int,
) -> dict[str, Any]:
    """
    Diff structuré du dernier scan pour une école.

    Returns
    -------
    dict {scan_run, new_courses, modified_courses, removed_courses}
    """
    result = await db.execute(
        select(MarketScanRun)
        .where(MarketScanRun.school_registry_id == school_registry_id)
        .order_by(MarketScanRun.started_at.desc())
        .limit(1)
    )
    scan_run = result.scalars().first()
    if scan_run is None or scan_run.started_at is None:
        return {
            "scan_run": None,
            "new_courses": [],
            "modified_courses": [],
            "removed_courses": [],
        }

    started = scan_run.started_at
    sid = school_registry_id

    new_q = await db.execute(
        select(SchoolCourse)
        .where(
            SchoolCourse.school_registry_id == sid,
            SchoolCourse.first_seen_at >= started,
            SchoolCourse.is_removed == False,
        )
        .order_by(SchoolCourse.first_seen_at.desc())
    )

    mod_q = await db.execute(
        select(SchoolCourse)
        .where(
            SchoolCourse.school_registry_id == sid,
            SchoolCourse.last_updated_at >= started,
            SchoolCourse.is_removed == False,
        )
        .order_by(SchoolCourse.last_updated_at.desc())
    )

    rem_q = await db.execute(
        select(SchoolCourse)
        .where(
            SchoolCourse.school_registry_id == sid,
            SchoolCourse.removed_at >= started,
            SchoolCourse.is_removed == True,
        )
        .order_by(SchoolCourse.removed_at.desc())
    )

    return {
        "scan_run": {
            "id": scan_run.id,
            "status": scan_run.status,
            "started_at": scan_run.started_at.isoformat()
            if scan_run.started_at
            else None,
            "finished_at": scan_run.finished_at.isoformat()
            if scan_run.finished_at
            else None,
            "courses_found": scan_run.courses_found,
            "courses_new": scan_run.courses_new,
            "courses_modified": scan_run.courses_modified,
            "courses_removed": scan_run.courses_removed,
            "error_msg": scan_run.error_msg,
        },
        "new_courses": [_course_to_dict(c) for c in new_q.scalars().all()],
        "modified_courses": [_course_to_dict(c) for c in mod_q.scalars().all()],
        "removed_courses": [_course_to_dict(c) for c in rem_q.scalars().all()],
    }


# ---------------------------------------------------------------------------
# Dashboard badges
# ---------------------------------------------------------------------------


async def get_dashboard_counts(db: AsyncSession) -> dict[str, int]:
    """
    Compteurs pour les badges de navigation du tableau de bord.

    Returns
    -------
    dict {total_schools, unreviewed_scans, closure_candidates,
          creation_suggestions}
    """
    try:
        total = await db.execute(
            select(func.count(SchoolRegistry.id)).where(
                SchoolRegistry.active == True
            )
        )
        total_schools: int = total.scalar() or 0

        unrev = await db.execute(
            select(func.count(MarketScanRun.id)).where(
                or_(
                    MarketScanRun.courses_new > 0,
                    MarketScanRun.courses_modified > 0,
                )
            )
        )
        unreviewed_scans: int = unrev.scalar() or 0

        # GapRecommendation counts — Phase 1c (toujours 0 pour l'instant)
        closure_candidates = 0
        creation_suggestions = 0
    except Exception as exc:
        logger.error("Erreur get_dashboard_counts : %s", exc)
        raise

    return {
        "total_schools": total_schools,
        "unreviewed_scans": unreviewed_scans,
        "closure_candidates": closure_candidates,
        "creation_suggestions": creation_suggestions,
    }
