"""The CLI is the contract the Node adapter codes against: exit codes included."""

from __future__ import annotations

import json

from click.testing import CliRunner

from conftest import OPS
from office_core.cli import main


def test_extract_prints_json(template):
    result = CliRunner().invoke(main, ["extract", str(template)])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["schema"] == "dsh-office/facts@1"
    assert payload["slots"]


def test_fill_then_verify_roundtrip(template, tmp_path):
    ops_path = OPS
    out = tmp_path / "out.docx"

    runner = CliRunner()
    fill = runner.invoke(main, ["fill", str(template), str(ops_path), "-o", str(out)])
    assert fill.exit_code == 0, fill.output

    verify = runner.invoke(main, ["verify", str(out), str(ops_path)])
    assert verify.exit_code == 0, verify.output
    assert json.loads(verify.output)["ok"] is True


def test_verify_exits_3_on_hard_errors(template, tmp_path):
    ops_path = OPS
    out = tmp_path / "out.docx"
    runner = CliRunner()
    runner.invoke(main, ["fill", str(template), str(ops_path), "-o", str(out)])

    # verify the *template* against ops authored for a filled doc
    bad = runner.invoke(main, ["verify", str(template), str(ops_path)])
    assert bad.exit_code == 3

    relaxed = runner.invoke(main, ["verify", str(template), str(ops_path), "--allow-fail"])
    assert relaxed.exit_code == 0


def test_missing_document_is_reported(tmp_path):
    result = CliRunner().invoke(main, ["extract", str(tmp_path / "nope.docx")])
    assert result.exit_code != 0
