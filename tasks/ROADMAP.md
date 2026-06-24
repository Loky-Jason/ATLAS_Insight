# ROADMAP — ATLAS_Insight

> Dashboard décisionnel SCAP.paris
> Source de vérité : `docs/SPEC.md`

---

## ✅ Phase 0 — Fondations _(terminée)_

| Module | Statut | Détail |
|--------|--------|--------|
| Scaffolding | ✅ | Vite + FastAPI + SQLite, 3 commits |
| Auth | ✅ | Register/login/logout/me, argon2 + JWT httpOnly, bootstrap admin |
| Data model | ✅ | 5 entités (User, Course, MarketCourse, CourseProposal, AuditLog) |
| Import Excel/CSV | ✅ | pandas + openpyxl, protection injection formules, validation colonnes |
| Analytics | ✅ | Popularity score, top/flop, refresh endpoint |
| Dashboard UI | ✅ | Recharts bar charts, stats cards, fallback mock data |
| Tests | ✅ | 3 suites (auth, analytics, import) — 24+ tests |
| Sécurité | ✅ | Timing attack protection, audit logs, soft-delete, upload limits |

---

## 🔜 Phase 1 — Veille, estimation, certification _(en cours)_

| Module | Priorité | Dépendances | Statut |
|--------|----------|-------------|--------|
| **1.1** Courses CRUD frontend | P0 | API courses, router existant | ⏳ À faire |
| **1.2** MarketCourse CRUD frontend | P0 | API market_courses | ⏳ À faire |
| **1.3** CourseProposal CRUD frontend | P0 | API course_proposals | ⏳ À faire |
| **1.4** Veille marché auto | P1 | API recherche web + LLM | ⏳ À faire |
| **1.5** Estimation heures | P1 | Logique métier par similarité | ⏳ À faire |
| **1.6** Suggestions certification | P1 | RNCP + open badge matching | ⏳ À faire |
| **1.7** Tests Phase 1 | P1 | Chaque module | ⏳ À faire |

### Modules API backend à créer

- `app/api/market_courses.py` — CRUD MarketCourse
- `app/api/proposals.py` — CRUD CourseProposal
- `app/api/estimate.py` — Endpoint estimation heures
- `app/api/certification.py` — Suggestions certificat
- `app/services/market_service.py` — Veille web (recherche + parsing)
- `app/services/estimation_service.py` — Calcul heures estimées
- `app/services/certification_service.py` — Matching RNCP / open badge
- `app/services/market_veille.py` — Agrégation veille + score pertinence

### Pages frontend à créer

- `src/pages/MarketWatch/index.tsx` — Tableau veille + sources + score pertinence
- `src/pages/Proposals/index.tsx` — Liste propositions avec estim/certif
- `src/pages/Courses/index.tsx` — Liste CRUD avec filtres, recherche, édition

---

## 📅 Phase 2 — Export, archivage, migration _(plus tard)_

| Module | Priorité | Dépendances | Statut |
|--------|----------|-------------|--------|
| **2.1** Export PDF (WeasyPrint) | P0 | Phase 1 complète | 📅 |
| **2.2** Export Word (python-docx) | P0 | Phase 1 complète | 📅 |
| **2.3** Archives view frontend | P1 | Phase 1 | 📅 |
| **2.4** Archivage avancé (batch, filtre) | P1 | Phase 1 | 📅 |
| **2.5** Migration M365/Entra ID | P2 | Phases 0-2 stables | 📅 |
| **2.6** Tests Phase 2 | P1 | Chaque module | 📅 |

---

## Jalons

| Jalon | Date cible | Livrables |
|-------|-----------|-----------|
| M0 — Phase 0 | ✅ Terminé | Auth, CRUD, import, dashboard |
| M1 — Phase 1 core | TBD | CRUD frontend complet + veille |
| M2 — Phase 1 full | TBD | Estimation + certification |
| M3 — Phase 2 | TBD | Export + archivage |
| M4 — Production | TBD | Migration M365 |

---

## Conventions de branche

- `master` — stable, Phase 0 livrée
- `feat/<module>` — branches feature (ex: `feat/market-watch`, `feat/export-pdf`)
- Commits en Conventional Commits (caveman style)
