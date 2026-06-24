# TODOs — Session courante

> **Phase:** 1 — Veille, estimation, certification
> **Dernière mise à jour:** 2026-06-24

## Backend — CRUD à créer

- [ ] `app/api/market_courses.py` — CRUD MarketCourse (list, create, get, update, delete)
- [ ] `app/api/proposals.py` — CRUD CourseProposal (list, create, get, update, delete)
- [ ] `app/api/estimate.py` — Endpoint estimation heures
- [ ] `app/api/certification.py` — Suggestions certificat
- [ ] `app/services/market_service.py` — Veille web automatisée
- [ ] `app/services/estimation_service.py` — Calcul heures estimées
- [ ] `app/services/certification_service.py` — Matching RNCP / open badge

## Frontend — Pages à implémenter

- [ ] `src/pages/Courses/index.tsx` — Liste CRUD avec filtres, recherche, édition
- [ ] `src/pages/MarketWatch/index.tsx` — Tableau veille + sources + score pertinence
- [ ] `src/pages/Proposals/index.tsx` — Liste propositions avec estim/certif

## Infrastructure

- [ ] Ajouter routes manquantes dans `app/main.py` (market_courses, proposals)
- [ ] Ajouter endpoints API manquants dans `src/lib/api.ts`
- [ ] Ajouter tests pour chaque nouveau module

## Qualité

- [ ] `npm run lint` + `npm run typecheck` avant chaque livraison
- [ ] `python -m pytest -v` après chaque module backend
- [ ] Relecture `impeccable` sur les nouvelles pages frontend
- [ ] MAJ `lessons.md` après chaque review
