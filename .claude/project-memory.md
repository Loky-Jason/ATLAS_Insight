# Memory — ATLAS_Insight v2
**Last:** 2026-07-01 — Reprise handoff OpenCode : cartes reco affichent titre+description cours (props calculées `course_title`/`course_description` sur GapRecommendation, selectinload anti-N+1) ; + commits OpenCode intermédiaires (GenericScraperAdapter, test-connection avant save, cookie SameSite=lax, stratégies dynamiques, WAL SQLite). Poussé `d18108b`. **Backend 325 tests**, **front 89 vitest**, tsc clean. Prochaine : **Phase 2** (export PDF/Word, archives) ; dette Alembic demi-mesure à trancher (voir tasks/HANDOFF_OPENCODE.md §A) + perf gap_service O(n²).

## Durcissement revue Phase 1b/1c (2026-06-26)
- **B1** `gap_service` : recommandations "creation" s'écrasaient toutes en 1 ligne (filtre upsert trop large) → colonne `creation_key` + insertion sans discriminant. Régression `tests/test_gap_service.py`.
- **B2** `gap_service` : datetime naïf/aware → helper `_as_utc` (aware UTC des 2 côtés, safe SQLite+Postgres). Corrige la "solution" naïve d'OpenCode (cassait à la migration Postgres).
- I/O scrapers : try/except `httpx.HTTPError`→`RuntimeError`, borne `MAX_PAGES=200`, `_safe_close`.
- Sécu : `app/core/url_safety.py` (anti-SSRF, `field_validator` schéma school) ; AuditLog sur create/update/scan school + gap analyze/approve ; `error_msg` générique `/diff`.
- `_compute_hash` étendu (durée/prix/desc/catégorie/format/certif). Lint : forward-refs models `TYPE_CHECKING`, `== True/False`→`.is_()`.

## État pour reprise
- **Phase 0** ✅, **1a** ✅, **1b** ✅ (scraper engine multi-vendeurs : SchoolRegistry/SchoolCourse/MarketScanRun ; `BaseScraperAdapter` httpx+sitemap+bornes ; adaptateurs **SCAP/Stub/ORSYS/Cegos/Demos** ; ScannerService diff hash ; endpoints schools CRUD/scan/diff/counts ; UI Écoles/Scans/Journal), **1c** ✅ (gap engine : GapRecommendation+`creation_key`, Closure/Creation scorers 5 facteurs, endpoints analyze/candidates/suggestions/approve/list, UI À fermer/À créer), **UX** ✅ (sidebar hiérarchique, dashboard hub badges, redirections, MarketWatch retiré).
- Datetime tz : **`_as_utc` (aware UTC des 2 côtés)** — remplace l'ancien fix naïf `datetime.now()` qui cassait à la migration Postgres. NE PAS revenir au naïf.
- `scraper_strategy` défaut = **`stub`** (enregistré ; "html" n'existe pas → 500 sinon).
- **Prochaine session : Phase 2** — export PDF (WeasyPrint) + Word (python-docx), vue Archives, archivage avancé. Avant : optimiser perf `gap_service` O(n²)+N+1 (chip `task_8aa9a344`, [[project-atlas-gap-perf]]).
- Fragilité scraping (ponytail, non bloquant) : filtre sitemap `/formation/` hardcodé partagé (orsys+demos) + `<loc>` suivis sans allowlist → durcir au branchement scan réel.
- Lancer en local : backend `cd backend && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` ; frontend `cd frontend && npm install && npm run dev` (port 5173). Admin : `admin@scap.paris` / `admin2026`.
- Migrations DB : `cd backend && python -m alembic upgrade head` (Alembic initialisé le 28/06, première migration `initial_schema`).
- PowerShell note : si npm bloqué par execution policy, utiliser `cmd /c "cd frontend && npm run dev"`.
- Règle process : après chaque sprint front+back, faire un **run d'intégration réel** (serveurs lancés + parcours navigateur) — les sous-agents valident build/pytest, pas le runtime câblé.

## Session 2026-06-28 — Fix review 6 issues
- **🔴 1** `school_registry_id` absente table SQLite → `ALTER TABLE market_courses` + vérif migration
- **🟡 2** Reset password admin sans AuditLog → insertion manuelle + commit
- **🟡 3** Aucune migration DB → **Alembic installé**, env.py async→sync, `initial_schema` stampée
- **🟡 4** `school_registry_id` jamais propagé dans `market_service.run_market_scan` → lookup SchoolRegistry par nom d'école
- **🟢 5** Contournement PowerShell non documenté → ajouté à CLAUDE.md
- **🟢 6** Backend exposé sur `0.0.0.0` → `127.0.0.1` dans CLAUDE.md
- Backend **256 tests OK**, graph rebuild incrémental (19 nodes, 136 edges)

## Architecture

### Backend — FastAPI async
- `app/core/` — config (pydantic-settings), DB (SQLAlchemy async + aiosqlite), security (argon2 + JWT)
- `app/models/` — 9 entités : User, Course, MarketCourse, CourseProposal, AuditLog, Favorite, SchoolRegistry, SchoolCourse, MarketScanRun, GapRecommendation
- `app/schemas/` — Pydantic v2 (Create/Update/Read par entité) + `analytics.py` + `gap_recommendation.py`
- `app/api/` — 12 routers : analytics, audit_logs, auth, certification, courses, estimate, favorites, imports, market, market_courses, proposals, **schools**, **school_courses**, **scan_runs**, **dashboard**, **gap_recommendations**
- `app/services/` — analytics, import, estimation (difflib), certification (14 règles), market (StubProvider déprécié), **scanner_service**, **gap_service** (ClosureScorer + CreationScorer)
- `app/scrapers/` — adapters scraper : **base.py** (ABC + registry), **scap.py** (httpx sync), **stub.py** (mock data)
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
| **Gap analysis : 5 facteurs pondérés (Closure + Creation)** | Phase 1c | schools_validation 30%, category_gap 25%, cert_potential 15%, no_scap_equivalent 15%, recent_discovery 10%. Seuil 40%, est. heures via difflib |
| **datetime.now() sans timezone pour SQLite** | Phase 1c | SQLite stocke naive — `datetime.now(timezone.utc)` crashe les comparaisons temporelles en pass2 |
| **transition-all → transition sur composants UI** | Review Phase 1c | Perf PC Mairie : set Tailwind default (color/bg/opacity/shadow/transform) suffit |
| **Anim tokens CSS vars liés aux classes Tailwind** | Review Phase 1c | `duration-[var(--duration-normal)]`, `ease-[var(--ease-out)]` connectent tokens emil-design-eng |
