"""Pydantic v2 schemas — User."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="user", pattern=r"^(user|admin)$")


class UserRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    email: EmailStr
    role: str
    created_at: datetime


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)
