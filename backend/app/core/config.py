"""Application settings loaded from environment / .env file."""

from __future__ import annotations

import logging

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_WEAK_KEYS = {"CHANGE_ME_IN_DOT_ENV", "changeme", "secret", ""}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Security
    secret_key: str = "CHANGE_ME_IN_DOT_ENV"
    jwt_expire_seconds: int = 3600  # 1 h (tokens non révocables au logout)

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/atlas.db"

    # CORS
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Market scan
    market_provider: str = "stub"

    # Environment
    environment: str = "development"

    @model_validator(mode="after")
    def _validate_secret_key(self) -> Settings:
        """Refuse une SECRET_KEY faible en production ; avertit hors prod."""
        key = self.secret_key
        is_weak = key in _WEAK_KEYS or len(key) < 32
        if self.is_production:
            if is_weak:
                raise ValueError(
                    "SECRET_KEY trop faible ou par défaut. "
                    "Générez-en une avec : python -c \"import secrets; print(secrets.token_hex(32))\""
                )
        else:
            if is_weak:
                logger.warning(
                    "SECRET_KEY faible détectée (développement). "
                    "Ne jamais utiliser cette clé en production."
                )
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a parsed list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


settings = Settings()
