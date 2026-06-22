"""Service d'import Excel/CSV → table courses.

Colonnes requises minimales dans le fichier source :
    title (str)

Colonnes optionnelles reconnues (nommage souple, insensible à la casse) :
    category, status, enrolled_count, dropout_count,
    age_brackets, year, hours_estimated, notes
"""

from __future__ import annotations

import io
import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# Mapping flexible : nom normalisé → variantes acceptées
_COLUMN_ALIASES: dict[str, list[str]] = {
    "title": ["title", "titre", "nom", "intitulé", "intitule", "cours"],
    "category": ["category", "categorie", "catégorie", "domaine"],
    "status": ["status", "statut", "état", "etat"],
    "enrolled_count": [
        "enrolled_count", "inscrits", "nb_inscrits", "enrollments", "participants"
    ],
    "dropout_count": [
        "dropout_count", "desistements", "désistements", "abandons", "dropouts"
    ],
    "age_brackets": ["age_brackets", "tranches_age", "ages"],
    "year": ["year", "annee", "année"],
    "hours_estimated": ["hours_estimated", "heures", "nb_heures", "duree", "durée"],
    "notes": ["notes", "remarques", "commentaires"],
}

_REQUIRED_COLUMNS = {"title"}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename DataFrame columns using _COLUMN_ALIASES mapping."""
    rename_map: dict[str, str] = {}
    lowered = {c: c.lower().strip() for c in df.columns}

    for canonical, aliases in _COLUMN_ALIASES.items():
        for orig, low in lowered.items():
            if low in aliases and canonical not in rename_map.values():
                rename_map[orig] = canonical
                break

    return df.rename(columns=rename_map)


def _validate_columns(df: pd.DataFrame) -> None:
    """Raise ValueError if required columns are missing."""
    missing = _REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Colonnes requises manquantes dans le fichier : {', '.join(sorted(missing))}. "
            f"Colonnes détectées : {', '.join(df.columns.tolist())}"
        )


def _clean_row(row: pd.Series) -> dict[str, Any]:
    """Convert a DataFrame row to a dict suitable for Course model creation."""
    def _int_or_none(val: Any) -> int | None:
        try:
            return int(val) if pd.notna(val) else None
        except (ValueError, TypeError):
            return None

    def _float_or_none(val: Any) -> float | None:
        try:
            return float(val) if pd.notna(val) else None
        except (ValueError, TypeError):
            return None

    # Préfixes déclenchant une injection de formule dans Excel/LibreOffice (E3b)
    _FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

    def _str_or_none(val: Any) -> str | None:
        if pd.isna(val):
            return None
        s = str(val).strip()
        if not s:
            return None
        # Neutralise toute injection de formule : préfixe apostrophe si nécessaire
        if s[0] in _FORMULA_PREFIXES:
            s = "'" + s
        return s

    status_raw = _str_or_none(row.get("status")) or "active"
    if status_raw not in ("active", "archived"):
        status_raw = "active"

    return {
        "title": str(row["title"]).strip(),
        "category": _str_or_none(row.get("category")),
        "status": status_raw,
        "enrolled_count": _int_or_none(row.get("enrolled_count")) or 0,
        "dropout_count": _int_or_none(row.get("dropout_count")) or 0,
        "age_brackets": _str_or_none(row.get("age_brackets")),
        "year": _int_or_none(row.get("year")),
        "hours_estimated": _float_or_none(row.get("hours_estimated")),
        "notes": _str_or_none(row.get("notes")),
        "source": "import",
    }


def parse_upload(
    content: bytes,
    filename: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Parse an Excel (.xlsx/.xls) or CSV file.

    Returns:
        (rows, errors) where:
          - rows: list of dicts ready for Course(**row) creation
          - errors: list of human-readable error messages for invalid rows
    """
    errors: list[str] = []

    try:
        if filename.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content), dtype=str)
        elif filename.lower().endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content), dtype=str, encoding="utf-8-sig")
        else:
            raise ValueError(
                f"Format de fichier non supporté : '{filename}'. "
                "Formats acceptés : .xlsx, .xls, .csv"
            )
    except ValueError:
        raise
    except Exception as exc:
        logger.error("Erreur de lecture du fichier '%s' : %s", filename, exc)
        raise ValueError(f"Impossible de lire le fichier : {exc}") from exc

    df = _normalize_columns(df)

    try:
        _validate_columns(df)
    except ValueError:
        raise

    rows: list[dict[str, Any]] = []

    for idx, row in df.iterrows():
        title_raw = row.get("title")
        if pd.isna(title_raw) or str(title_raw).strip() == "":
            errors.append(f"Ligne {idx + 2} ignorée : colonne 'title' vide.")
            continue
        try:
            cleaned = _clean_row(row)
            rows.append(cleaned)
        except Exception as exc:
            errors.append(f"Ligne {idx + 2} ignorée : {exc}")

    logger.info(
        "Import '%s' : %d lignes valides, %d erreurs.", filename, len(rows), len(errors)
    )
    return rows, errors
