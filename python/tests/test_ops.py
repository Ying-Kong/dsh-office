"""Ops are the only write path: they must be strict, explicit and reversible."""

from __future__ import annotations

import pytest

from office_core.docx_io import cell_text, load_docx
from office_core.errors import OpsRejected, TargetNotFound, TemplateMismatch
from office_core.index import DocIndex
from office_core.ops import validate_ops
from conftest import render as apply_ops


def _cell(payload, label):
    index = DocIndex(load_docx(payload))
    cid, cell = index.cell_after_label(label)
    return cell_text(cell)


def test_cell_label_writes_the_neighbour_not_the_label(template, tmp_path, ops_payload):
    out = tmp_path / "out.docx"
    apply_ops(template, ops_payload, out)

    doc = load_docx(out)
    index = DocIndex(doc)
    # the label cell still holds the label
    assert cell_text(index.cells["t0r1c4"]).strip() == "指导老师"
    # the value cell holds the value
    assert cell_text(index.cells["t0r1c5"]).strip() == "李老师"


def test_replace_in_paragraph_keeps_the_rest_of_the_line(template, tmp_path, ops_payload):
    out = tmp_path / "out.docx"
    apply_ops(template, ops_payload, out)
    header = next(p for p in load_docx(out).paragraphs if "班级" in p.text)
    assert "2026 年 10 月 24 日" in header.text
    assert "2023000000001" in header.text  # untouched


def test_append_content_adds_paragraphs_and_numbered_figures(template, tmp_path, ops_payload):
    out = tmp_path / "out.docx"
    result = apply_ops(template, ops_payload, out)
    caps = [c["caption"] for op in result["applied"] if op["op"] == "append_content"
            for c in op["created"] if c["kind"] == "figure"]
    assert caps == ["图 1  Scala 2.12.15 解压目录", "图 2  cmd 中输入 scala 进入交互环境"]

    doc = load_docx(out)
    cell = DocIndex(doc).cells["t0r5c0"]
    texts = [p.text for p in cell.paragraphs]
    assert any("一、实验环境与准备" == t for t in texts)
    assert len(doc.inline_shapes) == 2


def test_large_image_is_capped_but_not_distorted(template, tmp_path):
    """fig2 is 2524×1136: a wide console frame, i.e. a full-size screenshot."""
    payload = {"schema": "dsh-office/ops@1", "ops": [
        {"op": "append_content", "into": {"by": "cell-id", "id": "t0r5c0"},
         "items": [{"kind": "figure", "image": "../images/fig2.png",
                    "caption": "图 {n}  大图宽度约束", "width_cm_max": 14.2}]}]}
    out = tmp_path / "wide.docx"
    apply_ops(template, payload, out)

    doc = load_docx(out)
    assert len(doc.inline_shapes) == 1
    shape = doc.inline_shapes[0]
    assert round(shape.width.cm, 1) == 14.2
    # aspect ratio preserved: 2524×1136 within rounding
    assert abs(shape.height.cm / shape.width.cm - 1136 / 2524) < 0.01


def test_unknown_target_is_an_error_not_a_noop(template, tmp_path, ops_payload):
    payload = {"schema": "dsh-office/ops@1", "ops": [
        {"op": "set_text", "target": {"by": "cell-label", "label": "不存在的标签"}, "value": "x"}]}
    with pytest.raises(TargetNotFound):
        apply_ops(template, payload, tmp_path / "x.docx")


def test_schema_rejects_unknown_fields(ops_payload):
    payload = {"schema": "dsh-office/ops@1", "ops": [
        {"op": "set_text", "target": {"by": "cell-id", "id": "t0r0c1"}, "value": "x", "injected": True}]}
    with pytest.raises(OpsRejected):
        validate_ops(payload)


def test_template_fingerprint_guard(template, tmp_path, ops_payload):
    payload = dict(ops_payload)
    payload["template"] = {"content_sha256": "0" * 64}
    with pytest.raises(TemplateMismatch):
        apply_ops(template, payload, tmp_path / "x.docx")
    # explicit override is allowed and documented
    result = apply_ops(template, payload, tmp_path / "y.docx", force=True)
    assert result["ok"] is True


def test_missing_image_is_rejected_before_writing(template, tmp_path):
    payload = {"schema": "dsh-office/ops@1", "ops": [
        {"op": "append_content", "into": {"by": "cell-id", "id": "t0r5c0"},
         "items": [{"kind": "figure", "image": "fixtures/images/nope.png", "caption": "图 {n} x"}]}]}
    with pytest.raises(OpsRejected):
        apply_ops(template, payload, tmp_path / "x.docx")
    assert not (tmp_path / "x.docx").exists()
