# HANDOFF OpenCode — Démarche obligatoire

> À suivre **à la lettre**. Ce fichier prime sur l'improvisation.
> Contexte : projet ATLAS_Insight, HEAD master `11dcac1`. Phases 0/1a/1b/1c/UX livrées.
> Tu reprends le travail. Des erreurs récurrentes ont dû être corrigées derrière toi —
> la section « Garde-fous » liste exactement ces pièges. Ne les reproduis pas.

---

## 0. Avant de toucher au code (rituel d'ouverture, non négociable)

1. `git pull` puis `git log --oneline -5` — vérifie que tu pars de `11dcac1` ou plus récent.
2. Lis `.claude/project-memory.md` (section « État pour reprise ») + `.claude/lessons.md`.
3. Lis `tasks/ROADMAP.md` pour l'ordre des phases.
4. Crée une branche : `git checkout -b feat/<module>` — **jamais** commit direct sur `master` sans review.
5. Environnement Python : interpréteur = **`python`** (jamais `python3` = stub MS Store cassé).
   Backend : `cd backend && .venv/Scripts/python.exe -m pytest -q` doit afficher **256 passed** AVANT de commencer. Si rouge, stop et signale.

---

## 1. Garde-fous — erreurs déjà commises, INTERDIT de répéter

### G1 — Précédence booléenne
Toujours parenthéser `and`/`or` mélangés. `a and b or c` ≠ `a and (b or c)`.
```python
# FAUX (déjà corrigé dans market_service.py)
if raw_school and raw_school in rname or rname in raw_school
# JUSTE
if raw_school and (raw_school in rname or rname in raw_school)
```

### G2 — datetime toujours aware UTC
**Jamais** `datetime.now()` nu. Toujours `datetime.now(UTC)`. Pour normaliser une valeur lue en base, passe par le helper `_as_utc` de `gap_service.py`.
Raison : SQLite stocke naïf, mais la migration Postgres plus tard casse sur comparaison naïf/aware. Le « fix » naïf a déjà dû être annulé.

### G3 — Upsert : discriminant obligatoire
Une recommandation/entité « creation » sans FK doit avoir une clé d'identité explicite (`creation_key`). Filtre d'upsert trop large = toutes les lignes s'écrasent en une seule → `MultipleResultsFound`. Voir `_upsert_recommendation`.

