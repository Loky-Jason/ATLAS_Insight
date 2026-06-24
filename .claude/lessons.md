# Lessons — ATLAS_Insight
**Updated:** 2026-06-24

## Format per entry
- Context → Problem → Cause → Solution → Rule

## 2026-06-24 — SECRET_KEY faible en dev
- **Context:** Premier commit avec clé par défaut "CHANGE_ME"
- **Problem:** Averti par le code mais pas de mécanisme de refus
- **Cause:** Validation `model_validator` n'existait pas encore
- **Solution:** Ajout validation pydantic qui refuse/bloque selon environnement
- **Rule:** Valider les secrets côté config, pas seulement en commentaire

## 2026-06-24 — Timing attack sur login
- **Context:** Endpoint login — vérification email puis mot de passe
- **Problem:** Si email inconnu, réponse plus rapide que si email connu mais mauvais password
- **Cause:** Vérification password skipée quand user est None
- **Solution:** Hash bidon systématique + vérification constante en temps (E2)
- **Rule:** Toujours égaliser le temps de vérification auth, quelle que soit l'existence du compte

## 2026-06-24 — CSV injection dans l'import
- **Context:** Import Excel/CSV — upload fichier utilisateur
- **Problem:** Cellules commençant par `=`, `+`, `-`, `@` exécutées comme formules par Excel
- **Cause:** Pas de nettoyage des valeurs textuelles importées
- **Solution:** Prefix `'` automatique sur les valeurs commençant par un opérateur de formule (E3b)
- **Rule:** Neutraliser les formules Excel à l'import, pas seulement valider les types
