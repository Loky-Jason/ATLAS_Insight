# Memory — ATLAS_Insight
**Last:** 2026-06-25 — Phase 1 livrée + **vérifiée en live** (login+dashboard+CRUD). Backend 121/121, frontend build vert. Dernier commit `be01eb0` (master, poussé GitHub Loky-Jason/ATLAS_Insight).

## État pour reprise (OpenCode)
- Phase 0 + Phase 1 fonctionnelles et poussées. Reste Phase 1 : (1) **provider veille web RÉEL** (`market_service.get_market_provider()`, aujourd'hui StubProvider) ; (2) **passe design** ui-ux-pro-max → emil-design-eng → impeccable (UI encore brute, thème dark neutre).
- Lancer en local : backend `cd backend && .venv/Scripts/python -m uvicorn app.main:app --port 8000` (copier `.env.example`→`.env`, générer SECRET_KEY `python -c "import secrets;print(secrets.token_hex(32))"`) ; frontend `cd frontend && npm run dev` (port 5173). Compte démo seedé possible via API : admin (1er compte = admin).
- Règle process : après chaque sprint front+back, faire un **run d'intégration réel** (serveurs lancés + parcours navigateur) — les sous-agents valident build/pytest, pas le runtime câblé.

## Architecture

### Backend — FastAPI async
- `app/core/` — config (pydantic-settings), DB (SQLAlchemy async + aiosqlite), security (argon2 + JWT)
- `app/models/` — 6 entités : User, Course, MarketCourse, CourseProposal, AuditLog, Favorite
- `app/schemas/` — Pydantic v2 (Create/Update/Read par entité) + `analytics.py` (response_model AnalyticsPopularity/PopularityEntry)
- `app/api/` — 8 routers : auth, courses, imports, analytics, **market_courses, proposals, favorites, audit_logs** (Phase 1)
- `app/models/` — +Favorite (FK course OU market_course, 1 seule via model_validator)
- `app/services/` — analytics, import, **estimation (difflib), certification (14 règles), market (StubProvider, scoring vs offre SCAP)**
- Endpoints métier : POST `/estimate/hours`, `/certification/suggest`, `/market/scan` (admin). Provider veille web réel = point d'intégration `get_market_provider()`
- `tests/` — Pytest async, **121/121** (auth, analytics, import, market_courses, proposals, favorites, audit_logs)
- API préfixe `/api/v1`. Mutations destructives = require_admin + AuditLog. Favoris isolés par user.

### Frontend — React 18 + Vite 6 + TS strict
- `src/lib/` — api.ts (fetch client), auth.tsx (AuthProvider + useAuth), utils.ts (cn)
- `src/components/` — AppShell (sidebar layout, wrappe Outlet dans ErrorBoundary key=pathname), **ErrorBoundary.tsx** (fallback FR anti page blanche), ui/ (shadcn Button, Card, Input, Label, dialog)
- `src/pages/` — Login, Dashboard, **Courses/MarketWatch/Proposals/Import (CRUD complet)**, Archives (placeholder Phase 2)
- `src/lib/api.ts` — BASE_URL inclut `/api/v1` (sinon 404). Endpoints typés par module.
- Routes : `/login`, `/dashboard`, `/courses`, `/market-watch`, `/proposals`, `/import`, `/archives`

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
