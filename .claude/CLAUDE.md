# ATLAS_Insight — Règles projet

Dashboard décisionnel pédagogique SCAP.paris. Voir `docs/SPEC.md` (source de vérité).

**Type:** fullstack
**Created:** 2026-06-24

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
- Sécurité : jamais de mot de passe en clair, DB chiffrée, JWT httpOnly, actions destructives = confirmation + AuditLog.
- Suppression côté serveur : soft-delete / archivage par défaut.
- Design : `ui-ux-pro-max` puis relecture `impeccable` avant livraison ; `emil-design-eng` pour toute animation.
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
cd backend && python -m alembic upgrade head   # migrations DB
cd backend && python -m alembic current        # état migration
```

## Workflow
1. spec before coding
2. plan tasks
3. delegate to subagents
4. review + update lessons.md
5. ship

## Communication
- Mode **caveman** global actif : réponses ultra-compressées (~75% tokens)
- Commandes : `/caveman lite|full|ultra`, `/caveman-help`
- Commits en style caveman (Conventional Commits, sujet ≤50 car.)

## Délégation subagents
- Avant de coder, vérifier si un subagent (`~/.claude/agents/*.md`) correspond à la tâche
- Tâche complexe multi-étapes → orchestrer via `ruflo-swarm` ou `agent-organizer`
- Tâche ciblée → lancer le subagent dédié (ex. `fastapi-developer`, `react-specialist`)
- Compétence atomique → agent-skills (`/spec`, `/plan`, `/review`, `/ship`)

## Plugins/Skills actifs
- **code-review-graph** (hook session)
- **ruflo-wrapper** (orchestration swarm)
- **agent-skills** (/spec, /plan, /review, /ship)
- **ui-ux-pro-max** + **impeccable** + **emil-design-eng** (design)
- **karpathy-guidelines** + **humanizer** (qualité)
