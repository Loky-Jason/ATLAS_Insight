# TODOs — Session courante

> **Phase:** 1 — quasi terminée (CRUD + services + frontend) ; reste design + provider veille réel
> **Dernière mise à jour:** 2026-06-25

## Spécifications (à rédiger avant chaque module)

- [ ] `specs/courses-ui.md` — CRUD courses frontend
- [ ] `specs/market-crud.md` — CRUD MarketCourse frontend
- [ ] `specs/proposals-crud.md` — CRUD CourseProposal frontend
- [ ] `specs/import-ui.md` — Page import frontend
- [ ] `specs/market-veille.md` — Veille marché automatisée
- [ ] `specs/estimation.md` — Estimation heures
- [ ] `specs/certification.md` — Suggestions certification
- [ ] `specs/favorites.md` — Favoris utilisateur

## Backend — Routes API à créer

- [x] `app/api/market_courses.py` — CRUD MarketCourse (75/75 tests)
- [x] `app/api/proposals.py` — CRUD CourseProposal
- [x] `app/api/audit_logs.py` — GET list audit logs (paginated, admin only)
- [x] `app/api/favorites.py` — CRUD Favoris (isolés par user)
- [x] `app/models/favorite.py` — SQLAlchemy model Favorite
- [x] `app/schemas/favorite.py` — Pydantic FavoriteCreate/Read
- [ ] `app/api/estimate.py` — Endpoint estimation heures
- [ ] `app/api/certification.py` — Suggestions certificat
- [ ] `app/services/market_service.py` — Veille web automatisée + score pertinence
- [ ] `app/services/estimation_service.py` — Calcul heures estimées
- [x] `app/services/estimation_service.py` — heures par similarité
- [x] `app/services/certification_service.py` — Matching RNCP / open badge
- [x] `app/services/market_service.py` + `app/api/market.py` — veille (StubProvider)
- [ ] Brancher provider veille web RÉEL dans `get_market_provider()` (WebSearch/LLM)

## Frontend — Pages à implémenter

- [x] `src/pages/Courses/index.tsx` — CRUD + filtres + favori
- [x] `src/pages/MarketWatch/index.tsx` — Tableau veille + sources + score
- [x] `src/pages/Proposals/index.tsx` — propositions + estim/certif
- [x] `src/pages/Import/index.tsx` — Upload Excel/CSV + résultat

## Infrastructure

- [x] Routes câblées dans `app/main.py` (8 routers + estimate/certification/market)
- [x] Endpoints ajoutés dans `src/lib/api.ts`
- [x] Tests par module (backend 121/121, frontend build vert)

## Reste Phase 1 / vers Phase 2

- [ ] Passe design `ui-ux-pro-max` → `emil-design-eng` → `impeccable` sur les pages
- [ ] Provider veille web réel (point d'intégration market_service)
- [ ] Phase 2 : export PDF/Word, vue Archives, migration M365

## Qualité (rappel continu)

- [ ] `npm run build` + `tsc --noEmit` avant chaque livraison
- [ ] `python -m pytest -v` après chaque module backend
- [ ] Relecture `impeccable` sur les nouvelles pages frontend
- [ ] MAJ `lessons.md` après chaque review
