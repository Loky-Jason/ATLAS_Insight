# ROADMAP — ATLAS_Insight v2

> Dashboard décisionnel SCAP.paris — veille multi-écoles + gap analysis
> Source de vérité : `docs/SPEC.md`

---

## ✅ Phase 0 — Fondations _(terminée)_

| Module | Statut | Détail |
|--------|--------|--------|
| Scaffolding | ✅ | Vite + FastAPI + SQLite |
| Auth | ✅ | Register/login/logout/me, argon2 + JWT httpOnly, bootstrap admin |
| Data model | ✅ | 6 entités (User, Course, MarketCourse, CourseProposal, AuditLog, Favorite) |
| Import Excel/CSV | ✅ | pandas + openpyxl, protection injection formules, validation colonnes |
| Analytics | ✅ | Popularity score, top/flop, refresh endpoint |
| Dashboard UI | ✅ | Recharts bar charts, stats cards, fallback mock data |
| Tests | ✅ | 3 suites (auth, analytics, import) — 36/36 tests |
| Sécurité | ✅ | Timing attack protection, audit logs, soft-delete, upload limits |

---

## ✅ Phase 1a — CRUD + services _(terminée)_

| Module | Statut | Détail |
|--------|--------|--------|
| Courses CRUD frontend | ✅ | Liste, filtres, recherche, édition |
| MarketCourse CRUD frontend | ✅ | Tableau veille + sources + score pertinence |
| CourseProposal CRUD frontend | ✅ | Liste propositions avec estim/certif |
| Import UI frontend | ✅ | Upload Excel/CSV avec statut et historique |
| Estimation heures | ✅ | difflib + fallbacks, basis borné |
| Suggestions certification | ✅ | 14 règles RNCP + open badge |
| Favoris | ✅ | Backend + UI bouton favori |
| WebMarketProvider (SCAP) | ✅ | API SCAP `POST /Search/Elements`, parsing regex stdlib, pagination auto |
| Passe design (ui-ux-pro-max → impeccable) | ✅ | Design system, theme HSL, AppShell, Dashboard, animations |
| Tests | ✅ | Backend 133/133 ; frontend build vert |

### Modules API backend

- ✅ `app/api/market_courses.py` — CRUD MarketCourse (list/get/create/update, delete admin+audit) — **75/75 tests**
- ✅ `app/api/proposals.py` — CRUD CourseProposal (idem)
- ✅ `app/api/audit_logs.py` — GET list audit logs (paginé, admin only)
- ✅ `app/api/favorites.py` — CRUD Favoris (isolés par user)
- ✅ `app/api/estimate.py` — POST `/estimate/hours` (similarité difflib)
- ✅ `app/api/certification.py` — POST `/certification/suggest` (14 règles)
- ✅ `app/api/market.py` — POST `/market/scan` (admin) + `market_service.py` **(déprécié en faveur de Phase 1b)**
- ✅ `app/services/estimation_service.py` — Calcul heures estimées
- ✅ `app/services/certification_service.py` — Matching RNCP / open badge

---

## ✅ Phase 1b — Moteur de veille multi-écoles _(terminée 2026-06-27)_

> Livrée + poussée (`ee117f0`). Scrapers **SCAP + Stub + ORSYS + Cegos + Demos** (registry), `BaseScraperAdapter` (httpx + template sitemap + bornes), ScannerService diff hash-based, endpoints schools CRUD/scan/diff/counts, UI Écoles/Scans/Journal. Backend 256 tests, front 65 tests. Durci (try/except I/O, MAX_PAGES/MAX_COURSES, anti-SSRF schéma, AuditLog).

**Objectif** : Remplacer le pipeline mono-source `MarketSearchProvider` par un système multi-école à base de scraper adapters et d'un registre d'écoles.

