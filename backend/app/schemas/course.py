"""Pydantic v2 schemas — Course."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

# Borne dure du lot : évite une transaction géante sur SQLite.
MAX_BATCH_SIZE = 200


class CourseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    category: str | None = None
    status: str = Field(default="active", pattern=r"^(active|archived)$")
    enrolled_count: int = Field(default=0, ge=0)
    dropout_count: int = Field(default=0, ge=0)
    age_brackets: str | None = None  # JSON string
    year: int | None = Field(default=None, ge=1900, le=2100)
    hours_estimated: float | None = Field(default=None, ge=0)
    source: str = Field(default="scap", max_length=50)
    notes: str | None = None


class CourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=512)
    category: str | None = None
    status: str | None = Field(default=None, pattern=r"^(active|archived)$")
    enrolled_count: int | None = Field(default=None, ge=0)
    dropout_count: int | None = Field(default=None, ge=0)
    age_brackets: str | None = None
    year: int | None = Field(default=None, ge=1900, le=2100)
    hours_estimated: float | None = Field(default=None, ge=0)
    notes: str | None = None


class CourseArchiveBatch(BaseModel):
    """Lot d'archivage : liste explicite d'identifiants, jamais un filtre.

    Le serveur n'archive pas « tout ce qui correspond à une requête » — un
    filtre mal compris côté client viderait un catalogue sans que personne ne
    voie quoi. Le client filtre et coche ; le serveur reçoit la liste.
    """

    course_ids: list[int] = Field(min_length=1, max_length=MAX_BATCH_SIZE)

    @field_validator("course_ids")
    @classmethod
    def _reject_duplicates(cls, value: list[int]) -> list[int]:
        if len(set(value)) != len(value):
            raise ValueError("La liste contient des identifiants en double.")
        return value


class CourseArchiveBatchResult(BaseModel):
    """Ventilation du lot : ce qui a été fait, ignoré, ou introuvable."""

    archived: list[int]
    skipped: list[int]
    not_found: list[int]


class CourseRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    title: str
    category: str | None
    status: str
    enrolled_count: int
    dropout_count: int
    age_brackets: str | None
    year: int | None
    hours_estimated: float | None
    popularity_score: float | None
    source: str
    notes: str | None
    created_at: datetime
    updated_at: datetime
