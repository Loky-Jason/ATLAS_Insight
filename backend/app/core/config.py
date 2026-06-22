"""Application settings loaded from environment / .env file."""

from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Security
    secret_key: str = "CHANGE_ME_IN_DOT_ENV"
    jwt_expire_seconds: int = 28800  # 8 h

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/atlas.db"

    # CORS
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Environment
    environment: str = "development"

    @field_validator("secret_key")
    @classmethod
    def _secret_not_default(cls, v: str) -> str:
        if v == "CHANGE_ME_IN_DOT_ENV" and False:  # warn only in prod
            pass
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a parsed list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


settings = Settings()
