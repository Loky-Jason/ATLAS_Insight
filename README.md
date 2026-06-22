# ATLAS_Insight

Dashboard décisionnel pour la coordination pédagogique **SCAP.paris** (Mairie de Paris).

Croise les statistiques internes des cours SCAP avec une **veille marché automatisée**
pour décider chaque année quels cours fermer et quels nouveaux cours ouvrir.

## Fonctionnalités

- 📊 Dashboard : cours populaires / impopulaires (infographies)
- 🔍 Veille marché auto (autres écoles, tendances) avec sources + pertinence
- 🗄️ Archivage des anciens cours (historique)
- ⏱️ Estimation auto du nombre d'heures
- 🎓 Suggestions de certification (RNCP, open badge)
- 📤 Export PDF / Word des cours proposés
- ✏️ Édition des données, accès rapide aux cours enregistrés
- 🔐 Connexion par identifiants, données chiffrées

## Stack

Web app locale — React/Vite/TypeScript + FastAPI/SQLite. Légère, migrable Microsoft 365.

Voir [docs/SPEC.md](docs/SPEC.md) pour la spécification complète.

## Démarrage

```bash
# Backend
cd backend && python -m venv .venv && .venv\Scripts\activate
pip install -e . && uvicorn app.main:app --reload

# Frontend
cd frontend && npm install && npm run dev
```
