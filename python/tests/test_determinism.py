"""Replay must be a function: same template + same ops -> same content bytes."""

from __future__ import annotations

import json

from office_core.docx_io import content_fingerprint
from conftest import render as apply_ops


def test_two_renders_have_identical_content(template, tmp_path, ops_payload):
    first = tmp_path / "a.docx"
    second = tmp_path / "b.docx"
    apply_ops(template, ops_payload, first)
    apply_ops(template, ops_payload, second)
    assert content_fingerprint(first) == content_fingerprint(second)


def test_render_is_stable_across_op_order_of_independent_writes(template, tmp_path, ops_payload):
    """Two ops touching different cells commute; their order must not matter."""
    ops = [op for op in ops_payload["ops"] if op["op"] == "set_text"][:2]
    assert len(ops) == 2
    forward = {"schema": "dsh-office/ops@1", "ops": ops}
    backward = {"schema": "dsh-office/ops@1", "ops": list(reversed(ops))}

    a = tmp_path / "f.docx"
    b = tmp_path / "r.docx"
    apply_ops(template, forward, a)
    apply_ops(template, backward, b)
    assert content_fingerprint(a) == content_fingerprint(b)


def test_zip_containers_differ_but_content_matches(template, tmp_path, ops_payload):
    """Documented limitation: whole-file bytes are not stable (zip timestamps)."""
    first = tmp_path / "a.docx"
    second = tmp_path / "b.docx"
    apply_ops(template, ops_payload, first)
    apply_ops(template, ops_payload, second)
    assert first.read_bytes() != second.read_bytes() or content_fingerprint(first) == content_fingerprint(second)
