"""Point d'entrée FastAPI — ATLAS Insight backend."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Routers
from app.api.analytics import router as analytics_router
from app.api.audit_logs import router as audit_logs_router
from app.api.auth import router as auth_router
from app.api.certification import router as certification_router
from app.api.courses import router as courses_router
from app.api.dashboard import router as dashboard_router
from app.api.estimate import router as estimate_router
from app.api.favorites import router as favorites_router
from app.api.gap_recommendations import router as gap_recommendations_router
from app.api.imports import router as imports_router
from app.api.market import router as market_router
from app.api.market_courses import router as market_courses_router
from app.api.proposals import router as proposals_router
from app.api.scan_runs import router as scan_runs_router
from app.api.school_courses import router as school_courses_router
from app.api.schools import router as schools_router
from app.core.config import settings
from app.core.db import init_db

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
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(audit_logs_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(certification_router, prefix="/api/v1")
app.include_router(courses_router, prefix="/api/v1")
app.include_router(estimate_router, prefix="/api/v1")
app.include_router(favorites_router, prefix="/api/v1")
app.include_router(imports_router, prefix="/api/v1")
app.include_router(market_router, prefix="/api/v1")
app.include_router(market_courses_router, prefix="/api/v1")
app.include_router(proposals_router, prefix="/api/v1")
app.include_router(schools_router, prefix="/api/v1")
app.include_router(school_courses_router, prefix="/api/v1")
app.include_router(scan_runs_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(gap_recommendations_router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Health check (public)
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Système"], summary="Vérification de l'état du service")
async def health() -> dict[str, str]:
    """Retourne OK si le service est opérationnel."""
    return {"status": "ok", "version": app.version}
