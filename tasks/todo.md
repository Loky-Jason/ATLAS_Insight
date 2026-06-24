# TODOs — Session courante

> **Phase:** 1 — Veille, estimation, certification
> **Dernière mise à jour:** 2026-06-24

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
- [ ] `app/services/certification_service.py` — Matching RNCP / open badge

## Frontend — Pages à implémenter

- [ ] `src/pages/Courses/index.tsx` — Liste CRUD avec filtres, recherche, édition
- [ ] `src/pages/MarketWatch/index.tsx` — Tableau veille + sources + score pertinence
- [ ] `src/pages/Proposals/index.tsx` — Liste propositions avec estim/certif
- [ ] `src/pages/Import/index.tsx` — Upload Excel/CSV avec statut et historique

## Infrastructure

- [ ] Ajouter routes manquantes dans `app/main.py` (market_courses, proposals, audit_logs)
- [ ] Ajouter endpoints API manquants dans `src/lib/api.ts`
- [ ] Ajouter tests pour chaque nouveau module

## Qualité

- [ ] `npm run lint` + `npm run typecheck` avant chaque livraison
- [ ] `python -m pytest -v` après chaque module backend
- [ ] Relecture `impeccable` sur les nouvelles pages frontend
- [ ] MAJ `lessons.md` après chaque review
