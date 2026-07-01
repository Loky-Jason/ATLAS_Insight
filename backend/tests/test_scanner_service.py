"""Tests Phase 1b — scanner_service.

Covers:
  - C1 : _course_to_dict inclut school_registry_id dans sa sortie
        (commit 68850d7).
  - C2 : toutes les clés dict sont présentes (structure complète).
  - C3 : run_school_scan retourne error_msg en cas d'exception scraper.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from app.models.school_course import SchoolCourse
from app.models.school_registry import SchoolRegistry
from app.scrapers.stub import StubScraperAdapter
from app.services.scanner_service import _course_to_dict, run_school_scan


def test_course_to_dict_includes_school_registry_id() -> None:
    """C1 : school_registry_id présent dans la sortie."""
    course = SchoolCourse(
        school_registry_id=42,
        external_id="ext-test-1",
        title="Test Course",
    )
    result = _course_to_dict(course)
    assert "school_registry_id" in result
    assert result["school_registry_id"] == 42


def test_course_to_dict_full_keys() -> None:
    """C2 : toutes les clés attendues sont présentes."""
    course = SchoolCourse(
        school_registry_id=1,
        external_id="ext-full",
        title="Full Course",
        url="https://example.com/course",
        description="A full course",
        duration_hours=30.0,
        price=199.99,
        category="Développement",
        format="présentiel",
        certification="Certificat",
        content_hash="abc123",
        first_seen_at=datetime(2026, 6, 1, tzinfo=UTC),
        last_seen_at=datetime(2026, 6, 27, tzinfo=UTC),
        last_updated_at=datetime(2026, 6, 20, tzinfo=UTC),
        is_removed=False,
        removed_at=None,
    )
    result = _course_to_dict(course)

    expected_keys = {
        "id",
        "school_registry_id",
        "external_id",
        "title",
        "url",
        "description",
        "duration_hours",
        "price",
        "category",
        "format",
        "certification",
        "content_hash",
        "first_seen_at",
        "last_seen_at",
        "last_updated_at",
        "is_removed",
        "removed_at",
    }
    assert set(result.keys()) == expected_keys
    assert result["school_registry_id"] == 1
    assert result["title"] == "Full Course"
    assert result["is_removed"] is False


def test_course_to_dict_nullable_fields_none() -> None:
    """Les champs optionnels peuvent être None sans planter."""
    course = SchoolCourse(
        school_registry_id=7,
        external_id="ext-nullable",
        title="Nullable Course",
        url=None,
        description=None,
        duration_hours=None,
        price=None,
        category=None,
        format=None,
        certification=None,
        content_hash=None,
        first_seen_at=datetime(2026, 6, 1, tzinfo=UTC),
        last_seen_at=datetime(2026, 6, 27, tzinfo=UTC),
        last_updated_at=None,
        is_removed=True,
        removed_at=datetime(2026, 6, 15, tzinfo=UTC),
    )
    result = _course_to_dict(course)
    assert result["school_registry_id"] == 7
    assert result["url"] is None
    assert result["description"] is None
    assert result["duration_hours"] is None
    assert result["price"] is None
    assert result["category"] is None
    assert result["format"] is None
    assert result["certification"] is None
    assert result["content_hash"] is None
    assert result["last_updated_at"] is None
    assert result["is_removed"] is True
    assert result["removed_at"] is not None


# ---------------------------------------------------------------------------
# C3 — run_school_scan error feedback
# ---------------------------------------------------------------------------


async def _seed_school(db) -> SchoolRegistry:
    """Ajoute une école active avec stratégie stub dans la DB de test."""
    school = SchoolRegistry(
        name="École Test Scan Error",
        url="https://test-scan-error.example.com",
        scraper_strategy="stub",
        active=True,
        scan_interval=1440,
    )
    db.add(school)
    await db.flush()
    return school


@pytest.mark.asyncio
async def test_run_school_scan_returns_error_msg_on_scraper_failure(db_session) -> None:
    """C3 : run_school_scan retourne error_msg quand le scraper lève une exception."""
    school = await _seed_school(db_session)

    with patch.object(
        StubScraperAdapter,
        "fetch_all_courses",
        side_effect=ValueError("Connection timeout — API injoignable"),
    ):
        result = await run_school_scan(
            db=db_session,
            school_registry_id=school.id,
            user_id=1,
        )

    assert result["status"] == "error"
    assert result["school_name"] == "École Test Scan Error"
    assert "error_msg" in result
    assert isinstance(result["error_msg"], str)
    assert len(result["error_msg"]) > 0
    assert "Connection timeout" in result["error_msg"]
    assert result["found"] == 0
    assert result["new"] == 0
    assert result["modified"] == 0
    assert result["removed"] == 0
    assert isinstance(result["scan_run_id"], int)
