# ATLAS_Insight — Spécification produit

> Dashboard décisionnel pour coordinateur pédagogique SCAP.paris (Mairie de Paris).
> Objectif : décider chaque année quels cours fermer / ouvrir, en croisant les stats
> internes SCAP avec une veille multi-écoles automatisée.

## 1. Persona & objectif

Coordinateur pédagogique (20 ans d'expérience). Veut un outil qui :
- visualise les cours SCAP populaires / impopulaires,
- agrège une veille marché (autres écoles parisiennes, tendances) via scrapping réel,
- détecte automatiquement les changements chez les concurrents (nouveaux cours, suppressions, modifications),
- propose des recommandations de fermeture/création avec score et justification,
- propose de nouveaux cours pertinents avec estimation d'heures et pistes de certification,
- permet d'archiver, éditer, exporter, retrouver rapidement les cours.

## 2. Décisions d'architecture (verrouillées)

| Sujet | Décision |
|---|---|
| Type | Web app **locale** (navigateur), migrable M365/Azure plus tard |
| Frontend | React + Vite + TypeScript, Tailwind, shadcn/ui, Recharts |
| Backend | FastAPI (Python 3.11+), SQLAlchemy 2.0, Pydantic v2 |
| Base | SQLite (fichier local). Chiffrement au repos = **BitLocker** (disque OS, standard parc Mairie) ; PAS SQLCipher (wheels Windows fragiles). Champ-chiffré AES-GCM ciblé seulement si clause contractuelle l'exige. Azure gère l'at-rest nativement après migration |
| Auth | Comptes locaux, hash **argon2** (argon2-cffi), sessions JWT httpOnly |
| Import données | Excel/CSV via pandas + openpyxl |
| Veille | Scrapping multi-écoles via adapters dédiés (registre d'écoles, 1 classe par école) |
| Gap Analysis | Moteur automatique croisant cours SCAP × marché, avec scores pondérés |
| Export | **PDF** (WeasyPrint) + **Word** (.docx, python-docx) |
| Estimation heures/certif | Module auto par comparaison (pas de référentiel fourni) |
| Langue | UI **français**, code **anglais** |
| Contrainte | Léger, PC peu performants → pas d'Electron, bundle minimal |

## 3. Modèle de données (entités)

### Existantes (Phase 0 + 1a)

- **User** : id, email, password_hash (argon2), role, created_at.
- **Favorite** : id, user_id (FK users), course_id (FK courses, nullable), market_course_id (FK market_courses, nullable), created_at (marquage rapide de cours/veille suivis).
- **Course** (cours SCAP) : id, title, category, status (`active|archived`), enrolled_count, dropout_count, age_brackets (JSON), year, hours_estimated, popularity_score (calculé), source=`scap`, notes, created_at, updated_at.
- **MarketCourse** (veille curatée) : id, title, school (string fallback), school_registry_id (FK, nullable), source_url, summary, relevance_score, why_it_works, related_scap_course_id (nullable), discovered_at, status (`candidate|reviewed|adopted|rejected`).
- **CourseProposal** : id, title, description, hours_estimated, certification_suggestions (JSON: RNCP/open badge), based_on (JSON refs), status (`draft|proposed|exported`), created_at.
- **AuditLog** : id, user_id, action, target, timestamp (journalisation actions destructives).

### Nouvelles (Phase 1b — Veille multi-écoles)

- **SchoolRegistry** : id, name, url, scraper_strategy (`html|json_api|rss`), active (bool), scan_interval (int, minutes), last_scanned_at (nullable), created_at. Permet d'ajouter/supprimer une école sans coder.
- **SchoolCourse** (données brutes scrappées) : id, school_registry_id (FK), external_id, title, url, description, duration_hours, price, category, format, certification, content_hash (hash title+URL pour détection modifs), first_seen_at, last_seen_at, last_updated_at, is_removed (bool), removed_at (nullable). Reflet exact du catalogue d'une école à un instant T.
- **MarketScanRun** (audit trail) : id, school_registry_id (FK), status (`running|completed|failed`), started_at, finished_at, courses_found, courses_new, courses_removed, courses_modified, error_msg (nullable).

### Nouvelles (Phase 1c — Gap Analysis)

- **GapRecommendation** : id, recommendation_type (`closure|creation`), scap_course_id (FK, nullable), market_course_id (FK, nullable), score (0-100), score_breakdown (JSON structuré Pydantic), schools_offering (JSON), suggested_hours, certification_suggestions, rationale (texte lisible), status (`draft|approved|rejected|implemented`), created_at.

### Relations clés

```
SchoolRegistry ──1:N── SchoolCourse (raw data per school)
SchoolRegistry ──1:N── MarketScanRun (scan history)
SchoolRegistry ──?── MarketCourse (via school_registry_id FK optionnelle)

SchoolCourse ──promotion──→ MarketCourse (curated, status="candidate")
                              ↑ réutilise _compute_relevance() existant

GapRecommendation (approved)
  ├ type=creation → CourseProposal (draft, based_on recommandation.id)
  └ type=closure  → Course.status="archived" + AuditLog
```

## 4. Fonctionnalités (mapping prompt → modules)

| Prompt | Module |
|---|---|
| Dashboard infographie populaires/impopulaires | `frontend/dashboard` + `backend/analytics` |
| Import cours Excel/CSV | `backend/imports` + `frontend/import` |
| Archivage cours (historique) | `Course.status=archived` + vue archives |
| Infographie veille (sources + explication + pertinence) | `MarketCourse` + vue veille |
| Détection changements concurrents | SchoolCourse (hash) + MarketScanRun + diff |
| Recommandations fermeture/création | GapAnalysisService + GapRecommendation |
| Connexion par identifiants | `backend/auth` |
| Sécurité des données | chiffrement DB + JWT httpOnly + audit log |
| Estimation heures cours proposé | `backend/estimation` |
| Titres certif (RNCP, open badge) | `backend/certification` (suggestions) |
| Export cours proposés | `backend/export` (PDF + docx) |
| Accès rapide cours enregistré | recherche/filtre + favoris (`Favorite`) |
| Édition données pour ajustement | CRUD éditable sur Course/MarketCourse/Proposal |

## 5. Sécurité (non négociable)

- Mots de passe : argon2, jamais en clair.
- DB chiffrée au repos.
- JWT en cookie httpOnly + SameSite, pas de token en localStorage.
- Toutes les I/O (fichiers, réseau, DB) en try/except + log.
- Actions destructives (suppression, archivage massif) : confirmation + AuditLog.
- Dépendances tierces : sécurisées et à jour (pin versions, audit).

## 6. Phasage

| Phase | Contenu | Statut |
|-------|---------|--------|
| **Phase 0** | Scaffolding, auth, modèle initial, import, dashboard basique | ✅ Terminé |
| **Phase 1a** | CRUD frontend, estimation, certification, favoris, WebMarketProvider SCAP, design pass | ✅ Terminé |
| **Phase 1b** | Veille multi-écoles : SchoolRegistry, SchoolCourse, Scraper Adapters, MarketScanRun, promotion | 📝 Planifié |
| **Phase 1c** | Gap Analysis : Closure Scorer, Creation Scorer, GapRecommendation, workflow post-approbation | 📝 Planifié |
| **Phase UX** | Navigation hiérarchique, dashboard hub, badges, one-click actions | 📝 Planifié |
| **Phase 2** | Export PDF/docx, archivage avancé, migration M365/Entra ID | 📅 Plus tard |

## 7. Structure projet

```
ATLAS_Insight/
  .claude/         # Règles projet, lessons, mémoire session
  specs/           # Spécifications par module
  tasks/           # Roadmap + todo
  backend/
    app/
      core/        # config, sécurité, db
      models/      # SQLAlchemy
      schemas/     # Pydantic
      api/         # routers FastAPI
      services/    # import, analytics, estimation, veille, export
      scrapers/    # Adapters par école (SCAP, ORSYS, Cegos, Demos…)
    tests/
    pyproject.toml
  frontend/
    src/
      components/
      pages/
      lib/
    package.json
  data/            # SQLite (gitignored)
  docs/
```
