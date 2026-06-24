"""Service de suggestions de certification.

Référentiel de règles intégré : mapping mots-clés → type de certif.
Aucun appel externe. Retourne une liste de suggestions ordonnées par confiance.

Types gérés :
  - rncp       : titre RNCP (accrédité État)
  - open_badge : badge numérique (compétence spécifique)
  - internal   : certificat interne SCAP
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Référentiel de règles
# ---------------------------------------------------------------------------
# Chaque règle : (pattern_regex, category_hint | None, certif_type, label, rationale, base_confidence)
# category_hint : si None → s'applique sans restriction de catégorie
# confidence augmente de +0.15 si la catégorie correspond.

_RULES: list[tuple[str | None, str | None, str, str, str, float]] = [
    # --- RNCP ---
    (
        r"management|leadership|chef de projet|gestion d.équipe|gestion d.project",
        None,
        "rncp",
        "RNCP Manager d'équipe",
        "Les formations en management sont éligibles au titre RNCP de niveau 5/6.",
        0.75,
    ),
    (
        r"comptab|finance|gestion financ|contrôle de gestion",
        None,
        "rncp",
        "RNCP Gestionnaire comptable et financier",
        "Compétences financières reconnues dans plusieurs titres RNCP niveau 5.",
        0.70,
    ),
    (
        r"ressources humaines|rh\b|recrutement|paie|formation professionnelle",
        None,
        "rncp",
        "RNCP Responsable RH",
        "Le domaine RH dispose de titres RNCP dédiés (niveau 5 et 6).",
        0.72,
    ),
    (
        r"numériqu|digital|informatique|développement|programmation|code|data|ia\b|intelligence artificielle",
        None,
        "rncp",
        "RNCP Développeur / Chef de projet numérique",
        "Compétences numériques couvertes par de nombreux titres RNCP niveaux 5–7.",
        0.68,
    ),
    (
        r"communication|relation.{0,10}public|médias|journalisme",
        None,
        "rncp",
        "RNCP Chargé de communication",
        "La communication est un titre RNCP de niveau 5 courant.",
        0.65,
    ),
    (
        r"secrétariat|assistanat|office|bureautique",
        None,
        "rncp",
        "RNCP Assistant de direction",
        "L'assistanat figure dans plusieurs titres RNCP niveaux 4–5.",
        0.60,
    ),
    (
        r"santé|bien[- ]être|sécurité au travail|pst|prévention",
        None,
        "rncp",
        "RNCP Préventeur / Conseiller en prévention",
        "Les formations santé/sécurité sont éligibles à des certifications RNCP dédiées.",
        0.65,
    ),
    # --- Open Badge ---
    (
        r"excel|tableur|word|powerpoint|office 365|microsoft 365|teams|sharepoint",
        None,
        "open_badge",
        "Open Badge Bureautique / Microsoft 365",
        "Les compétences sur outils bureautiques se formalisent idéalement en Open Badge.",
        0.80,
    ),
    (
        r"python|sql|git|linux|bash|scripting|automatisation",
        None,
        "open_badge",
        "Open Badge Compétence technique spécifique",
        "Les compétences techniques atomiques sont parfaitement adaptées au format Open Badge.",
        0.82,
    ),
    (
        r"prise de parole|présentation|négociation|assertivité|gestion du stress|confiance",
        None,
        "open_badge",
        "Open Badge Soft Skills",
        "Les soft skills sont difficiles à certifier RNCP mais bien valorisées en Open Badge.",
        0.75,
    ),
    (
        r"agile|scrum|kanban|lean|méthode de projet",
        None,
        "open_badge",
        "Open Badge Méthodes agiles",
        "Les certifications agiles (PSM, PSPO…) ou Open Badge sont la norme dans ce domaine.",
        0.78,
    ),
    (
        r"accessibilité|rgaa|handicap|inclusion",
        None,
        "open_badge",
        "Open Badge Accessibilité numérique",
        "Compétence transverse recommandée en Open Badge, alignée RGAA.",
        0.70,
    ),
    # --- Certificat interne ---
    (
        r"réglementaire|obligations légales|compliance|conformité|marchés publics|droit public|code des marchés",
        None,
        "internal",
        "Certificat interne SCAP — Conformité réglementaire",
        "Les formations réglementaires spécifiques à la Mairie se certifient idéalement en interne.",
        0.85,
    ),
    (
        r"accueil|relation.{0,10}usager|service public|protocole|administration",
        None,
        "internal",
        "Certificat interne SCAP — Service public",
        "Formation métier propre au contexte SCAP, pertinente pour un certificat de participation interne.",
        0.80,
    ),
    (
        r"atlas|scap|mairie|paris|collectivité|fonction publique",
        None,
        "internal",
        "Certificat interne SCAP — Formation institutionnelle",
        "Formation spécifique au contexte institutionnel SCAP/Mairie de Paris.",
        0.88,
    ),
]

# Bonus de confiance si la durée est longue (formation longue → RNCP plus probable)
_LONG_COURSE_HOURS = 35.0  # seuil heures
_LONG_COURSE_RNCP_BONUS = 0.08
_SHORT_COURSE_HOURS = 7.0   # seuil heures
_SHORT_COURSE_BADGE_BONUS = 0.06


def suggest_certifications(
    title: str,
    category: str | None,
    hours: float | None,
) -> list[dict[str, Any]]:
    """
    Retourne une liste de suggestions de certification triées par confiance desc.

    Parameters
    ----------
    title    : titre du cours proposé
    category : catégorie (peut être None)
    hours    : durée estimée en heures (peut être None)

    Returns
    -------
    list of dict {type, label, rationale, confidence}
    """
    text = f"{title} {category or ''}".lower()
    suggestions: list[dict[str, Any]] = []

    for cat_hint, _unused, cert_type, label, rationale, base_conf in _RULES:
        try:
            if not re.search(cat_hint or r".", text, re.IGNORECASE):
                continue
        except re.error as exc:
            logger.warning("Regex invalide dans le référentiel certification : %s", exc)
            continue

        confidence = base_conf

        # Bonus durée
        if hours is not None:
            if cert_type == "rncp" and hours >= _LONG_COURSE_HOURS:
                confidence += _LONG_COURSE_RNCP_BONUS
            elif cert_type == "open_badge" and hours <= _SHORT_COURSE_HOURS:
                confidence += _SHORT_COURSE_BADGE_BONUS

        # Dédoublonnage sur (type, label)
        already = next(
            (s for s in suggestions if s["type"] == cert_type and s["label"] == label),
            None,
        )
        if already:
            already["confidence"] = min(1.0, max(already["confidence"], round(confidence, 2)))
        else:
            suggestions.append(
                {
                    "type": cert_type,
                    "label": label,
                    "rationale": rationale,
                    "confidence": round(min(1.0, confidence), 2),
                }
            )

    # Tri desc par confiance
    suggestions.sort(key=lambda s: s["confidence"], reverse=True)
    return suggestions