| Module | Priorité | Dépendances | Statut |
|--------|----------|-------------|--------|
| **SchoolRegistry** (modèle + CRUD) | P0 | Aucune | 📝 |
| **SchoolCourse** (modèle brut scrappé) | P0 | SchoolRegistry | 📝 |
| **MarketScanRun** (audit trail scans) | P0 | SchoolRegistry | 📝 |
| **Scraper Adapters** (interface + registry) | P0 | Aucune | 📝 |
| **SCAP adapter** (migration WebMarketProvider) | P0 | Scraper Adapters | 📝 |
| **Scanner orchestrator** | P0 | SchoolRegistry + Adapters | 📝 |
| **Promouvoir** (SchoolCourse → MarketCourse) | P1 | SchoolCourse + MarketCourse | 📝 |
| **Endpoints API** (schools CRUD, scan, diff) | P0 | Modèles | 📝 |
| **UI Écoles suivies** (CRUD écoles) | P1 | Endpoints API | 📝 |
| **UI Résultats scan** (visualisation diffs) | P1 | Endpoints API | 📝 |
| **UI Journal modifs** (historique) | P1 | Endpoints API | 📝 |
| Tests | P1 | Chaque module | 📝 |

### Décisions architecturales
- `MarketSearchProvider` **déprécié** — SCAP réécrit comme `ScraperAdapter("SCAP", ...)` dans le registre
- `MarketCourse.school` → **gardé comme string fallback** + ajout de `school_registry_id FK` optionnelle
- **Promotion** : `SchoolCourse` (raw) → `MarketCourse` (curated, status="candidate"), réutilise `_compute_relevance()`
- **Content hash** : simple hash title+URL plutôt que checksum SHA-256 normalisé

---

## ✅ Phase 1c — Gap Analysis Engine _(terminée 2026-06-27)_

> Livrée. `GapRecommendation` (+`creation_key`), Closure/Creation scorers 5 facteurs, `gap_service` orchestrateur, endpoints analyze/closure-candidates/creation-suggestions/approve/list, UI Gap (À fermer / À créer). Régression `tests/test_gap_service.py`. Reste perf O(n²)+N+1 (chip `task_8aa9a344`, [[project-atlas-gap-perf]] — 27/06).

**Objectif** : Croiser les cours SCAP avec les données marché pour recommander fermetures et créations.

| Module | Priorité | Dépendances | Statut |
|--------|----------|-------------|--------|
| **GapRecommendation** (modèle + CRUD) | P0 | Phase 1b | 📝 |
| **Closure Scorer** (algorithme 5 facteurs) | P0 | SCAP Courses + SchoolCourse | 📝 |
| **Creation Scorer** (algorithme 5 facteurs) | P0 | SchoolCourse | 📝 |
| **GapAnalysisService** (orchestrateur) | P0 | Scorers + modèles | 📝 |
| **Workflow post-approbation** | P1 | GapRecommendation | 📝 |
| **Endpoints API** (closure-candidates, creation-suggestions, from-market, from-course) | P0 | GapAnalysisService | 📝 |
| **UI Recommandations** (À fermer, À créer) | P1 | Endpoints API | 📝 |

### Workflow post-approbation
```
GapRecommendation (approved)
  ├ type=creation → CourseProposal (draft, based_on recommandation.id)
  └ type=closure  → Course.status="archived" + AuditLog
```

---

## ✅ Phase UX — Refonte interface _(terminée 2026-06-27)_

> Livrée. Sidebar hiérarchique (Veille/Recommandations/Catalogue), redirections anciens chemins, dashboard hub (widgets stats + changements récents + reco one-click), endpoints `dashboard/counts`, badges live. Tests vitest (NavSectionBlock, Dashboard mock-data, Scans, Schools). MarketWatch monolithe retiré.

**Objectif** : Navigation hiérarchique, dashboard hub avec badges, actions one-click.

| Module | Priorité | Dépendances | Statut |
|--------|----------|-------------|--------|
| **Sidebar restructurée** (hiérarchie 3 niveaux) | P0 | Aucune (structure seule) | 📝 |
| **Redirections anciens chemins** | P0 | Routes restructurées | 📝 |
| **Dashboard hub** (stats + badges + widgets) | P1 | Phase 1b endpoints | 📝 |
| **Widget changements récents** | P1 | Endpoints scan/diff | 📝 |
| **Widget recommandations one-click** | P1 | Phase 1c endpoints | 📝 |
| **Endpoints dashboard/counts** | P0 | Phases 1b+1c | 📝 |
| **Badges live navigation** | P1 | Endpoints counts | 📝 |
| Tests intégration bout-en-bout | P1 | Tout ce qui précède | 📝 |