### G4 — ruff E712 : NE PAS auto-fixer
`ruff --fix` transforme `col == False` en `not col` → **CASSE** les requêtes SQLAlchemy (le `not` s'applique en Python, pas en SQL).
Conversion manuelle : `col == False` → `col.is_(False)`, `col == True` → `col.is_(True)`.
Lance ruff **sans** `--fix` sur les fichiers contenant des requêtes SQLAlchemy, ou exclus E712 du fix.

### G5 — Forward-refs SQLAlchemy
`Mapped["X"]` déclenche un faux F821 ruff. Solution = bloc `if TYPE_CHECKING:` avec l'import. **Pas** d'import réel (cycle), **pas** de `# noqa` aveugle.

### G6 — Feature backend = feature exposée UI
Si tu ajoutes un scraper/endpoint/champ, **expose-le côté front** dans le même lot. Les 3 scrapers ORSYS/Cegos/Demos avaient été livrés sans être dans le dropdown — incomplet. Une feature non atteignable par l'utilisateur = non livrée.

### G7 — Toute logique métier = test dédié AVANT merge
Phase 1c a été mergée avec **0 test** sur 534 lignes. Interdit. Chaque service/scorer/parser → au moins un `test_*.py` couvrant le cas nominal + 1 cas limite. Pas de framework lourd : pytest async simple, asserts.

### G8 — Run d'intégration réel, pas seulement pytest
`256 passed` ≠ « ça marche ». Après une feature front+back, lance vraiment les serveurs et clique le parcours :
```
# backend
cd backend && .venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# frontend
cd frontend && npm run dev   # port 5173
```
Login admin : `admin@scap.paris` / `admin2026`. Vérifie le parcours bout-en-bout. Les bugs de câblage (BASE_URL, drift de contrat JSON) ne sortent qu'au runtime.

### G9 — PowerShell ≠ Bash
Heredoc `@'...'@` = PowerShell. Pour un message de commit multi-ligne en Bash, écris dans un fichier puis `git commit -F fichier`. Ne mélange pas les syntaxes.

### G10 — Pas de dérive de scope
Tu fais **la tâche demandée**, rien de plus. Pas d'Alembic « pour plus tard », pas d'abstraction spéculative, pas de refactor d'un code adjacent qui marche. Toute structure ajoutée doit être utilisée maintenant.

---

## 2. Procédure par tâche (boucle obligatoire)

Pour CHAQUE tâche ci-dessous, dans cet ordre :

1. **Comprendre** : lis tout le code touché end-to-end avant d'écrire. Grep tous les appelants de la fonction modifiée (bug = corrige la racine partagée, pas le symptôme par appelant).
2. **Tester d'abord** : écris le(s) test(s) qui échoue(nt) et décrit le comportement attendu.
3. **Coder** le minimum qui fait passer. Type hints obligatoires. Commentaires utiles seulement.
4. **Relire** : applique la check-list Garde-fous (G1→G10).
5. **Vérifier** : `pytest -q` vert + `ruff check` (sans --fix sur fichiers SQLAlchemy) + run d'intégration si front+back touché (G8).
6. **Commit** : Conventional Commits, message factuel, finir par `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
7. **Documenter** : 1 entrée dans `.claude/lessons.md` (Contexte→Problème→Cause→Solution→Règle) + MAJ `.claude/project-memory.md` si décision d'archi + MAJ `tasks/ROADMAP.md` (statut). 
8. **Push** la branche, ouvre la PR. **Ne merge pas dans `master` toi-même** — laisse la review.

Critère d'arrêt d'une tâche : tests verts + intégration OK + docs à jour + PR poussée. Sinon la tâche n'est pas finie.

---

## 3. Tâches à réaliser (ordre imposé)

### Tâche A — Trancher Alembic (DETTE bloquante, à faire EN PREMIER)
**Problème actuel** : `backend/alembic/versions/f81738121747_initial_schema.py` est nommé `initial_schema`, `down_revision=None`, mais ne fait **que** `add_column('gap_recommendations', 'creation_key')` — aucun `CREATE TABLE`. Donc il ne peut PAS bootstrapper une base vierge. En parallèle `app/core/db.py:init_db()` fait toujours `create_all` à chaque démarrage. Résultat : migration inerte (stampée), et `alembic upgrade head` sur une base déjà créée planterait (colonne déjà présente). Contredit la décision verrouillée *« Pas d'Alembic — tables via init_db() »*.

**Décision par défaut imposée = REVERT** (rung paresseux correct : le projet n'a pas besoin de migrations tant qu'il est sur SQLite + `create_all`) :
1. `git rm -r backend/alembic backend/alembic.ini`
2. Retire `alembic` de `backend/pyproject.toml` (dépendances).
3. Garde `creation_key` (déjà dans le modèle `gap_recommendation.py` + créé par `create_all`) — ne touche pas au modèle.
4. `pytest -q` → 256 verts. Démarre l'app, vérifie que la table a bien `creation_key`.
5. Note dans `lessons.md` : « Alembic introduit prématurément (migration partielle trompeuse) → reverté ; on reste sur init_db/create_all tant que SQLite, on fera un vrai initial autogenerate au moment de Postgres/M365. »

**SI ET SEULEMENT SI** le client demande explicitement de garder Alembic → alors fais-le **proprement** : `alembic revision --autogenerate` sur une base vierge pour générer le **vrai** schéma initial complet (toutes les tables), retire `create_all` de `init_db`, et teste `alembic upgrade head` sur une base vide ET sur une base existante. Pas de demi-mesure.

### Tâche B — Perf gap_service (chip `task_8aa9a344`)
Cible : `backend/app/services/gap_service.py`.
- `_pass1_closure` / `_cluster_school_courses` : similarité O(n²) via `difflib.SequenceMatcher` sur tous les couples. Réduis (pré-filtre par 1ʳᵉ lettre / longueur, ou `difflib.get_close_matches` borné, ou normalisation + bucket). Pas de lib externe nouvelle (rung : stdlib d'abord).
- `_pass2_creation` : N+1 sur `estimate_hours` appelé par cours dans la boucle de cluster → calcule une fois par cluster ou batch.
- **Contrainte dure** : `tests/test_gap_service.py` (3 régressions) doit rester **vert** — comportement identique, seule la perf change. Ajoute un test de non-régression sur le résultat (mêmes recommandations avant/après).
- Marque les heuristiques d'un commentaire `# ponytail:` avec le plafond (ex. seuil de bucket).

### Tâche C — Phase 2 (après A+B verts)
Ordre : 2.1 → 2.2 → 2.3. Une PR par sous-tâche.
- **2.1 Export PDF** : WeasyPrint. Endpoint backend `GET /export/recommendations.pdf` (et/ou par entité). Template HTML → PDF. Texte UI **français**. Bouton export côté front (G6). Test : le endpoint renvoie un `application/pdf` non vide.
- **2.2 Export Word** : `python-docx`. Même périmètre que 2.1 en `.docx`. Réutilise les données de 2.1, ne duplique pas la couche de récupération.
- **2.3 Vue Archives (front)** : page `Archives` consommant les cours `status="archived"` + recommandations approuvées. Pas de nouvel endpoint si un existant suffit (vérifie d'abord).
- Reporte 2.4 (archivage avancé batch) et 2.5 (M365/Entra) — hors scope tant que 2.1–2.3 pas stables.

---

## 4. Check-list avant CHAQUE PR (copier dans la description)

- [ ] Pars de master à jour, branche `feat/*`
- [ ] `pytest -q` vert (≥256) — coller le compte
- [ ] `ruff check` propre (sans --fix sur SQLAlchemy — G4)
- [ ] Garde-fous G1–G10 relus
- [ ] datetime aware UTC partout (G2)
- [ ] Feature exposée côté front (G6)
- [ ] Test dédié sur la logique ajoutée (G7)
- [ ] Run d'intégration réel fait si front+back (G8)
- [ ] Textes UI en français, code en anglais
- [ ] Ops destructives = confirmation + AuditLog
- [ ] `lessons.md` + `project-memory.md` + `ROADMAP.md` à jour
- [ ] Commit `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
- [ ] PR poussée, **pas** de self-merge sur master

---

## 5. Interdits absolus
- Commit `.env`, secrets, `SECRET_KEY` par défaut en prod.
- `os.remove` direct → suppression via corbeille/soft-delete + AuditLog.
- Merge sur `master` sans review.
- `python3`, heredoc PowerShell en Bash, `ruff --fix` E712 sur SQLAlchemy.
- Ajouter une dépendance pour ce que la stdlib fait en quelques lignes.
- Livrer une feature backend non atteignable côté UI.
