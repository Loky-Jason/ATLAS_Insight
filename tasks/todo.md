# TODOs — Session courante

> **Phase :** 0 / 1a / 1b / 1c / UX livrées. Dettes techniques traitées. Suite = **Phase 2**.
> **Dernière mise à jour :** 2026-09-05
> Détail des phases : `tasks/ROADMAP.md`. Source de vérité produit : `docs/SPEC.md`.

## Dettes techniques

- [x] **Alembic** — 3 migrations inertes (2 heads, `initial_schema` sans `CREATE TABLE`)
      remplacées par un vrai schéma autogénéré ; `init_db()` piloté par migrations,
      adoption d'une base pré-Alembic ou tamponnée sur révision inconnue
- [x] **Scrapers** — segment d'URL `/formation/` plus figé (paramètre `url_pattern`) ;
      allowlist d'hôte sur les `<loc>` moissonnés (fermeture d'un SSRF par sitemap)
- [x] **`todo.md`** remis à l'état réel du projet
- [ ] **Lint E501** — 24 lignes > 100 caractères dans 12 fichiers non liés aux
      chantiers en cours ; pur formatage, à faire en passe dédiée
- [ ] **Provider veille réel** — `scraper_strategy` par défaut reste `stub` ;
      brancher un scan réel puis vérifier le comportement des adaptateurs en conditions réelles

## Phase 2 — prochaine

- [x] **2.1** Export PDF (**fpdf2**, pas WeasyPrint — décision 2026-09-05, SPEC mis à jour).
      `GET /export/proposals/{id}.pdf` + bouton par ligne dans Propositions. 20 tests back,
      7 front. GET sûr : n'écrit pas le statut `exported`, mais trace un AuditLog.
      Reste à faire : **le clic réel** (téléchargement navigateur, non testable en jsdom)
- [x] **2.2** Export Word (python-docx) — `GET /export/proposals/{id}.docx` + second bouton.
      Contenu défini une seule fois (`build_proposal_content`), PDF et Word ne sont que
      deux rendus. Pas d'assainissement latin-1 côté Word : l'UTF-8 y est natif.
      Reste à faire : **ouvrir le .docx dans Word** pour valider la mise en page
- [x] **2.3** Vue Archives front — **aucun endpoint nouveau** (`GET /courses?status=archived`,
      `POST /{id}/restore` et les helpers client existaient déjà). Cours archivés +
      recherche + restauration admin, et recommandations validées. 14 tests.
      Parcours navigateur validé le 2026-09-05 (restauration réelle + AuditLog vérifié en base)
- [x] **2.4** Archivage par lot — `POST /courses/archive-batch` (admin, liste explicite
      d'ids, jamais un filtre), réponse ventilée archived/skipped/not_found, 1 AuditLog
      par cours. UI : cases à cocher + confirmation nommant le nombre. 13 tests back, 11 front.
      Reste à faire : **le parcours réel** (sélectionner, confirmer, vérifier Archives)
- [ ] **2.5** Migration M365 / Entra ID — reporté

## Spécifications à rédiger avant implémentation

- [x] `specs/export-pdf.md` (2.1)
- [x] `specs/export-word.md` (2.2)
- [ ] `specs/archives-view.md` (2.3)

## Qualité (rappel continu)

- [ ] `python -m pytest -q` après chaque module backend
- [ ] `cmd /c "npx vitest run"` + `npm run typecheck` avant chaque livraison
- [ ] `ruff check` sans `--fix` sur les fichiers contenant des requêtes SQLAlchemy (E712)
- [ ] Run d'intégration réel (serveurs lancés + parcours navigateur), pas seulement pytest
- [ ] Relecture `impeccable` sur les nouvelles pages frontend
- [ ] MAJ `.claude/lessons.md` après chaque review
