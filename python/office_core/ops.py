"""Op validation and the deterministic interpreter.

The orchestrating model writes ops (declarative), never code. This module is the
only place that mutates a document, so:

* the op set is a closed whitelist - no arbitrary script can run;
* every op is validated against ``spec/ops.schema.json`` before anything moves;
* replaying the same ops on the same template produces the same content
  fingerprint (see ``tests/test_determinism.py``).
"""

from __future__ import annotations

import json
from pathlib import Path

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

from .docx_io import load_docx, replace_paragraph_text
from .errors import OpsRejected, TargetNotFound, TemplateMismatch
from .index import DocIndex, resolve_target
from .schemas import OPS_SCHEMA
from .styles import effective_run_format

_ALIGN = {
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "center": WD_ALIGN_PARAGRAPH.CENTER,
    "right": WD_ALIGN_PARAGRAPH.RIGHT,
    "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
}

DEFAULT_BODY = {"sz_pt": 10.5, "font_east_asia": "宋体", "font_ascii": "Times New Roman"}
DEFAULT_HEADING = {"sz_pt": 10.5, "font_east_asia": "黑体", "font_ascii": "Times New Roman"}


def load_schema(schema_dir: str | Path | None = None) -> dict:
    base = Path(schema_dir) if schema_dir else Path(__file__).resolve().parents[2] / "spec"
    path = base / "ops.schema.json"
    if not path.is_file():  # pragma: no cover - packaging safety net
        raise OpsRejected(f"ops schema not found at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_ops(payload: dict, schema_dir: str | Path | None = None) -> None:
    try:
        import jsonschema
    except ImportError:  # pragma: no cover - optional dependency
        _minimal_validate(payload)
        return
    try:
        jsonschema.validate(payload, load_schema(schema_dir))
    except jsonschema.ValidationError as exc:
        raise OpsRejected(f"{exc.message} (at {'/'.join(str(p) for p in exc.absolute_path)})") from exc


def _minimal_validate(payload: dict) -> None:
    if not isinstance(payload, dict) or payload.get("schema") != OPS_SCHEMA:
        raise OpsRejected(f"ops file must declare schema {OPS_SCHEMA}")
    ops = payload.get("ops")
    if not isinstance(ops, list) or not ops:
        raise OpsRejected("ops must be a non-empty list")
    allowed = {"set_text", "replace_in_paragraph", "append_content", "set_format"}
    for index, op in enumerate(ops):
        if not isinstance(op, dict) or op.get("op") not in allowed:
            raise OpsRejected(f"ops[{index}]: unsupported op {op.get('op')!r}")


def _style_run(run, *, sz_pt=None, font_east_asia=None, font_ascii=None, bold=None) -> None:
    if sz_pt is not None:
        run.font.size = Pt(sz_pt)
    if bold is not None:
        run.font.bold = bold
    if font_ascii or font_east_asia:
        rpr = run._element.get_or_add_rPr()
        fonts = rpr.find(qn("w:rFonts"))
        if fonts is None:
            fonts = rpr.makeelement(qn("w:rFonts"), {})
            rpr.insert(0, fonts)
        if font_ascii:
            fonts.set(qn("w:ascii"), font_ascii)
            fonts.set(qn("w:hAnsi"), font_ascii)
        if font_east_asia:
            fonts.set(qn("w:eastAsia"), font_east_asia)


def _shade_paragraph(paragraph, fill: str = "F4F4F4") -> None:
    ppr = paragraph._p.get_or_add_pPr()
    shd = ppr.find(qn("w:shd"))
    if shd is None:
        shd = ppr.makeelement(qn("w:shd"), {})
        # w:shd must precede w:tabs/w:spacing/w:ind/w:jc in CT_PPr
        anchor = None
        for tag in ("w:tabs", "w:spacing", "w:ind", "w:jc", "w:rPr"):
            anchor = ppr.find(qn(tag))
            if anchor is not None:
                break
        if anchor is not None:
            anchor.addprevious(shd)
        else:
            ppr.append(shd)
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)


