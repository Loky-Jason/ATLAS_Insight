"""Génération des exports de propositions de cours (PDF et Word).

fpdf2 plutôt que WeasyPrint (écart assumé à `docs/SPEC.md`, cf.
`specs/export-pdf.md`) : WeasyPrint dépend de GTK/Pango en librairies système,
à installer sur chaque poste Windows ; fpdf2 est pur Python.

Le contenu affiché est décrit une seule fois (`build_proposal_content`) ; PDF et
Word ne sont que deux rendus de cette description. Cf. `specs/export-word.md`.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass
from io import BytesIO

from docx import Document
from fpdf import FPDF

from app.models.course_proposal import CourseProposal

logger = logging.getLogger(__name__)

STATUS_LABELS: dict[str, str] = {
    "draft": "Brouillon",
    "proposed": "Proposé",
    "exported": "Exporté",
}

# Caractères typographiques courants absents de latin-1, ramenés à leur
# équivalent ASCII plutôt que de faire échouer tout l'export.
_TYPOGRAPHIC_REPLACEMENTS = str.maketrans(
    {
        "‘": "'",
        "’": "'",
        "‚": "'",
        "“": '"',
        "”": '"',
        "„": '"',
        "–": "-",
        "—": "-",
        "…": "...",
        " ": " ",
        " ": " ",
        "→": "->",
        "•": "-",
    }
)

# Catégories Unicode à retirer : contrôle, format, surrogates, usage privé.
_CONTROL_CATEGORIES = frozenset({"Cc", "Cf", "Cs", "Co", "Cn"})

_PAGE_WIDTH_MM = 210
_MARGIN_MM = 15
_CONTENT_WIDTH_MM = _PAGE_WIDTH_MM - 2 * _MARGIN_MM


def _to_latin1(text: str) -> str:
    """Rend un texte imprimable par les polices de base de fpdf2.

    Trois passes : équivalents ASCII des caractères typographiques, retrait des
    caractères de contrôle, puis suppression de ce que latin-1 ne code pas.

    Les caractères de contrôle doivent être retirés explicitement : ils sont
    valides en latin-1, donc `encode("latin-1")` les laisserait passer — un
    octet NUL venu d'un titre finirait tel quel dans le PDF.

    ponytail: latin-1 seulement — suffit pour du français. Un alphabet non latin
    serait vidé ; chemin d'upgrade = embarquer une police TTF Unicode
    (`pdf.add_font(...)`) et retirer cette fonction.
    """
    cleaned = text.translate(_TYPOGRAPHIC_REPLACEMENTS)
    cleaned = "".join(
        char
        for char in cleaned
        if char in "\n\t" or unicodedata.category(char) not in _CONTROL_CATEGORIES
    )
    return cleaned.encode("latin-1", errors="ignore").decode("latin-1")


def _format_json_field(raw: str | None) -> str:
    """Rend lisible un champ stocké en JSON (certifications, éléments d'origine).

    Les certifications sont des objets `{"type": ..., "label": ...}`. Un JSON
    invalide est renvoyé tel quel : un export ne doit pas échouer sur une
    donnée mal formée en base.
    """
    if not raw or not raw.strip():
        return "—"

    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw.strip()

    if isinstance(parsed, list):
        parts = [_format_json_entry(entry) for entry in parsed]
        parts = [part for part in parts if part]
        return " · ".join(parts) if parts else "—"
    if isinstance(parsed, dict):
        return _format_json_entry(parsed) or "—"
    return str(parsed)


def _format_json_entry(entry: object) -> str:
    """Une entrée de liste JSON — objet typé/labellisé ou valeur simple."""
    if isinstance(entry, dict):
        label = entry.get("label") or entry.get("title") or entry.get("name")
        kind = entry.get("type") or entry.get("source")
        if label and kind:
            return f"{label} ({kind})"
        if label:
            return str(label)
        # Référence brute type {"source": "market_course", "id": 4}
        identifier = entry.get("id")
        if kind and identifier is not None:
            return f"{kind} #{identifier}"
        return ", ".join(f"{k}: {v}" for k, v in entry.items())
    return str(entry) if entry is not None else ""


def _slugify(value: str) -> str:
    """Nom de fichier sûr, sans accent ni caractère spécial."""
    normalised = unicodedata.normalize("NFKD", value)
    ascii_only = normalised.encode("ascii", errors="ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_only).strip("-").lower()
    return slug[:60] or "proposition"


def build_proposal_filename(proposal: CourseProposal, extension: str) -> str:
    """Nom du fichier téléchargé, stable et lisible.

    Le slug ne contient que `[a-z0-9-]` : rien ne peut s'échapper de l'en-tête
    `Content-Disposition`.
    """
    return f"proposition-{proposal.id}-{_slugify(proposal.title)}.{extension}"


@dataclass(frozen=True)
class ProposalContent:
    """Ce qu'un export affiche, indépendamment du format.

    Source unique du contenu : PDF et Word rendent cette structure. Un champ
    ajouté ici apparaît dans les deux formats sans double saisie.
    """

    title: str
    subtitle: str
    sections: tuple[tuple[str, str], ...]


def build_proposal_content(proposal: CourseProposal) -> ProposalContent:
    """Décrit le document à produire pour une proposition.

    Toutes les valeurs absentes deviennent « — » : un export ne doit jamais
    afficher « None » à une hiérarchie.
    """
    status_label = STATUS_LABELS.get(proposal.status, proposal.status)
    created = proposal.created_at.strftime("%d/%m/%Y") if proposal.created_at else "—"
    hours = (
        f"{proposal.hours_estimated:g} h"
        if proposal.hours_estimated is not None
        else "—"
    )

    return ProposalContent(
        title=proposal.title,
        subtitle=f"Statut : {status_label}   |   Créé le {created}",
        sections=(
            ("Heures estimées", hours),
            ("Description", (proposal.description or "").strip() or "—"),
            (
                "Pistes de certification",
                _format_json_field(proposal.certification_suggestions),
            ),
            ("Éléments d'origine", _format_json_field(proposal.based_on)),
        ),
    )


class _ProposalPdf(FPDF):
    """Document une page, avec pied de page numéroté."""

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120)
        self.cell(0, 10, _to_latin1(f"ATLAS Insight — page {self.page_no()}"), align="C")


def _section(pdf: FPDF, title: str, body: str) -> None:
    """Titre de section puis corps de texte, avec retour à la ligne automatique."""
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(60)
    pdf.multi_cell(_CONTENT_WIDTH_MM, 6, _to_latin1(title))
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(0)
    pdf.multi_cell(_CONTENT_WIDTH_MM, 6, _to_latin1(body))
    pdf.ln(3)


def render_proposal_pdf(proposal: CourseProposal) -> bytes:
    """Construit le PDF d'une proposition de cours.

    Le texte passe par `_to_latin1` : contrainte des polices de base de fpdf2,
    pas du contenu — l'export Word n'en a pas besoin.
    """
    content = build_proposal_content(proposal)
    try:
        pdf = _ProposalPdf(format="A4")
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.set_margins(_MARGIN_MM, _MARGIN_MM, _MARGIN_MM)
        pdf.add_page()

        pdf.set_font("Helvetica", "B", 16)
        pdf.multi_cell(_CONTENT_WIDTH_MM, 8, _to_latin1(content.title))
        pdf.ln(2)

        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(110)
        pdf.multi_cell(_CONTENT_WIDTH_MM, 5, _to_latin1(content.subtitle))
        pdf.set_text_color(0)
        pdf.ln(4)

        for heading, body in content.sections:
            _section(pdf, heading, body)

        return bytes(pdf.output())
    except Exception as exc:
        logger.error("Erreur génération PDF proposition %s : %s", proposal.id, exc)
        raise RuntimeError("Échec de la génération du PDF.") from exc


def render_proposal_docx(proposal: CourseProposal) -> bytes:
    """Construit le `.docx` éditable d'une proposition de cours.

    Aucun assainissement de caractères : `.docx` est de l'UTF-8, contrairement
    aux polices de base du PDF. Le japonais et les emoji survivent ici.
    """
    content = build_proposal_content(proposal)
    try:
        document = Document()
        document.add_heading(content.title, level=1)

        subtitle = document.add_paragraph(content.subtitle)
        # Un paragraphe vide n'a aucun run : ne pas indexer à l'aveugle.
        if subtitle.runs:
            subtitle.runs[0].italic = True

        for heading, body in content.sections:
            document.add_heading(heading, level=2)
            document.add_paragraph(body)

        buffer = BytesIO()
        document.save(buffer)
        return buffer.getvalue()
    except Exception as exc:
        logger.error("Erreur génération DOCX proposition %s : %s", proposal.id, exc)
        raise RuntimeError("Échec de la génération du document Word.") from exc
