# Memory — ATLAS_Insight v2
**Last:** 2026-06-25 — Roadmap v2 validée : Phase 1a ✅, Phase 1b (multi-school) + Phase 1c (gap analysis) + UX refonte planifiés. Backend 133/133, frontend build vert. Dernier commit `0413f34` (master, GitHub Loky-Jason/ATLAS_Insight).

## État pour reprise (OpenCode)
- Phase 0 + Phase 1a complètes. Roadmap étendue avec Phase 1b (veille multi-écoles), Phase 1c (gap analysis), Phase UX (refonte navigation + dashboard hub).
- 5 décisions clés validées : (1) dépréciation `MarketSearchProvider` → scraper adapters + registre, (2) `MarketCourse.school_registry_id FK` + string fallback, (3) endpoint `/dashboard/counts` plutôt que `/ui/counts`, (4) scoring à la promotion SchoolCourse → MarketCourse, (5) content hash title+URL simple.
- Prochaine session : démarrer Phase 1b — SchoolRegistry model + scraper adapter interface + SCAP adapter migration.
- Lancer en local : backend `cd backend && .venv/Scripts/python -m uvicorn app.main:app --port 8000` (copier `.env.example`→`.env`, générer SECRET_KEY `python -c "import secrets;print(secrets.token_hex(32))"`) ; frontend `cd frontend && npm run dev` (port 5173). Admin : `admin@scap.paris` / `admin123`.
- Règle process : après chaque sprint front+back, faire un **run d'intégration réel** (serveurs lancés + parcours navigateur) — les sous-agents valident build/pytest, pas le runtime câblé.

## Architecture

### Backend — FastAPI async
- `app/core/` — config (pydantic-settings), DB (SQLAlchemy async + aiosqlite), security (argon2 + JWT)
- `app/models/` — 6 entités actuelles : User, Course, MarketCourse, CourseProposal, AuditLog, Favorite. **À ajouter :** SchoolRegistry, SchoolCourse, MarketScanRun, GapRecommendation
- `app/schemas/` — Pydantic v2 (Create/Update/Read par entité) + `analytics.py`
- `app/api/` — 8 routers actuels. **À ajouter :** schools, gap-recommendations, dashboard (counts)
- `app/services/` — analytics, import, estimation (difflib), certification (14 règles), market (StubProvider, **à déprécier**)
- `app/scrapers/` — **NOUVEAU** répertoire pour adapters scraper (SCAP, ORSYS, Cegos, Demos…)
- `tests/` — Pytest async, **133/133**
- API préfixe `/api/v1`. Mutations destructives = require_admin + AuditLog.

### Frontend — React 18 + Vite 6 + TS strict
- `src/lib/` — api.ts (fetch client), auth.tsx (AuthProvider + useAuth), utils.ts (cn)
- `src/components/` — AppShell (sidebar), ErrorBoundary, ui/ (shadcn)
- `src/pages/` — Login, Dashboard, Courses, MarketWatch, Proposals, Import, Archives
- **UX à refondre :** navigation hiérarchique (Veille/Recommandations/Catalogue), dashboard hub avec badges, redirections anciens chemins

### Base — SQLite
- Fichier : `data/atlas.db` (gitignored)
- Chiffrement : BitLocker disque (pas SQLCipher)
- Pas d'Alembic — création tables via `init_db()` au démarrage

## Key decisions
| Décision | Date | Raison |
|----------|------|--------|
| Chiffrement BitLocker plutôt que SQLCipher | Phase 0 | Wheels SQLCipher fragiles sur Windows ; BitLocker standard Mairie |
| Bootstrap admin (premier compte = admin) | Phase 0 | Pas d'interface d'admin seeding — simple et sécurisé |
| Mock data fallback sur Dashboard | Phase 0 | UX utilisable même sans backend pour dev/démo |
| Popularity_score = enrolled − (dropouts × 1.5), normalisé [0,100] | Phase 0 | Formule simple, pondère les désistements |
| CSV injection protection (prefix `'`) | Phase 0 | E3b du spec — neutralise les formules Excel malveillantes |
| `starlette>=0.41,<1.0` épinglé | Phase 1 | Conflit starlette 1.x (tiré par mcp) vs FastAPI 0.115 |
| Cross-champ → `model_validator(mode="after")` | Phase 1 | field_validator ne voit pas les autres champs en Pydantic v2 |
| `response_model` obligatoire sur endpoints consommés par le front | Phase 1 | Verrou de contrat — un drift `{top,flop}`→`{most_popular,…}` avait crashé le dashboard |
| ErrorBoundary autour des pages | Phase 1 | Une erreur de rendu = page blanche sinon |
| `httpx` plutôt que `requests` | Phase 1b | httpx déjà en dev-deps, support sync+async natif, évite doublon de lib HTTP |
| `close()` sur MarketSearchProvider | Phase 1b | Ressource leak potentiel de la session HTTP sur scans longs |
| `query` forwardé à l'API SCAP | Phase 1b | Paramètre ignoré = code mort ; le mappage sur Keywords filtre les résultats côté API |
| **Dépréciation MarketSearchProvider → ScraperAdapter + registry** | Roadmap v2 | Évite double pipeline concurrent ; SCAP migré en adapter |
| **MarketCourse.school_registry_id FK + string fallback** | Roadmap v2 | Compat ascendante avec données legacy, lien FK vers SchoolRegistry |
| **Endpoint /dashboard/counts plutôt que /ui/counts** | Roadmap v2 | Cohérence avec convention par domaine existante |
| **Scoring à la promotion SchoolCourse→MarketCourse** | Roadmap v2 | SchoolCourse = raw, scoring appliqué au moment de la curation |
| **Content hash title+URL (pas SHA-256)** | Roadmap v2 | Suffisant pour détection modifs, coût implémentation minimal |
| **Workflow post-approbation GapRecommendation** | Roadmap v2 | Création→CourseProposal(draft), Fermeture→archive Course+AuditLog |
| **score_breakdown = Pydantic model typé (pas str JSON)** | Roadmap v2 | Évite les bugs de validation qu'ont `based_on` et `certification_suggestions` |
