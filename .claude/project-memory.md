# Memory — ATLAS_Insight
**Last:** 2026-06-24 12:50

## Architecture

### Backend — FastAPI async
- `app/core/` — config (pydantic-settings), DB (SQLAlchemy async + aiosqlite), security (argon2 + JWT)
- `app/models/` — 5 entités : User, Course, MarketCourse, CourseProposal, AuditLog
- `app/schemas/` — Pydantic v2 (Create/Update/Read par entité)
- `app/api/` — 4 routers : auth, courses, imports, analytics
- `app/services/` — analytics_service (popularity score), import_service (Excel/CSV parser)
- `tests/` — Pytest async (conftest, test_auth, test_analytics, test_import)

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
