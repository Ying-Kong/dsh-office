"""The fact table is the product's interface: if it lies, the panel lies."""

from __future__ import annotations

from office_core.docx_io import logical_text, load_docx
from office_core.extract import extract


def test_schema_and_template_identity(template):
    facts = extract(template)
    assert facts["schema"] == "dsh-office/facts@1"
    assert len(facts["template"]["content_sha256"]) == 64
    # A4 in twips, taken from the template's sectPr
    assert facts["template"]["page"]["width_twip"] == 11906
    assert facts["template"]["page"]["height_twip"] == 16838


def test_slots_cover_the_report_form(template):
    facts = extract(template)
    labels = {slot["label"] for slot in facts["slots"]}
    assert {"实验实训名称", "指导老师"} <= labels
    kinds = {slot["kind"] for slot in facts["slots"]}
    assert "date-inline" in kinds

    teacher = next(slot for slot in facts["slots"] if slot["label"] == "指导老师")
    assert teacher["target"]["by"] == "cell-id"
    assert teacher["current"] == ""
    assert teacher["confidence"] >= 0.9


def test_font_resolution_reaches_the_style_chain(template):
    facts = extract(template)
    header = next(p for p in facts["paragraphs"] if p["id"] == "p2")
    assert "日期" in header["text"]
    # Written nowhere as a direct run property: it comes from the Normal style.
    assert header["sz_pt"] == 12.0
    assert header["font_east_asia"] == "宋体"
    assert header["font_ascii"] == "Times New Roman"


def test_tables_are_reported_in_row_order(template):
    facts = extract(template)
    rows = facts["tables"][0]["rows"]
    assert len(rows) == 7
    assert rows[0][0]["text"] == "实验实训名称"
    assert rows[5][0]["text"].startswith("【实验实训内容及步骤】")


def test_run_splitting_is_undone(split_run_docx):
    doc = load_docx(split_run_docx)
    paragraph = doc.paragraphs[0]
    assert [run.text for run in paragraph.runs] == ["指导", "老师", "：", "李老师"]
    assert logical_text(paragraph) == "指导老师：李老师"
