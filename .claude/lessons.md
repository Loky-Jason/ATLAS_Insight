# Lessons — ATLAS_Insight
**Updated:** 2026-06-26 — session 4

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

## 2026-06-25 — Verrouiller les contrats API avec response_model
### Contexte
Review du correctif analytics : endpoint renvoyait `dict[str, Any]` sans schéma
### Problème
Sans `response_model`, la forme de la réponse peut dériver sans alerte (cause initiale du bug front/back). `.env.example` frontend pointait aussi sur `:8000` sans `/api/v1`
### Solution
Schéma Pydantic `AnalyticsPopularity`/`PopularityEntry` + `response_model` sur `/analytics/popularity` ; `.env.example` corrigé vers `/api/v1`
### Règle
Tout endpoint consommé par le front DOIT avoir un `response_model` Pydantic (verrou de contrat + OpenAPI). Les `.env.example` doivent contenir une valeur fonctionnelle telle quelle.

## 2026-06-25 — Review subagent : 3 corrections post-livraison WebMarketProvider
### Contexte
Sub-agent `review-changes` a audité les modifs Phase 1b (WebMarketProvider). A remonté 5 issues dont 3 mineures skippées puis re-corrigées sur demande.
### Problème
(1) `requests` ajouté comme dep alors que `httpx` déjà en dev-deps ; (2) `query` param marqué `# noqa: ARG002` jamais forwardé à l'API SCAP ; (3) Session HTTP jamais close (ressource leak mineur)
### Solution
(1) `requests`→`httpx` (promu en dep principale) ; (2) `query` passé comme `Keywords` dans le payload SCAP via `_fetch_page(page, query)` ; (3) `close()` abstrait dans ABC + implémenté Stub (pass) / Web (`self._http.close()`)
### Règle
Un sub-agent de review peut skipper des issues pour trade-off explicables, MAIS toujours demander confirmation avant de les laisser non corrigées. Parfois le skip est juste de la paresse.

## 2026-06-25 — Décisions roadmap v2 (multi-école + gap analysis + UX)
### Contexte
Extension du scope : remplacer la veille mono-source SCAP par un système multi-école avec gap analysis automatisée.
### Problème
11 issues soulevées par sous-agents de validation : double pipeline concurrent (ancien MarketSearchProvider vs nouveau ScraperAdapter), conflit MarketCourse.school (string vs FK), endpoint /ui/counts hors convention, scoring non défini dans le nouveau pipeline, checksum SHA-256 surdimensionné.
### Solution
5 décisions validées ensemble : (1) Déprécié MarketSearchProvider → SCAP réécrit en ScraperAdapter, (2) MarketCourse.school_registry_id FK + string fallback legacy, (3) endpoint /dashboard/counts plutôt que /ui/counts, (4) scoring à la promotion SchoolCourse→MarketCourse via _compute_relevance() existant, (5) content hash title+URL simple au lieu de SHA-256.
### Règle
Avant de restructurer un pipeline d'ingestion, valider par sous-agents les conflits avec l'existant (modèles, endpoints, conventions). Les décisions de transition (dépréciation, migration FK, conventions naming) doivent être documentées dans ROADMAP.md + project-memory.md avant l'implémentation.

## 2026-06-26 — Phase 1c : datetime naive/aware dans gap service
### Contexte
GapAnalysisService._pass2_creation() compare first_seen_at (SQLite) avec cutoff_30d (datetime.now(timezone.utc))
### Problème
SQLite stocke les datetimes sans timezone (offset-naive), datetime.now(timezone.utc) est offset-aware. La comparaison `>=` lève `TypeError: can't compare offset-naive and offset-aware datetimes`, rollback la transaction entière → aucune recommandation persistée.
### Cause
Ligne #330 de gap_service.py utilisait `datetime.now(timezone.utc)` par habitude d'UTC, sans réaliser que SQLAlchemy/SQLite renvoie des naives.
### Solution
Remplacé par `datetime.now()` (naive) — cohérent avec le format SQLite. La pass1 closure n'était pas touchée car elle ne fait pas de comparaison temporelle.
### Règle
Dans un projet SQLite (pas de timezone en base), utiliser `datetime.now()` sans timezone pour toutes les comparaisons temporelles internes. Ne mélanger naive et aware que si la base stocke explicitement des timezone.

## 2026-06-26 — transition-all sur UI boutons/nav/cards (PC Mairie)
### Contexte
Review impeccable a détecté `transition-all` sur boutons, nav links et cards dashboard — fait transiter toutes les propriétés (width, height, padding…), pas seulement celles qui changent.
### Problème
Inutile sur les PC Mairie visés (bas de gamme) : `transition-all` force le navigateur à écouter les changements de toutes les propriétés animables, gaspillage CPU/GPU pour des éléments qui ne changent que color/bg/transform.
### Solution
Remplacé par `transition` (Tailwind default property set), `duration-[var(--duration-normal)]`, `ease-[var(--ease-out)]`. Progress bar → `transition-[width,background-color]` explicite car width n'est pas dans le default set.
### Règle
Ne pas utiliser `transition-all` sur les composants d'UI fréquents. Préférer `transition` (set par défaut : color, bg, opacity, shadow, transform) ou un set explicite. Lier `duration-*` et `ease-*` aux tokens CSS quand ils existent (`--duration-normal`, `--ease-out`).
