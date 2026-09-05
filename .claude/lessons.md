# Lessons — ATLAS_Insight
**Updated:** 2026-07-01 — session 7

## 2026-06-27 — Scrapers multi-vendeurs : fragilité du filtre partagé
### Contexte
Ajout adaptateurs ORSYS/Cegos/Demos sur `BaseScraperAdapter` (httpx remonté dans la base, template `_fetch_all_from_sitemap`).
### Problème
Le filtre d'URLs sitemap `/formation/` est codé en dur dans `base._fetch_sitemap_urls`, partagé par orsys + demos (vendeurs aux schémas d'URL différents). Si un vendeur change de chemin → 0 cours, **silencieux** (juste un log). De plus les `<loc>` du sitemap sont suivis via `_http.get` sans allowlist d'hôte (SSRF-via-sitemap théorique).
### Cause
Mutualisation prématurée d'un détail (le path filter) qui n'est pas commun à tous les vendeurs.
### Solution
Laissé tel quel pour l'instant (marqué `ponytail:` dans le commit `ee117f0`) : tout I/O est wrappé try/except, dégrade à 0 cours + log, jamais de crash ; domaines https de confiance. Validable seulement contre les vrais sites.
### Règle
Un détail de parsing propre à un vendeur (path filter, sélecteur) ne se mutualise pas dans la base tant qu'il n'est pas prouvé commun. Préférer un override par adaptateur ou un paramètre. Un scraper qui peut renvoyer 0 silencieusement doit logger explicitement le cas « sitemap non vide mais 0 URL retenue ».

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
~~Remplacé par `datetime.now()` (naive)~~ **CORRIGÉ 2026-06-26 (revue Phase 1b/1c) :** le naïf casse à la migration Postgres prévue (Postgres renvoie aware → re-TypeError). Solution robuste = normaliser **les deux côtés** en aware UTC avant comparaison via helper `_as_utc(dt)` (`dt.replace(tzinfo=UTC)` si naïf, sinon `astimezone(UTC)`). `now = datetime.now(UTC)`.
### Règle
Ne jamais comparer des datetimes dont l'awareness dépend du backend DB. Normaliser systématiquement en aware UTC au point de comparaison (helper `_as_utc`). Vaut pour SQLite (naïf) ET Postgres (aware) — indispensable vu la migration M365/Postgres au programme.

