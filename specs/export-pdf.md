# Spec — Export PDF d'une proposition de cours (Phase 2.1)

## Contexte

`docs/SPEC.md` §4 : « Export cours proposés → `backend/export` (PDF + docx) ». Une
`CourseProposal` est le livrable que le SCAP présente à sa hiérarchie ; aujourd'hui
elle n'existe qu'à l'écran. Son statut prévoit déjà `exported`, mais rien ne produit
de fichier.

**Écart assumé au SPEC :** le SPEC nomme WeasyPrint. Retenu à la place : **fpdf2**,
sur décision du 2026-09-05. WeasyPrint dépend de GTK/Pango en librairies système,
à installer sur chaque poste Windows de la Mairie ; fpdf2 est pur Python, zéro
dépendance native. `docs/SPEC.md` est mis à jour en conséquence.

## Objectif

Produire à la demande un PDF d'une seule page présentant une proposition de cours,
téléchargeable depuis la page Propositions.

## Contrats

- **Entrée :** `GET /api/v1/export/proposals/{proposal_id}.pdf`, utilisateur
  authentifié. Aucun paramètre.
- **Sortie :** `200` avec `Content-Type: application/pdf` et
  `Content-Disposition: attachment; filename="proposition-<id>-<slug>.pdf"`.
  `404` si la proposition n'existe pas. `401` sans session.
- **Comportement :**
  - Contenu : titre, statut, date de création, heures estimées, description,
    pistes de certification, éléments d'origine (`based_on`).
  - `certification_suggestions` et `based_on` sont des **chaînes JSON** en base
    (`[{"type": "RNCP", "label": "..."}, ...]`). Elles sont désérialisées et
    rendues lisiblement ; un JSON invalide est affiché tel quel plutôt que de
    faire échouer l'export.
  - Champs vides → « — », jamais « None ».
  - **Méthode sûre :** le GET ne modifie pas la proposition. Le passage au statut
    `exported` reste une action explicite de l'utilisateur (PATCH existant) :
    muter un état métier sur un GET casserait l'idempotence et pourrait se
    déclencher sur un prefetch navigateur.
  - **Traçabilité :** une entrée `AuditLog` `export_proposal` est écrite. L'export
    n'est pas destructif, mais c'est une sortie de données : le projet audite déjà
    des actions non destructives (`approve`, `scan`), on suit cette convention.
  - **Encodage :** fpdf2 avec police de base est limité à latin-1. Le texte est
    assaini (tirets cadratins, apostrophes et guillemets typographiques ramenés à
    leurs équivalents ASCII, autres caractères hors latin-1 retirés) pour qu'un
    caractère exotique ne fasse jamais échouer un export. Plafond assumé :
    pas d'alphabet non latin. Chemin d'upgrade : embarquer une police TTF Unicode.

## Données de test

```python
CourseProposal(
    title="Excel perfectionnement — niveau avancé",
    description="Tableaux croisés dynamiques, macros.",
    hours_estimated=21.0,
    certification_suggestions='[{"type": "RNCP", "label": "Titre RNCP 35148"}]',
    based_on='[{"source": "market_course", "id": 4}]',
    status="proposed",
)
```

## Scénarios

1. **Nominal** — proposition complète → PDF non vide, `application/pdf`, titre présent.
2. **Erreur** — id inexistant → 404 ; sans session → 401.
3. **Limite** — tous champs optionnels à `None`, JSON invalide, titre très long
   (512 car.), caractères hors latin-1 → l'export réussit quand même.

## Critères d'acceptance

- [ ] `GET /export/proposals/{id}.pdf` renvoie un PDF non vide commençant par `%PDF-`
- [ ] 404 sur id inconnu, 401 sans authentification
- [ ] Champs `None` et JSON invalide n'empêchent pas l'export
- [ ] Un caractère hors latin-1 n'empêche pas l'export
- [ ] `AuditLog` `export_proposal` écrit
- [ ] La proposition n'est **pas** modifiée par l'export
- [ ] Bouton d'export atteignable depuis la page Propositions (G6)
- [ ] Tests automatisés écrits et passent
- [ ] Pas de régression sur les modules existants

## Hors périmètre

- Export multi-propositions (dossier récapitulatif) — extension évidente si besoin.
- Export Word `.docx` — c'est 2.2, il réutilisera la couche de récupération.
- Mise en page riche (logo, charte). Une page sobre suffit au besoin exprimé.
