"""Tests Phase 1b — scanner_service.

Covers:
  - C1 : _course_to_dict inclut school_registry_id dans sa sortie
        (commit 68850d7).
  - C2 : toutes les clés dict sont présentes (structure complète).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.models.school_course import SchoolCourse
from app.services.scanner_service import _course_to_dict


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
