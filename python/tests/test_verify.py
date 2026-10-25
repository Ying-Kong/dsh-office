"""Verification must fail loudly on tampering - that is the whole product."""

from __future__ import annotations

import pytest

from office_core.docx_io import load_docx
from office_core.index import DocIndex
from office_core.verify import verify


def _checks(report, name):
    return [item for item in report["hard"] if item["check"] == name]


def test_clean_render_passes(filled, ops_payload):
    report = verify(filled, ops_payload)
    assert report["ok"] is True
    assert report["hard"] == []
    assert report["images"] == 2
    assert report["captions"] == [1, 2]


def test_wrong_slot_value_is_a_hard_error(filled, ops_payload):
    doc = load_docx(filled)
    index = DocIndex(doc)
    index.cells["t0r1c5"].paragraphs[0].runs[0].text = "张三"
    tampered = filled.with_name("tampered.docx")
    doc.save(str(tampered))

    report = verify(tampered, ops_payload)
    assert report["ok"] is False
    errors = _checks(report, "set_text")
    assert errors and "李老师" in errors[0]["detail"]


def test_foreign_font_is_a_hard_error(filled, ops_payload):
    doc = load_docx(filled)
    index = DocIndex(doc)
    target = next(p for p in index.cells["t0r5c0"].paragraphs if p.text.strip())
    run = target.runs[0]
    run.font.name = "Comic Sans MS"  # writes w:rFonts/w:ascii through python-docx
    tampered = filled.with_name("font.docx")
    doc.save(str(tampered))

    report = verify(tampered, ops_payload)
    assert report["ok"] is False
    assert _checks(report, "font_whitelist")


def test_caption_numbering_gap_is_a_hard_error(filled, ops_payload):
    doc = load_docx(filled)
    index = DocIndex(doc)
    cell = index.cells["t0r5c0"]
    for paragraph in cell.paragraphs:
        if paragraph.text.strip().startswith("图 2"):
            for run in paragraph.runs:
                if "图 2" in run.text:
                    run.text = run.text.replace("图 2", "图 5")
    tampered = filled.with_name("captions.docx")
    doc.save(str(tampered))

    report = verify(tampered, ops_payload)
    assert report["ok"] is False
    assert _checks(report, "caption_numbering")


def test_platform_default_fonts_are_only_a_soft_warning(filled, ops_payload):
    report = verify(filled, ops_payload)
    soft = {item["check"] for item in report["soft"]}
    assert "platform_default_fonts" in soft  # template was produced on Linux
    assert report["ok"] is True
