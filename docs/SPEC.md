# ATLAS_Insight — Spécification produit

> Dashboard décisionnel pour coordinateur pédagogique SCAP.paris (Mairie de Paris).
> Objectif : décider chaque année quels cours fermer / ouvrir, en croisant les stats
> internes SCAP avec une veille marché automatisée.

## 1. Persona & objectif

Coordinateur pédagogique (20 ans d'expérience). Veut un outil qui :
- visualise les cours SCAP populaires / impopulaires,
- agrège une veille marché (autres écoles parisiennes, tendances),
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
| Veille | Recherche web automatisée côté backend (WebSearch/LLM), validation humaine |
| Export | **PDF** (WeasyPrint) + **Word** (.docx, python-docx) |
| Estimation heures/certif | Module auto par comparaison (pas de référentiel fourni) |
| Langue | UI **français**, code **anglais** |
| Contrainte | Léger, PC peu performants → pas d'Electron, bundle minimal |

## 3. Modèle de données (entités principales)

- **User** : id, email, password_hash (argon2), role, created_at.
- **Course** (cours SCAP) : id, title, category, status (`active|archived`),
  enrolled_count, dropout_count, age_brackets (JSON), year, hours_estimated,
  popularity_score (calculé), source=`scap`, notes, created_at, updated_at.
- **MarketCourse** (veille) : id, title, school, source_url, summary,
  relevance_score, why_it_works (texte), related_scap_course_id (nullable),
  discovered_at, status (`candidate|reviewed|adopted|rejected`).
- **CourseProposal** : id, title, description, hours_estimated,
  certification_suggestions (JSON: RNCP/open badge), based_on (JSON refs),
  status (`draft|proposed|exported`), created_at.
- **AuditLog** : id, user_id, action, target, timestamp (journalisation actions destructives).

## 4. Fonctionnalités (mapping prompt → modules)

| Prompt | Module |
|---|---|
| Dashboard infographie populaires/impopulaires | `frontend/dashboard` + `backend/analytics` |
| Archivage cours (historique) | `Course.status=archived` + vue archives |
| Infographie veille (sources + explication + pertinence) | `MarketCourse` + vue veille |
| Connexion par identifiants | `backend/auth` |
| Sécurité des données | chiffrement DB + JWT httpOnly + audit log |
| Estimation heures cours proposé | `backend/estimation` |
| Titres certif (RNCP, open badge) | `backend/certification` (suggestions) |
| Export cours proposés | `backend/export` (PDF + docx) |
| Accès rapide cours enregistré | recherche/filtre + favoris |
| Édition données pour ajustement | CRUD éditable sur Course/MarketCourse/Proposal |

## 5. Sécurité (non négociable)

- Mots de passe : argon2, jamais en clair.
- DB chiffrée au repos.
- JWT en cookie httpOnly + SameSite, pas de token en localStorage.
- Toutes les I/O (fichiers, réseau, DB) en try/except + log.
- Actions destructives (suppression, archivage massif) : confirmation + AuditLog.
- Dépendances tierces : sécurisées et à jour (pin versions, audit).

## 6. Phasage

- **Phase 0 (cette session)** : scaffolding, auth, modèle de données, import Excel/CSV,
  shell dashboard, 1 graphe popularité.
- **Phase 1** : veille auto (recherche web), estimation heures, suggestions certif.
- **Phase 2** : export PDF/docx, archivage avancé, migration M365/Entra ID.

## 7. Structure projet

```
ATLAS_Insight/
  backend/
    app/
      core/        # config, sécurité, db
      models/      # SQLAlchemy
      schemas/     # Pydantic
      api/         # routers FastAPI
      services/    # import, analytics, estimation, veille, export
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
