"""Tests export PDF d'une proposition de cours (Phase 2.1).

Contrats vérifiés : `specs/export-pdf.md`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO

import pytest
from docx import Document
from sqlalchemy import select

from app.api.export import DOCX_MEDIA_TYPE
from app.models.audit_log import AuditLog
from app.models.course_proposal import CourseProposal
from app.services.export_service import (
    _format_json_field,
    _to_latin1,
    build_proposal_content,
    build_proposal_filename,
    render_proposal_docx,
    render_proposal_pdf,
)

PDF_MAGIC = b"%PDF-"


async def _register_and_login(client, email: str, password: str = "validpass1") -> None:
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    await client.post("/api/v1/auth/login", json={"email": email, "password": password})


async def _create_proposal(client, **overrides) -> int:
    payload = {
        "title": "Excel perfectionnement",
        "description": "Tableaux croisés dynamiques.",
        "hours_estimated": 21,
        "certification_suggestions": '[{"type": "RNCP", "label": "Titre RNCP 35148"}]',
        "based_on": '[{"source": "market_course", "id": 4}]',
        "status": "proposed",
    }
    payload.update(overrides)
    resp = await client.post("/api/v1/proposals", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _make_proposal(**overrides) -> CourseProposal:
    """Instance détachée — le rendu ne touche pas la base."""
    values = {
        "id": 1,
        "title": "Excel perfectionnement",
        "description": "Tableaux croisés dynamiques.",
        "hours_estimated": 21.0,
        "certification_suggestions": None,
        "based_on": None,
        "status": "proposed",
        "created_at": datetime(2026, 3, 4, tzinfo=UTC),
    }
    values.update(overrides)
    proposal = CourseProposal()
    for key, value in values.items():
        setattr(proposal, key, value)
    return proposal


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_export_returns_pdf(client):
    await _register_and_login(client, "admin@test.com")
    proposal_id = await _create_proposal(client)

    resp = await client.get(f"/api/v1/export/proposals/{proposal_id}.pdf")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(PDF_MAGIC)
    assert len(resp.content) > 800


@pytest.mark.asyncio
async def test_export_sets_download_filename(client):
    await _register_and_login(client, "admin@test.com")
    proposal_id = await _create_proposal(client, title="Excel perfectionnement — avancé")

    resp = await client.get(f"/api/v1/export/proposals/{proposal_id}.pdf")

    disposition = resp.headers["content-disposition"]
    assert disposition.startswith("attachment;")
    # Accents et tirets cadratins ne doivent pas fuiter dans un nom de fichier.
    assert f'filename="proposition-{proposal_id}-excel-perfectionnement-avance.pdf"' in disposition


@pytest.mark.asyncio
async def test_export_unknown_proposal_returns_404(client):
    await _register_and_login(client, "admin@test.com")
    resp = await client.get("/api/v1/export/proposals/9999.pdf")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_export_unauthenticated_returns_401(client):
    resp = await client.get("/api/v1/export/proposals/1.pdf")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_export_does_not_modify_proposal(client):
    """Méthode sûre : un GET ne fait pas basculer le statut métier."""
    await _register_and_login(client, "admin@test.com")
    proposal_id = await _create_proposal(client, status="draft")

    await client.get(f"/api/v1/export/proposals/{proposal_id}.pdf")

    resp = await client.get(f"/api/v1/proposals/{proposal_id}")
    assert resp.json()["status"] == "draft"


@pytest.mark.asyncio
async def test_export_writes_audit_log(client, db_session):
    await _register_and_login(client, "admin@test.com")
    proposal_id = await _create_proposal(client)

    await client.get(f"/api/v1/export/proposals/{proposal_id}.pdf")

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "export_proposal_pdf")
    )
    logs = list(result.scalars().all())
    assert len(logs) == 1
    assert logs[0].target == f"course_proposal:{proposal_id}"


@pytest.mark.asyncio
async def test_export_audit_actions_name_their_format(client, db_session):
    """Les deux formats doivent être distinguables en analyse de journal."""
    await _register_and_login(client, "admin@test.com")
    proposal_id = await _create_proposal(client)

    await client.get(f"/api/v1/export/proposals/{proposal_id}.pdf")
    await client.get(f"/api/v1/export/proposals/{proposal_id}.docx")

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.action.like("export_proposal%"))
    )
    actions = sorted(log.action for log in result.scalars().all())
    assert actions == ["export_proposal_docx", "export_proposal_pdf"]


@pytest.mark.asyncio
async def test_export_survives_empty_optional_fields(client):
    """Une proposition minimale doit tout de même produire un PDF."""
    await _register_and_login(client, "admin@test.com")
    proposal_id = await _create_proposal(
        client,
        description=None,
        hours_estimated=None,
        certification_suggestions=None,
        based_on=None,
    )

    resp = await client.get(f"/api/v1/export/proposals/{proposal_id}.pdf")

    assert resp.status_code == 200
    assert resp.content.startswith(PDF_MAGIC)


@pytest.mark.asyncio
async def test_export_survives_invalid_json_fields(client):
    """Un JSON mal formé en base ne doit pas faire échouer l'export."""
    await _register_and_login(client, "admin@test.com")
    proposal_id = await _create_proposal(
        client, certification_suggestions="{pas du json", based_on="[[["
    )

    resp = await client.get(f"/api/v1/export/proposals/{proposal_id}.pdf")

    assert resp.status_code == 200
    assert resp.content.startswith(PDF_MAGIC)