## 2026-06-26 — Revue Phase 1b/1c (scrapers + gap engine) : bugs non couverts par les tests
### Contexte
Revue (code-reviewer + security-auditor en sous-agents) du code OpenCode Phase 1b/1c. 133 tests verts + build vert, mais Phase 1c (gap_service, 534 lignes) avait **0 test** → bugs logiques/sécu latents.
### Problème
1. **Upsert "creation" s'écrasait en 1 ligne** : `_upsert_recommendation` filtrait seulement `type=="creation"` (scap/market_course_id None) → chaque cluster, via flush+select, écrasait la ligne du précédent. N opportunités → 1 ligne. 2 lignes coexistantes → `MultipleResultsFound`.
2. I/O réseau scrapers sans try/except (viole règle projet) ; pagination `while True` non bornée ; `scraper.close()` hors garde.
3. SSRF latent : `url` école = `str` libre, pas de garde http/https/IP interne.
4. AuditLog absent sur 4 mutations admin (create/update/scan school, gap analyze/approve).
5. `error_msg` httpx brut exposé à tout user via `/diff`.
6. Hash de changement sur `title|url` seul → modif prix/durée/desc jamais détectée.
### Cause
Feature livrée sans suite de tests dédiée ; tests existants ne couvraient pas le service gap ni les chemins d'erreur réseau.
### Solution
1. Colonne `creation_key` (titre représentatif normalisé) comme clé d'identité d'upsert ; insertion directe si aucun discriminant. + 3 tests régression `test_gap_service.py`.
2. try/except `httpx.HTTPError`→`RuntimeError` ; borne `MAX_PAGES=200` (`while/else`) ; helper `_safe_close`.
3. Helper `app/core/url_safety.py::validate_external_url` (schéma http/https, blocage loopback/privé/link-local/metadata) branché en `field_validator` sur le schéma school.
4. `_write_audit` ajouté aux 4 mutations ; `approve_recommendation(user_id)` + AuditLog.
5. `error_msg` générique côté API, détail gardé dans logs serveur.
6. `_compute_hash` couvre titre+url+durée+prix+catégorie+format+certif+description.
### Règle
Toute feature métier ⇒ suite de tests dédiée AVANT merge (surtout services purs logique, invisibles aux tests d'API). Tout I/O réseau ⇒ try/except + borne d'itération. Toute URL externe fournie par l'utilisateur ⇒ valider anti-SSRF au schéma. Toute mutation admin ⇒ AuditLog dans la même transaction. Clé d'upsert ⇒ discriminant explicite, jamais `scalar_one_or_none()` sur un filtre large.

## 2026-06-26 — transition-all sur UI boutons/nav/cards (PC Mairie)
### Contexte
Review impeccable a détecté `transition-all` sur boutons, nav links et cards dashboard — fait transiter toutes les propriétés (width, height, padding…), pas seulement celles qui changent.
### Problème
Inutile sur les PC Mairie visés (bas de gamme) : `transition-all` force le navigateur à écouter les changements de toutes les propriétés animables, gaspillage CPU/GPU pour des éléments qui ne changent que color/bg/transform.
### Solution
Remplacé par `transition` (Tailwind default property set), `duration-[var(--duration-normal)]`, `ease-[var(--ease-out)]`. Progress bar → `transition-[width,background-color]` explicite car width n'est pas dans le default set.
### Règle
Ne pas utiliser `transition-all` sur les composants d'UI fréquents. Préférer `transition` (set par défaut : color, bg, opacity, shadow, transform) ou un set explicite. Lier `duration-*` et `ease-*` aux tokens CSS quand ils existent (`--duration-normal`, `--ease-out`).

## 2026-07-01 — Props calculées reco : lazy async + duplication UI
### Contexte
Feature OpenCode : cartes recommandations affichent `course_title`/`course_description` (props calculées sur le modèle `GapRecommendation`). Review 5 axes.
### Problème
1. `course_title` (closure) lit `self.scap_course`. En SQLAlchemy **async**, un lazy load implicite lève `MissingGreenlet` → crash. Sûr uniquement grâce au `selectinload`, mais **aucun test** ne le couvrait (retirer le selectinload = tests verts, runtime cassé).
2. `course_description` (creation) construisait `"Proposé par X — Nh — certifs Z"` alors que la carte affiche DÉJÀ ces 3 infos (schools, badges heures/certifs) → triple redondance visuelle.
### Cause
Props de présentation ajoutées sans test de sérialisation, et sans vérifier ce que la carte rendait déjà.
### Solution
1. `course_description` retourne `None` pour creation (code mort retiré, commentaire `ponytail:` + chemin d'upgrade = stocker `rep.description` scrappée). Closure conservé (non redondant, `isClosure` masque les badges).
2. 2 tests : `test_closure_candidates_serialize_course_title` (échoue si selectinload retiré) + `test_creation_has_no_redundant_description`.
### Règle
Prop calculée qui lit une relation ⇒ TOUS les endpoints qui la sérialisent doivent `selectinload` la relation + 1 test qui casse si on l'enlève (lazy async ≠ lazy sync). Avant d'ajouter un champ d'affichage, vérifier que la vue ne le montre pas déjà ailleurs. Présentation (chaînes FR formatées) dans l'ORM = à éviter (core/ui), toléré ici tant que source unique.

## 2026-07-01 — "Erreur serveur" veille = serveurs éteints, pas un bug
### Contexte
User : "Impossible de charger les écoles / Erreur serveur." sur la page Veille.
### Problème
Réflexe = chercher un bug backend. Endpoint `GET /schools` testé isolément (query, sérialisation Pydantic, ASGI+login) → 200, 6 écoles, aucun défaut.
### Cause
Rien n'écoutait sur `:8000`/`:5173` (`netstat`). Backend/frontend jamais relancés après fermeture session. Front mappe l'échec réseau (connection refused) sur le message générique "Erreur serveur.".
### Solution
Relancer les 2 serveurs. Aucun changement de code.
### Règle
Avant de débugger un "Erreur serveur" front : `netstat -ano | grep :8000` d'abord. Serveurs liés à la session Claude → morts à la fermeture. Un 500 générique côté front peut être un simple connection-refused, pas une exception backend.

## 2026-09-04 — Alembic demi-mesure : 2 heads, schéma initial vide, base réelle non démarrable
### Contexte
Dette « Alembic demi-mesure » (HANDOFF §A). Décision client : reconstruire proprement plutôt que reverter, parce que le bug « colonne manquante sur base existante » s'était déjà produit 3 fois (`school_registry_id`, `creation_key`, `config`) et exigeait un ALTER TABLE manuel à chaque fois.
### Problème
1. `alembic upgrade head` **échouait** : `662f6fe18004` et `b6a77fe8f7bc` avaient tous deux `down_revision = 'f81738121747'` → deux heads. Commande pourtant documentée dans CLAUDE.md.
2. `f81738121747_initial_schema` ne créait **aucune table** — il ajoutait `creation_key`, exactement comme `662f6fe18004`. Impossible d'amorcer une base vierge.
3. Après reconstruction, la vraie base de dev restait tamponnée `b6a77fe8f7bc` (révision supprimée) → `upgrade head` levait `Can't locate revision` : **l'app ne démarrait plus**.
4. `stamp head` seul aurait déclaré « à jour » une base à qui il manquait réellement `market_courses.school_registry_id` — le bug survivait en silence.
### Cause
Alembic ajouté « pour cocher une case de review » sans jamais autogénérer le schéma, et sans supprimer `create_all`. Les deux mécanismes coexistaient, aucun n'était la source de vérité. Les migrations suivantes ont branché sur un ancêtre inerte.
### Solution
- 3 migrations supprimées, `alembic revision --autogenerate` sur base vierge → `8783a989e776` avec les **10 tables** réelles.
- `alembic/env.py` dérive l'URL de `settings` (fin du drift avec `alembic.ini`) + `render_as_batch=True` (SQLite ne sait pas ALTER COLUMN).
- `init_db()` ne fait plus `create_all` : il inspecte la base et route entre `upgrade head` (vierge / gérée) et réparation + `stamp head, purge=True` (pré-Alembic ou révision inconnue).
- `_repair_legacy_schema()` : crée les tables absentes puis ajoute les colonnes absentes (nullable ou avec défaut), et **lève** sur une NOT NULL sans défaut plutôt que de corrompre.
- 8 tests + preuve runtime sur une **copie de la vraie base** : adoptée, colonne ajoutée, 8 lignes intactes.
### Règle (Alembic)
Une migration nommée `initial_schema` doit créer le schéma — sinon ce n'est pas un initial. Vérifier `alembic heads` (un seul head) après toute migration ajoutée. Réécrire un historique de migrations casse toute base tamponnée sur une révision supprimée : prévoir le chemin d'adoption (`stamp --purge`) et vérifier le schéma réel avant de tamponner, jamais faire confiance au tampon seul. `create_all` n'ajoute **jamais** une colonne à une table existante : ne pas l'utiliser comme mécanisme d'évolution de schéma.

## 2026-09-05 — SSRF par sitemap : les `<loc>` sont du contenu distant, pas une entrée de confiance
### Contexte
Dette « fragilité scraping » : segment `/formation/` figé dans `base.py` (partagé ORSYS/Demos) et `<loc>` suivis sans allowlist.
### Problème
1. Le filtre `/formation/` était codé en dur dans `_fetch_sitemap_urls` : une école dont le sitemap utilise `/cours/` renvoyait **zéro résultat en silence**, sans erreur.
2. Plus grave : le scraper émettait un GET vers **n'importe quelle URL** trouvée dans le XML distant. Un sitemap compromis (ou une école hostile ajoutée au registre) pouvait viser `http://127.0.0.1:8000/...`, `http://169.254.169.254/...` ou un hôte interne — SSRF côté serveur. `validate_external_url` ne protégeait que l'URL **configurée** de l'école (niveau schéma Pydantic), jamais les URLs moissonnées.
3. `generic.py` redéfinissait `_fetch_sitemap_urls` en version **plus faible** (aucun filtre), donc le durcissement de la base l'aurait contourné.
4. Première version de l'allowlist trop permissive : `reference.endswith("." + host)` laissait passer `https://fr/...` pour un sitemap `www.orsys.fr` (« fr » est un hôte à label unique, qui résout souvent en interne sur un réseau d'entreprise).
### Cause
Confiance implicite dans un document servi par un tiers. La validation anti-SSRF existait mais était placée à la frontière de saisie utilisateur, pas à la frontière réseau où les URLs entrent réellement.
### Solution
- `url_pattern` paramétrable (`COURSE_URL_PATTERN` par défaut, `None` = pas de filtre).
- `is_same_site()` dans `url_safety.py` : `www.` neutralisé des deux côtés, puis hôte identique ou sous-domaine **strict** du sitemap. Volontairement plus strict qu'une comparaison de domaine enregistrable — sans liste de suffixes publics, « deux labels communs » laisserait passer `evil.co.uk` pour `orsys.co.uk`.
- Chaque `<loc>` passe `validate_external_url` **et** `is_same_site`, avec log du nombre d'URLs écartées.
- Override affaibli de `generic.py` supprimé (réutilise la base) → un seul point de contrôle.
- 7 tests, dont sitemaps hostiles (localhost, 169.254.169.254, `file://`, domaine tiers, suffixe `www.orsys.fr.evil.example.com`, hôte à label unique).
### Règle (SSRF sitemap)
Toute URL issue d'un document distant (sitemap, JSON-LD, `href` scrappé) est une entrée non fiable : la valider **au point de sortie réseau**, pas seulement à la saisie. Anchor de l'allowlist = l'hôte du document qui l'a fournie. Ne jamais redéfinir dans une sous-classe un helper porteur d'un contrôle de sécurité en version affaiblie — étendre le helper partagé. Un filtre codé en dur partagé par plusieurs adaptateurs échoue en silence (0 résultat) : le rendre paramétrable.

## 2026-09-05 — Vue Archives : compteur menteur et liste non bornée
### Contexte
Phase 2.3, page Archives (cours archivés + recommandations validées). Le todo demandait de vérifier d'abord si un endpoint existant suffisait.
### Problème
1. **Aucun code backend n'était nécessaire** : `GET /courses?status=archived`, `POST /courses/{id}/restore` (admin + AuditLog) et les helpers `coursesApi` / `gapApi` existaient déjà. Sans cette vérification, on écrivait un endpoint en double.
2. Revue : `gapApi.list()` sans `limit` → le serveur plafonne **silencieusement à 50** (`limit: int = Query(default=50, ge=1, le=200)`). Le compteur « (N) » de l'en-tête aurait affiché *50* alors qu'il pouvait y avoir 300 recommandations validées — **chiffre faux dans une vue décisionnelle**.
3. Revue : `GET /courses` n'a **aucune borne** serveur, et la page rendait toutes les lignes d'un bloc — contraire à la règle CLAUDE.md « rendu progressif au-delà de 100 éléments » sur des postes peu puissants.
4. Après restauration, un `fetchAll()` rechargeait aussi les recommandations, qu'une restauration ne modifie pas.
### Cause
Un défaut de pagination côté serveur est invisible depuis le client : la réponse est bien formée, juste tronquée. Rien dans le type `GapRecommendationList[]` ne signale la troncature.
### Solution
- `limit: 200` explicite (plafond serveur) + mention « Affichage limité aux 200… » quand `length === limit`, et « (200 affichées) » au lieu de « (200) ».
- Rendu plafonné à 100 lignes + bouton « Afficher les N cours restants ».
- Restauration → ne recharge que les cours.
- 14 tests, dont troncature, seuil de dépliage, non-rechargement des recommandations.
### Règle
Avant d'afficher un compteur issu d'une liste API, vérifier le `limit` **par défaut** de l'endpoint : `len(réponse)` n'est un total que si l'endpoint n'a pas de pagination. À ras du plafond, dire que c'est tronqué plutôt que d'afficher un total faux. Et vérifier qu'un endpoint existant ne suffit pas avant d'en écrire un nouveau — ici toute la Phase 2.3 était du frontend.

### Vérification G8 (2026-09-05)
Le parcours navigateur a été fait **par Paul**, pas par moi : la connexion exige de saisir un mot de passe, ce que je ne fais pas. Côté agent : endpoints protégés (401, pas 404), 103 tests vitest, `tsc` et `build` verts. Côté humain : page affichée, « Excel perfectionnement » restauré. Confirmé en base — statut repassé à `active`, 0 cours archivé restant, `AuditLog` `restore_course/course:1` écrit.

**Règle :** quand une vérification exige des identifiants, ne pas la déclarer faite ni la contourner — la déléguer explicitement et dire précisément quoi cliquer. Puis confirmer le résultat par la base, pas par la parole.

## 2026-09-05 — Export PDF : assainissement latin-1 mort et révocation de blob trop tôt
### Contexte
Phase 2.1, export PDF d'une `CourseProposal`. fpdf2 retenu contre le SPEC (qui nommait WeasyPrint) : GTK/Pango à installer sur chaque poste Windows de la Mairie contre zéro dépendance native.
### Problème
1. `_to_latin1` avait un bloc censé retirer les caractères non représentables. Il ne retirait **rien** : `char.encode("latin-1", errors="ignore")` renvoie `b""` (falsy) pour un caractère hors latin-1, et la condition retombait alors sur `category != "Cc"` qui est vraie — donc le caractère était gardé, puis supprimé de toute façon par l'encodage final. Code mort. Pire, les **caractères de contrôle** (`\x00`, `\x07`) *sont* valides en latin-1 : ils traversaient intacts jusque dans le PDF. Vérifié : `_to_latin1("A\x00B\x07C")` renvoyait la chaîne inchangée.
2. Front : `URL.revokeObjectURL` appelé dans le `finally`, donc dans le même tick que `link.click()`. Certains navigateurs n'ont pas encore lu le blob → téléchargement annulé. Aucun test ne pouvait l'attraper, jsdom ne télécharge rien.
3. Le test de typographie utilisait une apostrophe droite `'` et ne couvrait donc pas U+2019, le cas le plus fréquent en français.
### Cause
Assainissement écrit « à l'instinct » sans vérifier ce que chaque passe filtre réellement. La condition mélangeait deux tests sans rapport, et l'intuition « latin-1 = imprimable » est fausse : latin-1 contient les caractères de contrôle.
### Solution
- Trois passes explicites : remplacements typographiques → retrait des catégories Unicode `Cc/Cf/Cs/Co/Cn` (sauf `\n` et `\t`) → encodage latin-1.
- Révocation différée via `setTimeout(..., 0)`, avec le pourquoi en commentaire.
- Tests ajoutés : contrôle retiré, sauts de ligne gardés, apostrophe courbe, et un `afterEach` qui draine les timers différés (sinon ils polluent les compteurs du test suivant).
### Règle
Un filtre de caractères se vérifie en l'exécutant sur les cas limites, pas en le relisant : écrire la sonde (`_to_latin1("A\x00B")`) avant de croire le code. « Encodable en latin-1 » ≠ « imprimable » — les caractères de contrôle passent. Et ne jamais révoquer une object URL dans le même tick que le clic qui la consomme.

## 2026-09-05 — Export Word : un contenu, deux rendus
### Contexte
Phase 2.2, export `.docx` (python-docx). Le HANDOFF imposait de réutiliser la couche de récupération de 2.1 sans la dupliquer.
### Problème
1. Le rendu PDF mélangeait **quoi afficher** et **comment l'afficher** : statut, date, heures et sections étaient calculés au milieu des appels `multi_cell`. Copier ça pour le Word aurait créé deux sources de vérité — un champ ajouté un jour dans un seul format.
2. `_to_latin1` aurait été appliqué au Word par simple copier-coller. C'est une contrainte des **polices de base de fpdf2**, pas du contenu : `.docx` est de l'UTF-8. Le japonais et les emoji doivent survivre au Word alors qu'ils sont retirés du PDF.
3. Revue : `subtitle.runs[0].italic` lève `IndexError` sur un paragraphe vide — `add_paragraph("")` ne crée aucun run. Inatteignable aujourd'hui (le sous-titre est toujours rempli), mine pour plus tard.
4. Revue : `export_proposal` (PDF) vs `export_proposal_docx` — nommage asymétrique, les deux formats n'étaient pas distinguables proprement en analyse de journal.
### Cause
Le premier format écrit sert de moule au second. Sans extraction préalable, la duplication est le chemin de moindre effort.
### Solution
- `build_proposal_content()` renvoie un `ProposalContent` (titre, sous-titre, sections) : **source unique**. `render_proposal_pdf` et `render_proposal_docx` ne sont que deux rendus. Un test vérifie que tout le contenu de la structure se retrouve dans le `.docx`.
- `_to_latin1` reste appliqué au seul PDF, avec le pourquoi en docstring. Test dédié : le `.docx` conserve « 日本語 » et « 🎓 ».
- Garde `if subtitle.runs:`.
- `export_proposal_pdf` / `export_proposal_docx`, plus un test qui vérifie que les deux actions nomment leur format.
- Endpoint : `_load_proposal`, `_trace_export` et `_attachment` extraits, les deux routes ne dupliquent plus la récupération ni l'en-tête.
### Règle
Avant d'ajouter un second format d'export, extraire d'abord *ce qui est affiché* de *comment c'est affiché* — sinon les deux divergent au premier champ ajouté. Et ne pas transporter dans le nouveau format les contraintes techniques de l'ancien : vérifier lesquelles viennent de la bibliothèque, pas du contenu. Deux actions jumelles dans un journal doivent nommer ce qui les distingue.

## 2026-09-05 — Archivage par lot : ne jamais archiver par requête, et mesurer avant d'optimiser
### Contexte
Phase 2.4. `docs/SPEC.md` §5 range l'archivage massif parmi les actions destructives : « confirmation + AuditLog ».
### Problème
1. La tentation était un endpoint « archive tout ce qui correspond au filtre ». Un filtre mal compris côté client aurait vidé un catalogue entier sans que personne ne voie quoi, et le journal n'aurait gardé qu'une requête, pas la liste des cours touchés.
2. `_write_audit` (helper partagé) fait `db.add()` **puis** `await db.flush()`. Réutilisé tel quel dans une boucle, ça fait 200 allers-retours SQLite sur un lot plein. Mesuré : **326 ms** pour 200 cours.
3. Test `test_batch_requires_admin` en échec au premier jet : le 403 déclenche le `rollback` de l'override `get_db`, qui annulait les cours créés par un simple `flush` dans le helper de test. Artefact de harnais, pas bug de code — mais il aurait pu être lu comme tel.
### Cause
Réutiliser un helper conçu pour un appel unitaire dans une boucle : sa granularité de flush devient un coût. Et l'ergonomie « archiver le résultat du filtre » paraît plus simple qu'elle n'est sûre.
### Solution
- Le serveur reçoit une **liste explicite d'identifiants**, jamais un filtre. Le client filtre et coche. Borne dure à 200, doublons refusés (ils fausseraient le décompte rendu à l'utilisateur).
- Réponse ventilée `archived` / `skipped` / `not_found` : partiel toléré, un id inconnu n'annule pas le reste. Idempotent.
- **Un AuditLog par cours**, avec la même action `archive_course` que l'archivage unitaire — « qui a archivé ce cours-là » se répond pareil, que ce soit en lot ou à l'unité.
- Journaux ajoutés sans flush intermédiaire : **326 ms → ~128 ms** sur 200 cours.
- Helper de test : `commit` au lieu de `flush`, avec le pourquoi en commentaire.
- UI : cases à cocher (cours actifs seulement), « tout sélectionner » portant sur les lignes filtrées, dialogue de confirmation **nommant le nombre**, admin uniquement.
### Règle
Une action de masse prend des identifiants, jamais un critère : ce que l'utilisateur a vu et coché doit être exactement ce que le serveur modifie. Un helper qui flushe à chaque appel ne se réutilise pas tel quel dans une boucle — mesurer avant et après plutôt que de supposer dans un sens ou dans l'autre. Et pour la traçabilité, garder le même nom d'action en lot qu'à l'unité.

### Piège worktree (2026-09-05)
Le premier lancement des serveurs se faisait sur `backend/data/atlas.db` **du worktree** : 0 utilisateur, 0 cours. Aucune connexion n'était possible, quels que soient les identifiants — et rien dans l'UI ne le disait (juste un échec de login). La base réelle est celle du repo principal ; en worktree, passer `DATABASE_URL` explicitement.
Corollaire : avant de conclure « les identifiants sont faux », vérifier que la table `users` n'est pas simplement vide.
