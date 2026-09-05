# Spec — Export Word d'une proposition de cours (Phase 2.2)

## Contexte

Suite directe de `specs/export-pdf.md`. `docs/SPEC.md` §2 prévoit les deux formats :
le PDF pour diffuser, le `.docx` pour que la hiérarchie **retouche** le texte avant
de le transmettre. Sans le Word, toute correction impose de repartir de l'écran.

## Objectif

Produire le même contenu que l'export PDF, au format `.docx` éditable.

## Contrats

- **Entrée :** `GET /api/v1/export/proposals/{proposal_id}.docx`, utilisateur
  authentifié.
- **Sortie :** `200`, `Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document`,
  `Content-Disposition: attachment; filename="proposition-<id>-<slug>.docx"`.
  `404` inconnu, `401` sans session.
- **Comportement :**
  - **Contenu identique au PDF, défini une seule fois.** Les deux exports lisent la
    même description de document (`_proposal_content`) ; seul le rendu diffère. Un
    champ ajouté doit apparaître dans les deux formats sans double saisie.
  - Mêmes règles de données que 2.1 : champs vides → « — », JSON invalide affiché
    tel quel plutôt que de faire échouer l'export.
  - **Pas d'assainissement latin-1 ici.** C'est une contrainte des polices de base
    de fpdf2, pas du format Word : `.docx` est de l'UTF-8. Le japonais et les
    emoji doivent donc survivre à l'export Word alors qu'ils sont retirés du PDF.
  - Méthode sûre, comme 2.1 : ne modifie pas la proposition. `AuditLog`
    `export_proposal_docx` écrit.

## Données de test

Même jeu que `specs/export-pdf.md`, plus un cas « caractères non latins conservés ».

## Scénarios

1. **Nominal** — proposition complète → `.docx` non vide, ouvrable, titre présent.
2. **Erreur** — id inexistant → 404 ; sans session → 401.
3. **Limite** — champs `None`, JSON invalide, titre 512 caractères, caractères
   non latin-1 (qui, eux, doivent être **conservés**).

## Critères d'acceptance

- [ ] `GET /export/proposals/{id}.docx` renvoie un `.docx` non vide (signature ZIP `PK`)
- [ ] Le document contient le titre, le statut et les quatre sections
- [ ] 404 sur id inconnu, 401 sans authentification
- [ ] Champs `None` et JSON invalide n'empêchent pas l'export
- [ ] Les caractères non latin-1 sont **conservés** (contrairement au PDF)
- [ ] Le contenu provient de la même source que le PDF (un test le vérifie)
- [ ] `AuditLog` écrit, proposition non modifiée
- [ ] Bouton d'export Word atteignable depuis la page Propositions (G6)
- [ ] Tests automatisés écrits et passent
- [ ] Pas de régression sur l'export PDF

## Hors périmètre

- Export multi-propositions.
- Styles Word avancés (en-têtes de charte, sommaire). Document sobre et éditable.