# ---------------------------------------------------------------------------
# Rendu (unitaire)
# ---------------------------------------------------------------------------

def test_render_handles_non_latin1_characters():
    """Un caractère hors latin-1 est retiré, pas propagé en exception."""
    pdf = render_proposal_pdf(
        _make_proposal(title="Formation 日本語 🎓 — avancé", description="→ Ω ≈ ∑")
    )
    assert pdf.startswith(PDF_MAGIC)


def test_render_handles_very_long_title():
    pdf = render_proposal_pdf(_make_proposal(title="A" * 512))
    assert pdf.startswith(PDF_MAGIC)


def test_to_latin1_normalises_typography():
    # Apostrophe courbe U+2019 : le cas le plus fréquent en français.
    assert _to_latin1("l’été — «oui»…") == "l'été - «oui»..."


def test_to_latin1_keeps_french_accents():
    assert _to_latin1("Éàçüö") == "Éàçüö"


def test_to_latin1_strips_control_characters():
    """Les caractères de contrôle sont valides en latin-1 : à retirer explicitement."""
    assert _to_latin1("A\x00B\x07C") == "ABC"


def test_to_latin1_keeps_newlines_and_tabs():
    assert _to_latin1("ligne1\nligne2\tfin") == "ligne1\nligne2\tfin"


def test_format_json_field_renders_certifications():
    raw = (
        '[{"type": "RNCP", "label": "Titre RNCP 35148"}, '
        '{"type": "Badge", "label": "Open Badge"}]'
    )
    assert _format_json_field(raw) == "Titre RNCP 35148 (RNCP) · Open Badge (Badge)"


def test_format_json_field_renders_bare_references():
    assert _format_json_field('[{"source": "market_course", "id": 4}]') == "market_course #4"


def test_format_json_field_returns_dash_when_empty():
    assert _format_json_field(None) == "—"
    assert _format_json_field("   ") == "—"


def test_format_json_field_passes_through_invalid_json():
    assert _format_json_field("{pas du json") == "{pas du json"


def test_filename_is_slugified():
    proposal = _make_proposal(id=7, title="Excel — perfectionnement (avancé) !")
    assert (
        build_proposal_filename(proposal, "pdf")
        == "proposition-7-excel-perfectionnement-avance.pdf"
    )


def test_filename_falls_back_when_title_has_no_ascii():
    proposal = _make_proposal(id=3, title="日本語")
    assert build_proposal_filename(proposal, "pdf") == "proposition-3-proposition.pdf"


