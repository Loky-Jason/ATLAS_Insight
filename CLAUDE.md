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
uvicorn app.main:app --reload
# frontend
cd frontend && npm install && npm run dev
```
