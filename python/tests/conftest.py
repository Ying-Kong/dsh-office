"""Shared fixtures.

Every temp file stays inside the repository (``.pytest-work/``) so the suite
never touches paths outside this project - see CONTRIBUTING.md.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TEMPLATE = REPO / "fixtures" / "templates" / "report.docx"
OPS = REPO / "fixtures" / "reporter" / "ops.json"
IMAGES = REPO / "fixtures" / "images"


@pytest.fixture()
def template() -> Path:
    return TEMPLATE


@pytest.fixture()
def ops_payload() -> dict:
    import json

    return json.loads(OPS.read_text(encoding="utf-8"))


@pytest.fixture()
def workdir(tmp_path: Path) -> Path:
    return tmp_path


def render(template_path, payload, out_path, **kwargs):
    """Apply ops the way the CLI does: images resolve next to the ops file."""
    from office_core.ops import apply_ops

    return apply_ops(template_path, payload, out_path, base_dir=OPS.parent, **kwargs)


@pytest.fixture()
def filled(tmp_path: Path) -> Path:
    """A document rendered through the reference ops file."""
    from office_core.ops import apply_ops

    import json

    import json as _json

    out = tmp_path / "filled.docx"
    render(TEMPLATE, _json.loads(OPS.read_text(encoding="utf-8")), out)
    return out


@pytest.fixture()
def split_run_docx(tmp_path: Path) -> Path:
    """A document whose sentence is split across several runs, as Word does."""
    from docx import Document

    doc = Document()
    paragraph = doc.add_paragraph()
    paragraph.add_run("指导")
    paragraph.add_run("老师")
    paragraph.add_run("：")
    paragraph.add_run("李老师")
    path = tmp_path / "split.docx"
    doc.save(str(path))
    return path


@pytest.fixture()
def copy_of_template(tmp_path: Path) -> Path:
    target = tmp_path / "template.docx"
    shutil.copyfile(TEMPLATE, target)
    return target
