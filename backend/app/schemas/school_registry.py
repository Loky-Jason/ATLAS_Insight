"""Pydantic v2 schemas — SchoolRegistry."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.url_safety import validate_external_url


class SchoolRegistryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1, max_length=2048)
    scraper_strategy: str = Field(default="stub", max_length=50)
    active: bool = True
    scan_interval: int = Field(default=1440, ge=1)
    config: dict | None = Field(default=None)

    @field_validator("url")
    @classmethod
    def _check_url(cls, v: str) -> str:
        return validate_external_url(v)


class SchoolRegistryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    url: str | None = Field(default=None, min_length=1, max_length=2048)
    scraper_strategy: str | None = Field(default=None, max_length=50)
    active: bool | None = None
    scan_interval: int | None = Field(default=None, ge=1)
    config: dict | None = Field(default=None)

    @field_validator("url")
    @classmethod
    def _check_url(cls, v: str | None) -> str | None:
        return validate_external_url(v) if v is not None else v


class SchoolRegistryRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    url: str
    scraper_strategy: str
    active: bool
    scan_interval: int
    last_scanned_at: datetime | None
    config: dict | None
    created_at: datetime


class SchoolRegistryList(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    url: str
    scraper_strategy: str
    active: bool
    scan_interval: int
    last_scanned_at: datetime | None
    config: dict | None
    created_at: datetime


class TestConnectionRequest(BaseModel):
    url: str = Field(max_length=2048)

    @field_validator("url")
    @classmethod
    def _check_url(cls, v: str) -> str:
        return validate_external_url(v)
