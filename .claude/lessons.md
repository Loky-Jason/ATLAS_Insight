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