def _trim_trailing_empty(cell) -> int:
    """Drop the blank paragraphs a template uses to reserve row height.

    Without this, appended content starts several lines down and the rendered
    cell shows a gap that nobody authored. The last paragraph is always kept so
    the cell stays valid.
    """
    removed = 0
    for paragraph in list(cell.paragraphs)[1:]:  # never drop the first one
        if paragraph.text.strip():
            continue
        if paragraph._p.find(qn("w:r")) is not None and paragraph._p.find(".//" + qn("w:drawing")) is not None:
            continue
        paragraph._element.getparent().remove(paragraph._element)
        removed += 1
    return removed


class OpRunner:
    """Applies a validated op list to a document, tracking figure numbering."""

    def __init__(self, doc, index: DocIndex, *, figure_start: int = 1, base_dir: Path | None = None):
        self.doc = doc
        self.index = index
        self.figure_no = figure_start
        self.base_dir = Path(base_dir) if base_dir else None

    def _resolve_image(self, image: str) -> Path:
        """Ops files are portable: relative images resolve next to the ops file."""
        candidate = Path(image)
        if candidate.is_absolute():
            return candidate
        for base in (self.base_dir, Path.cwd()):
            if base is not None and (Path(base) / candidate).is_file():
                return Path(base) / candidate
        return candidate

    # -- helpers ----------------------------------------------------------
    def _resolve(self, target: dict):
        return resolve_target(self.index, target)

    def _apply_format(self, paragraph, spec: dict) -> None:
        for run in paragraph.runs:
            _style_run(run, sz_pt=spec.get("sz_pt"), font_east_asia=spec.get("font_east_asia"),
                       font_ascii=spec.get("font_ascii"), bold=spec.get("bold"))
        align = spec.get("align")
        if align:
            paragraph.alignment = _ALIGN[align]

    # -- ops --------------------------------------------------------------
    def set_text(self, op: dict) -> dict:
        kind, node_id, node = self._resolve(op["target"])
        value = op["value"]
        if kind == "cell":
            from .docx_io import set_cell_text

            set_cell_text(node, value)
        else:
            replace_paragraph_text(node, value)
        return {"op": "set_text", "target": node_id, "kind": kind, "value": value}

    def replace_in_paragraph(self, op: dict) -> dict:
        kind, node_id, node = self._resolve(op["target"])
        if kind != "paragraph":
            raise OpsRejected("replace_in_paragraph needs a paragraph target", target=op["target"])
        from .docx_io import logical_text

        before = logical_text(node)
        find, repl = op["find"], op["replace"]
        if find not in before:
            raise TargetNotFound(f"{find!r} not found in paragraph {node_id}", paragraph=node_id)
        after = before.replace(find, repl, 1 if not op.get("all") else -1)
        replace_paragraph_text(node, after)
        return {"op": "replace_in_paragraph", "target": node_id, "before": before, "after": after}

    def set_format(self, op: dict) -> dict:
        kind, node_id, node = self._resolve(op["target"])
        spec = op.get("format", op)
        paragraphs = node.paragraphs if kind == "cell" else [node]
        for paragraph in paragraphs:
            self._apply_format(paragraph, spec)
        return {"op": "set_format", "target": node_id, "kind": kind,
                "applied": {k: v for k, v in spec.items() if k in
                            ("sz_pt", "font_east_asia", "font_ascii", "bold", "align")}}

    def append_content(self, op: dict) -> dict:
        kind, cell_id, cell = self._resolve(op["into"])
        if kind != "cell":
            raise OpsRejected("append_content currently targets a table cell", into=op["into"])
        trimmed = _trim_trailing_empty(cell)
        created = []
        for item in op["items"]:
            item_kind = item["kind"]
            if item_kind in ("paragraph", "heading"):
                paragraph = cell.add_paragraph()
                paragraph.paragraph_format.space_before = Pt(item.get("space_before_pt", 0))
                paragraph.paragraph_format.space_after = Pt(item.get("space_after_pt", 3))
                defaults = DEFAULT_HEADING if item_kind == "heading" else DEFAULT_BODY
                run = paragraph.add_run(item["text"])
                _style_run(run, sz_pt=item.get("sz_pt", defaults["sz_pt"]),
                           font_east_asia=item.get("font_east_asia", defaults["font_east_asia"]),
                           font_ascii=item.get("font_ascii", defaults["font_ascii"]),
                           bold=item.get("bold", item_kind == "heading"))
                if item.get("align"):
                    paragraph.alignment = _ALIGN[item["align"]]
                created.append({"kind": item_kind, "text": item["text"]})
            elif item_kind == "figure":
                image_path = self._resolve_image(item["image"])
                if not image_path.is_file():
                    raise OpsRejected(f"image not found: {image_path}", image=str(image_path))
                caption = item.get("caption", "")
                if "{n}" in caption:
                    caption = caption.replace("{n}", str(self.figure_no))
                paragraph = cell.add_paragraph()
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                paragraph.paragraph_format.space_before = Pt(item.get("space_before_pt", 4))
                paragraph.paragraph_format.space_after = Pt(0)
                width = Cm(float(item.get("width_cm_max", 14.2)))
                run = paragraph.add_run()
                run.add_picture(str(image_path), width=width)
                if caption:
                    paragraph.add_run().add_break()
                    caption_run = paragraph.add_run(caption)
                    _style_run(caption_run, sz_pt=9, font_east_asia="宋体",
                               font_ascii="Times New Roman", bold=False)
                    caption_run.font.color.rgb = __import__("docx").shared.RGBColor(0x59, 0x59, 0x59)
                paragraph.paragraph_format.keep_with_next = bool(item.get("keep_with_next", True))
                created.append({"kind": "figure", "caption": caption, "number": self.figure_no})
                self.figure_no += 1
            else:  # pragma: no cover - schema catches this first
                raise OpsRejected(f"unsupported content item {item_kind!r}")
        return {"op": "append_content", "cell": cell_id, "trimmed_empty_paragraphs": trimmed, "created": created}

    def run(self, ops: list[dict]) -> list[dict]:
        handlers = {
            "set_text": self.set_text,
            "replace_in_paragraph": self.replace_in_paragraph,
            "set_format": self.set_format,
            "append_content": self.append_content,
        }
        applied = []
        for position, op in enumerate(ops):
            handler = handlers.get(op["op"])
            if handler is None:  # pragma: no cover - schema catches this first
                raise OpsRejected(f"ops[{position}]: unsupported op {op['op']!r}")
            applied.append({"index": position, **handler(op)})
        return applied


def apply_ops(template_path: str | Path, ops_payload: dict, out_path: str | Path, *,
              force: bool = False, base_dir: str | Path | None = None) -> dict:
    """Validate, then replay ops onto a copy of the template."""
    validate_ops(ops_payload)
    from .docx_io import content_fingerprint

    declared = (ops_payload.get("template") or {}).get("content_sha256")
    actual = content_fingerprint(template_path)
    if declared and declared != actual and not force:
        raise TemplateMismatch(
            "ops were authored against a different template build",
            expected=declared, actual=actual,
            hint="re-run `dsh-office extract` on this template, or pass --force",
        )

    doc = load_docx(template_path)
    index = DocIndex(doc)
    runner = OpRunner(doc, index, figure_start=int(ops_payload.get("figure_start", 1)), base_dir=base_dir)
    applied = runner.run(ops_payload["ops"])

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    doc.save(str(tmp))
    tmp.replace(out_path)
    return {
        "ok": True,
        "template": str(template_path),
        "output": str(out_path),
        "content_sha256": content_fingerprint(out_path),
        "applied": applied,
    }
