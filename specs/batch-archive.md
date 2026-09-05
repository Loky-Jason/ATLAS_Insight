# Spec — Archivage par lot (Phase 2.4)

## Contexte

Fermer une session de catalogue signifie archiver des dizaines de cours d'un
coup. Aujourd'hui c'est un clic par ligne dans Cours SCAP : à l'échelle d'une
année, c'est inutilisable.

`docs/SPEC.md` §5 range explicitement l'**archivage massif** parmi les actions
destructives : « confirmation + AuditLog ». C'est donc une contrainte de la
spec, pas une option d'ergonomie.

## Objectif

Archiver plusieurs cours en une action, à partir d'une sélection explicite,
avec confirmation et traçabilité individuelle.

## Contrats

- **Entrée :** `POST /api/v1/courses/archive-batch`, **admin uniquement**.
  Corps : `{"course_ids": [1, 2, 3]}` — 1 à 200 identifiants, sans doublon.
- **Sortie :** `200` avec `{"archived": [1, 2], "skipped": [3], "not_found": [9]}`.
  - `archived` : cours passés de `active` à `archived`.
  - `skipped` : cours déjà archivés — non comptés, non re-journalisés.
  - `not_found` : identifiants inexistants.
  - `403` non-admin, `401` sans session, `422` si la liste est vide ou > 200.
- **Comportement :**
  - **Sélection explicite d'identifiants, jamais un filtre.** Le serveur
    n'archive pas « tout ce qui correspond à une requête » : un filtre mal
    compris côté client archiverait un catalogue entier sans que personne ne
    voie quoi. Le client filtre et coche ; le serveur reçoit la liste.
  - **Un `AuditLog` par cours archivé** (`archive_course`, cible
    `course:{id}`), pas une seule ligne pour le lot : la traçabilité doit
    permettre de répondre à « qui a archivé ce cours-là ».
  - **Partiel toléré, pas d'échec global** : un identifiant inconnu ou un cours
    déjà archivé n'annule pas le reste. La réponse dit exactement ce qui a été
    fait.
  - Idempotent : rejouer la même requête archive 0 cours et n'écrit aucun
    journal supplémentaire.
  - Borne dure à 200 identifiants : évite une transaction géante sur SQLite.
- **UI :** cases à cocher dans Cours SCAP, case « tout sélectionner » portant
  sur les lignes **actuellement filtrées**, barre d'action affichant le nombre
  sélectionné, et **dialogue de confirmation nommant ce nombre** avant l'appel.
  Réservé aux admins, comme l'archivage unitaire existant.

## Données de test

Trois cours `active` (id 1, 2, 3), un cours déjà `archived` (id 4).
Requête : `{"course_ids": [1, 2, 4, 999]}`
→ `{"archived": [1, 2], "skipped": [4], "not_found": [999]}`.

## Scénarios

1. **Nominal** — 3 cours actifs sélectionnés → les 3 archivés, 3 AuditLog.
2. **Erreur** — utilisateur non admin → 403, aucun cours modifié, aucun journal.
3. **Limite** — liste vide → 422 ; 201 identifiants → 422 ; doublons → 422 ;
   lot mêlant actifs, déjà archivés et inconnus → réponse partielle correcte.
4. **Idempotence** — rejouer le même lot → `archived` vide, aucun journal ajouté.

## Critères d'acceptance

- [ ] `POST /courses/archive-batch` archive les cours actifs de la liste
- [ ] Réponse ventilée `archived` / `skipped` / `not_found`
- [ ] Un `AuditLog` par cours réellement archivé, aucun pour les ignorés
- [ ] 403 pour un non-admin, sans aucun effet de bord
- [ ] 422 sur liste vide, > 200 identifiants, ou doublons
- [ ] Rejouer le lot est sans effet
- [ ] UI : sélection, « tout sélectionner » sur les lignes filtrées, dialogue de
      confirmation nommant le nombre, réservé aux admins (G6)
- [ ] Tests automatisés écrits et passent
- [ ] Pas de régression sur l'archivage unitaire

## Hors périmètre

- Restauration par lot depuis Archives — extension symétrique évidente, à faire
  si le besoin se confirme.
- Suppression définitive par lot : le projet est en soft-delete, hors sujet.
