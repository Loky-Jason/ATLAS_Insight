# Memory — ATLAS_Insight
**Last:** 2026-06-25 — Sprint backend Phase 1 (CRUD) livré, 75/75 tests

## Architecture

### Backend — FastAPI async
- `app/core/` — config (pydantic-settings), DB (SQLAlchemy async + aiosqlite), security (argon2 + JWT)
- `app/models/` — 6 entités : User, Course, MarketCourse, CourseProposal, AuditLog, Favorite
- `app/schemas/` — Pydantic v2 (Create/Update/Read par entité)
- `app/api/` — 8 routers : auth, courses, imports, analytics, **market_courses, proposals, favorites, audit_logs** (Phase 1)
- `app/models/` — +Favorite (FK course OU market_course, 1 seule via model_validator)
- `app/services/` — analytics_service (popularity score), import_service (Excel/CSV parser)
- `tests/` — Pytest async, **75/75** (auth, analytics, import, market_courses, proposals, favorites, audit_logs)
- API préfixe `/api/v1`. Mutations destructives = require_admin + AuditLog. Favoris isolés par user.

### Frontend — React 18 + Vite 6 + TS strict
- `src/lib/` — api.ts (fetch client), auth.tsx (AuthProvider + useAuth), utils.ts (cn)
- `src/components/` — AppShell (sidebar layout), ui/ (shadcn Button, Card, Input, Label)
- `src/pages/` — Login (OK), Dashboard (OK + mock data fallback), Courses/MarketWatch/Proposals/Archives (placeholders)
- Routes : `/login`, `/dashboard`, `/courses`, `/market-watch`, `/proposals`, `/archives`

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