def test_filename_carries_requested_extension():
    proposal = _make_proposal(id=7, title="Excel")
    assert build_proposal_filename(proposal, "docx") == "proposition-7-excel.docx"


# ---------------------------------------------------------------------------
# Export Word (Phase 2.2)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_export_docx_returns_word_document(client):
    await _register_and_login(client, "admin@test.com")
    proposal_id = await _create_proposal(client)

    resp = await client.get(f"/api/v1/export/proposals/{proposal_id}.docx")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == DOCX_MEDIA_TYPE
    # Un .docx est une archive ZIP.
    assert resp.content.startswith(b"PK")
    assert len(resp.content) > 5000


@pytest.mark.asyncio
async def test_export_docx_sets_download_filename(client):
    await _register_and_login(client, "admin@test.com")
    proposal_id = await _create_proposal(client, title="Excel perfectionnement")

    resp = await client.get(f"/api/v1/export/proposals/{proposal_id}.docx")

    assert (
        f'filename="proposition-{proposal_id}-excel-perfectionnement.docx"'
        in resp.headers["content-disposition"]
    )


@pytest.mark.asyncio
async def test_export_docx_unknown_proposal_returns_404(client):
    await _register_and_login(client, "admin@test.com")
    resp = await client.get("/api/v1/export/proposals/9999.docx")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_export_docx_unauthenticated_returns_401(client):
    resp = await client.get("/api/v1/export/proposals/1.docx")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_export_docx_does_not_modify_proposal(client):
    await _register_and_login(client, "admin@test.com")
    proposal_id = await _create_proposal(client, status="draft")

    await client.get(f"/api/v1/export/proposals/{proposal_id}.docx")

    resp = await client.get(f"/api/v1/proposals/{proposal_id}")
    assert resp.json()["status"] == "draft"


@pytest.mark.asyncio
async def test_export_docx_writes_audit_log(client, db_session):
    await _register_and_login(client, "admin@test.com")
    proposal_id = await _create_proposal(client)

    await client.get(f"/api/v1/export/proposals/{proposal_id}.docx")

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "export_proposal_docx")
    )
    logs = list(result.scalars().all())
    assert len(logs) == 1
    assert logs[0].target == f"course_proposal:{proposal_id}"


def _docx_text(data: bytes) -> str:
    return "\n".join(p.text for p in Document(BytesIO(data)).paragraphs)


def test_render_docx_contains_title_and_sections():
    text = _docx_text(render_proposal_docx(_make_proposal()))

    assert "Excel perfectionnement" in text
    assert "Statut : Proposé" in text
    for heading in (
        "Heures estimées",
        "Description",
        "Pistes de certification",
        "Éléments d'origine",
    ):
        assert heading in text


def test_render_docx_keeps_non_latin1_characters():
    """Différence assumée avec le PDF : le .docx est de l'UTF-8, rien n'est retiré."""
    text = _docx_text(
        render_proposal_docx(_make_proposal(title="Formation 日本語 🎓"))
    )
    assert "日本語" in text
    assert "🎓" in text


def test_render_docx_shows_dash_for_empty_fields():
    text = _docx_text(
        render_proposal_docx(
            _make_proposal(
                description=None,
                hours_estimated=None,
                certification_suggestions=None,
                based_on=None,
            )
        )
    )
    assert "None" not in text
    assert "—" in text


def test_render_docx_survives_invalid_json():
    data = render_proposal_docx(
        _make_proposal(certification_suggestions="{pas du json", based_on="[[[")
    )
    assert data.startswith(b"PK")


def test_pdf_and_docx_share_the_same_content_source():
    """Un champ ajouté doit apparaître dans les deux formats sans double saisie."""
    proposal = _make_proposal()
    content = build_proposal_content(proposal)
    text = _docx_text(render_proposal_docx(proposal))

    assert content.title in text
    assert content.subtitle in text
    for heading, body in content.sections:
        assert heading in text
        assert body in text
