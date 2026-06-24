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
| Tests | ✅ | 3 suites (auth, analytics, import) — 36/36 tests |
| Sécurité | ✅ | Timing attack protection, audit logs, soft-delete, upload limits |

---

## 🔜 Phase 1 — Veille, estimation, certification _(quasi terminée)_

| Module | Priorité | Dépendances | Spec | Statut |
|--------|----------|-------------|------|--------|
| **1.1** Courses CRUD frontend | P0 | API courses existant | `specs/courses-ui.md` | ✅ Fait (build vert) |
| **1.2** MarketCourse CRUD frontend | P0 | API market_courses | `specs/market-crud.md` | ✅ Fait |
| **1.3** CourseProposal CRUD frontend | P0 | API course_proposals | `specs/proposals-crud.md` | ✅ Fait |
| **1.4** Import UI frontend | P1 | API imports existant | `specs/import-ui.md` | ✅ Fait |
| **1.5** Veille marché auto | P1 | API recherche web + LLM | `specs/market-veille.md` | 🟡 Stub livré — provider web réel à brancher (`get_market_provider()`) |
| **1.6** Favoris (Favorite model + UI) | P1 | Auth existante | `specs/favorites.md` | ✅ Backend fait ; UI bouton favori dans Courses |
| **1.7** Estimation heures | P1 | Logique métier par similarité | `specs/estimation.md` | ✅ Fait (difflib + fallbacks) |
| **1.8** Suggestions certification | P1 | RNCP + open badge matching | `specs/certification.md` | ✅ Fait (14 règles) |
| **1.9** Tests Phase 1 | P1 | Chaque module | — | ✅ Backend 121/121 ; frontend build vert |
| **1.10** Passe design (ui-ux-pro-max → impeccable) | P1 | Pages Phase 1 | — | ⏳ À faire |

### Modules API backend

- ✅ `app/api/market_courses.py` — CRUD MarketCourse (list/get/create/update, delete admin+audit) — **75/75 tests**
- ✅ `app/api/proposals.py` — CRUD CourseProposal (idem)
- ✅ `app/api/audit_logs.py` — GET list audit logs (paginé, admin only)
- ✅ `app/api/favorites.py` — CRUD Favoris (isolés par user)
- ✅ `app/models/favorite.py` + `app/schemas/favorite.py` — Favorite (model_validator: exactement 1 FK)
- ✅ `app/api/estimate.py` — POST `/estimate/hours` (similarité difflib)
- ✅ `app/api/certification.py` — POST `/certification/suggest` (14 règles)
- ✅ `app/api/market.py` — POST `/market/scan` (admin) + `market_service.py` (StubProvider, scoring) — provider web réel à brancher
- ✅ `app/services/estimation_service.py` — Calcul heures estimées
- ✅ `app/services/certification_service.py` — Matching RNCP / open badge

### Pages frontend à créer

- `src/pages/Courses/index.tsx` — Liste CRUD avec filtres, recherche, édition
- `src/pages/MarketWatch/index.tsx` — Tableau veille + sources + score pertinence
- `src/pages/Proposals/index.tsx` — Liste propositions avec estim/certif
- `src/pages/Import/index.tsx` — Upload Excel/CSV avec statut et historique

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
| M1a — Phase 1 CRUD | TBD | CRUD frontend complet (Courses, MarketWatch, Proposals) + Import UI |
| M1b — Phase 1 Veille | TBD | Veille marché automatisée avec sources + score pertinence |
| M1c — Phase 1 Estim+Certif+Fav | TBD | Estimation heures + certification + favoris |
| M2 — Phase 2 | TBD | Export PDF/Word + archivage avancé |
| M3 — Production | TBD | Migration M365/Entra ID |

---

## Conventions de branche

- `master` — stable, Phase 0 livrée
- `feat/<module>` — branches feature (ex: `feat/market-watch`, `feat/export-pdf`)
- Commits en Conventional Commits (caveman style)
