# Lessons — ATLAS_Insight
**Updated:** 2026-06-24 — session 2

## Format
Chaque entrée suit le template :
- Contexte → Problème → Cause → Solution → Règle

## 2026-06-24 — SECRET_KEY faible en dev
### Contexte
Premier commit avec clé par défaut "CHANGE_ME"
### Problème
Averti par le code mais pas de mécanisme de refus
### Cause
Validation `model_validator` n'existait pas encore
### Solution
Ajout validation pydantic qui refuse/bloque selon environnement
### Règle
Valider les secrets côté config, pas seulement en commentaire

## 2026-06-24 — Timing attack sur login
### Contexte
Endpoint login — vérification email puis mot de passe
### Problème
Si email inconnu, réponse plus rapide que si email connu mais mauvais password
### Cause
Vérification password skipée quand user est None
### Solution
Hash bidon systématique + vérification constante en temps (E2)
### Règle
Toujours égaliser le temps de vérification auth, quelle que soit l'existence du compte

## 2026-06-24 — PowerShell ExecutionPolicy bloque scripts
### Contexte
Lancer `init-project.ps1` pour scaffolding projet
### Problème
Script bloqué par execution policy (PSSecurityException)
### Cause
PowerShell 5.1 par défaut en Restricted sur Windows 11
### Solution
`powershell -ExecutionPolicy Bypass -File script.ps1 <args>`
### Règle
Toujours préfixer les appels PowerShell avec `-ExecutionPolicy Bypass` sur machines verrouillées

## 2026-06-24 — Cohérence croisée docs planification
### Contexte
Maintenir SPEC.md + ROADMAP.md + todo.md en parallèle
### Problème
ROADMAP.md listait `market_veille.py` mais todo.md listait `market_service.py` — même service, noms différents
### Cause
Écriture indépendante des fichiers sans vérification croisée
### Solution
Vérification systématique des refs entre fichiers après chaque MAJ : chemins, noms de services, jalons
### Règle
Tout changement dans un fichier de planification doit être répercuté dans les autres documents liés

## 2026-06-24 — CSV injection dans l'import
### Contexte
Import Excel/CSV — upload fichier utilisateur
### Problème
Cellules commençant par `=`, `+`, `-`, `@` exécutées comme formules par Excel
### Cause
Pas de nettoyage des valeurs textuelles importées
### Solution
Prefix `'` automatique sur les valeurs commençant par un opérateur de formule (E3b)
### Règle
Neutraliser les formules Excel à l'import, pas seulement valider les types

## 2026-06-25 — Validation cross-champ Pydantic v2
### Contexte
Schema Favorite : contrainte « exactement une des 2 FK (course_id / market_course_id) renseignée »
### Problème
`field_validator` ne voyait pas les autres champs → contrainte impossible à vérifier
### Cause
En Pydantic v2, un `field_validator` par champ s'exécute avant que les autres champs soient validés
### Solution
`model_validator(mode="after")` qui a accès à l'instance complète
### Règle
Toute contrainte portant sur plusieurs champs → `model_validator(mode="after")`, jamais `field_validator`

## 2026-06-25 — Conflit starlette / FastAPI
### Contexte
Sprint backend Phase 1 — lancement pytest
### Problème
Starlette 1.3.1 (tiré par `mcp`) incompatible FastAPI 0.115.12 ; tests cassés
### Cause
Dépendance transitive non épinglée, version majeure incompatible installée dans l'env
### Solution
`starlette>=0.41,<1.0` épinglé dans `pyproject.toml`
### Règle
Épingler les dépendances transitives critiques (starlette sous FastAPI) pour isoler l'env des conflits MCP/outils

## 2026-06-25 — Review Phase 1 : dérive doc/code dans services
### Contexte
Review 5 axes des services estimation/certification/market
### Problème
`certification_service` : commentaire promettait un bonus catégorie +0.15 jamais implémenté ; variable `cat_hint` contenait en fait le regex (col. 2 toujours None). `market_service._compute_relevance` : docstring (+0.5/+0.3 titre) ≠ code (+0.3/-0.4)
### Cause
Docstrings/commentaires écrits sur une intention initiale, code livré différent, jamais resynchronisés
### Solution
Renommé `cat_hint`→`pattern`, commentaires alignés sur le code réel, docstring scoring corrigée. 121/121 toujours verts
### Règle
Docstring = contrat : toute logique de scoring/règles doit décrire EXACTEMENT le code livré, pas l'intention. Vérifier à la review.

## 2026-06-25 — Suggestions review appliquées (estimation + scan 201)
### Contexte
Finalisation review Phase 1 : cap `basis`, seuil similarité, code HTTP scan
### Problème
`basis` non borné (affichage Proposals), seuil `_MIN_SIMILARITY=0.20` trop permissif ; `/market/scan` renvoyait 200 alors qu'il crée des ressources
### Solution
`_MAX_BASIS=5` (tri desc + slice sur les 3 chemins), seuil monté à 0.35, scan → 201 ; 3 tests asserts 200→201 mis à jour
### Règle
Endpoint qui crée des ressources → 201. Toute liste renvoyée au front = bornée. Changer un code HTTP = MAJ les tests qui l'assertent dans la foulée.

## 2026-06-25 — Bugs d'intégration front/back jamais testés en live
### Contexte
Premier lancement réel (uvicorn + vite + preview navigateur) pour montrer l'app
### Problème
2 bugs invisibles aux tests unitaires/build : (1) `api.ts` BASE_URL=`http://localhost:8000` sans préfixe `/api/v1` → tous les appels 404 ; (2) `/analytics/popularity` renvoyait `{top, flop}` mais le front attendait `{most_popular, least_popular, total_courses, total_enrolled, total_dropouts}` → crash StatCard/PopularityChart (page blanche, pas d'error boundary)
### Cause
Backend et frontend codés par sous-agents séparés, contrats jamais confrontés en exécution réelle (agents ont validé build/pytest, pas le runtime bout-en-bout)
### Solution
BASE_URL→`/api/v1` ; backend analytics aligné sur le contrat front (most_popular/least_popular + agrégats via `get_totals`) + tests MAJ. Vérifié en live : login + dashboard + CRUD OK
### Règle
Après un sprint front+back en parallèle, faire UN run d'intégration réel (serveurs lancés + parcours navigateur) avant de déclarer livré. Le build vert ≠ le runtime câblé. Ajouter à terme une error boundary React + des tests de contrat (schémas partagés).
