"""Point d'entrée FastAPI — ATLAS Insight backend."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.db import init_db

# Routers
from app.api.auth import router as auth_router
from app.api.courses import router as courses_router
from app.api.imports import router as imports_router
from app.api.analytics import router as analytics_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Démarrage ATLAS Insight backend…")
    await init_db()
    logger.info("Base de données prête.")
    yield
    logger.info("Arrêt du backend.")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ATLAS Insight API",
    description="Backend décisionnel pour coordinateur pédagogique SCAP.paris.",
    version="0.1.0",
    lifespan=lifespan,
    # Docs désactivées en production (M4)
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(auth_router, prefix="/api/v1")
app.include_router(courses_router, prefix="/api/v1")
app.include_router(imports_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Health check (public)
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Système"], summary="Vérification de l'état du service")
async def health() -> dict[str, str]:
    """Retourne OK si le service est opérationnel."""
    return {"status": "ok", "version": app.version}