### Nouvelle arborescence
```
📊 Tableau de bord
─────────────────────
🔍 Veille
  ├ Résultats de scan       [badge nouveautés]
  ├ Journal des modifs
  └ Écoles suivies
💡 Recommandations
  ├ À fermer                [badge]
  ├ À créer                 [badge]
  └ Propositions            (existant)
─────────────────────
📚 Catalogue
  ├ Cours SCAP              (existant)
  ├ Import                  (existant)
  └ Archives                (existant)
```

---

## ✅ Dettes techniques — _(soldées 2026-09-05)_

> Commits `e7480bf` (Alembic) et `9cc57f9` (scrapers + docs + lint). Backend 341 tests.

| Dette | Statut | Détail |
|-------|--------|--------|
| Alembic demi-mesure | ✅ | 3 migrations inertes (2 heads, `initial_schema` sans `CREATE TABLE`) → schéma réel autogénéré `8783a989e776` ; `init_db()` piloté par migrations + adoption d'une base pré-Alembic ou tamponnée sur révision inconnue |
| SSRF par sitemap | ✅ | `<loc>` moissonnés validés (`validate_external_url` + `is_same_site`) ; override affaibli de `generic.py` supprimé |
| Filtre `/formation/` figé | ✅ | Paramètre `url_pattern` (échouait en silence à 0 résultat sur un autre segment) |
| `tasks/todo.md` périmé | ✅ | Remis à l'état réel |
| Perf `gap_service` O(n²) | ✅ | Résolue avant cette session (`_token_similarity` + `asyncio.to_thread`) |
| Lint E501 | 📅 | 24 lignes > 100 car. dans 12 fichiers non liés — passe de formatage dédiée |
| Provider veille réel | 📅 | `scraper_strategy` défaut toujours `stub` |

---

## 📅 Phase 2 — Export, archivage, migration _(prochaine)_

| Module | Priorité | Dépendances | Statut |
|--------|----------|-------------|--------|
| **2.1** Export PDF (**fpdf2**) | P0 | Phase 1 complète | ✅ 2026-09-05 — `GET /export/proposals/{id}.pdf` + bouton Propositions |
| **2.2** Export Word (python-docx) | P0 | Phase 1 complète | ✅ 2026-09-05 — `GET /export/proposals/{id}.docx`, contenu partagé avec le PDF |
| **2.3** Archives view frontend | P1 | Phase 1 | ✅ 2026-09-05 — frontend seul, aucun endpoint nouveau |
| **2.4** Archivage avancé (batch, filtre) | P1 | Phase 1 | 📅 |
| **2.5** Migration M365/Entra ID | P2 | Phases 0-2 stables | 📅 |
| **2.6** Tests Phase 2 | P1 | Chaque module | 📅 |

---

## Séquencement recommandé

```
Semaine 1 : 1b (SchoolRegistry + scraper adapters + SchoolCourse + MarketScanRun)
            + UX sidebar (structure seule, composants vides)
Semaine 2 : 1b (Promouvoir + scanner orchestrator)
            + UX Dashboard hub (sans données dynamiques)
Semaine 3 : 1c (GapAnalysisService + ClosureScorer + CreationScorer + GapRecommendation)
            + connexion UX aux données réelles
Semaine 4 : UX final (badges live, one-click actions, polish)
            + tests intégration bout-en-bout
```

## Jalons

| Jalon | Date cible | Livrables |
|-------|-----------|-----------|
| M0 — Phase 0 | ✅ Terminé | Auth, CRUD, import, dashboard |
| M1a — Phase 1a | ✅ Terminé | CRUD frontend, estimation, certification, favoris, design |
| M1b — Phase 1b | ✅ 2026-06-27 | Multi-school scraper (5 adaptateurs), SchoolRegistry, SchoolCourse, scan/diff |
| M1c — Phase 1c | ✅ 2026-06-27 | Gap Analysis, recommandations fermeture/création |
| MUX — Refonte UX | ✅ 2026-06-27 | Navigation hiérarchique, dashboard hub, badges |
| MD — Dettes techniques | ✅ 2026-09-05 | Alembic reconstruit, SSRF sitemap fermé, docs à jour |
| M2 — Phase 2 | 🔜 prochaine | Export PDF/Word + archivage avancé |
| M3 — Production | TBD | Migration M365/Entra ID |

---

## Conventions de branche

- `master` — stable
- `feat/<module>` — branches feature (ex: `feat/school-registry`, `feat/gap-analysis`, `feat/ux-refont`)
- Commits en Conventional Commits (caveman style)
