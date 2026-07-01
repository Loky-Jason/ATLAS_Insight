# ATLAS_Insight — Règles projet (lu à chaque session)

Dashboard décisionnel pédagogique SCAP.paris. Voir `docs/SPEC.md` (source de vérité).

## Emplacement
- Tout le projet vit dans `E:\GitKraken\ATLAS_Insight` exclusivement.

## Stack
- Frontend : React + Vite + TypeScript, Tailwind, shadcn/ui, Recharts.
- Backend : FastAPI + SQLAlchemy 2.0 + Pydantic v2, Python 3.11+.
- Base : SQLite chiffrée. Auth comptes locaux (argon2 + JWT httpOnly).
- Interpréteur : `python` (jamais `python3`).

## Règles
- UI **français**, code/identifiants **anglais**.
- Type hints obligatoires (Python + TS strict).
- Exceptions gérées sur toutes les I/O (fichier, réseau, DB).
- Sécurité : jamais de mot de passe en clair, DB chiffrée, JWT httpOnly,
  actions destructives = confirmation + AuditLog.
- Suppression côté serveur : soft-delete / archivage par défaut.
- Design : `ui-ux-pro-max` puis relecture `impeccable` avant livraison ;
  `emil-design-eng` pour toute animation.
- Léger : pas d'Electron, bundle minimal (PC peu performants).

## Commandes
```
# backend
cd backend && python -m venv .venv && .venv\Scripts\activate && pip install -e .
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
# frontend (si npm échoue pour cause de execution policy PowerShell)
#   → utiliser cmd /c "cd frontend && npm run dev"
cd frontend && npm install && npm run dev

# tests
cd backend && python -m pytest -v
cd backend && python -m pytest tests/ -v -k "not integration"  # unit only
cd backend && python -m alembic upgrade head   # migrations DB
cd backend && python -m alembic current        # état migration

# frontend
cd frontend && cmd /c "npx vitest run"
cd frontend && cmd /c "npm run typecheck"
```

## Sessions
### Session 1 (2026-07-01) — Scraper générique + test connexion config
- `GenericScraperAdapter` : mode sitemap/list, JSON-LD + sélecteurs CSS fallback
- Config scraper stockée dans `school_registries.config` (colonne JSON)
- `POST /schools/test-connection` : teste l'URL avant sauvegarde (anti-SSRF)
- Feedback visuel : scanMsg (succès/erreur) + connError dans dialog config
- ICAN Design : config corrigée en mode sitemap
- Tests : 307 backend, 71 frontend — tout vert

### Session 2 (2026-07-01) — Pages recommandations (fermeture / création)
- Composant partagé `GapRecommendationsList` (fermeture + création)
- Backend : `GET /gap-recommendations/{id}`, `POST /{id}/approve`, `POST /{id}/reject`
- Backend : `GET /gap-recommendations/closure-candidates` et `/creation-suggestions`
- Fix DB : colonne `creation_key` manquante + migration idempotente `662f6fe18004`
- Fix critique : rendu des certifications (`{label,type}` objets JSON)
- Fix : `suggested_hours=0` n'était plus masqué, grammaire FR, mapping statut `implemented`
- Guard : approve/reject refusés si statut ≠ `draft` (HTTP 409)
- Perf analyse d'écart : similarité par tokens + thread worker (remplace `difflib` O(n²))
- Graph connaissance mis à jour : 933 nœuds, 8103 arêtes, 122 fichiers
- Tests : 325 backend, 88 frontend, TS clean — tout vert
