"""Verification: re-read the rendered document and prove the ops landed.

The point is not to trust the writer. Every op is re-checked against the output
tree, and a small set of document-wide invariants (font whitelist, figure
numbering, placeholder leftovers) is enforced. Failures are split into ``hard``
(must be fixed before delivery) and ``soft`` (reported, never looped on).
"""

from __future__ import annotations

import re
from pathlib import Path

from .docx_io import cell_text, image_count, load_docx, logical_text
from .index import DocIndex, resolve_target
from .schemas import VERIFY_SCHEMA
from .styles import effective_run_format

CAPTION_RE = re.compile(r"^图\s*(\d+)\b")
PLACEHOLDER_RE = re.compile(r"\{\{.*?\}\}|<<.*?>>")

DEFAULT_FONT_WHITELIST = [
    "宋体", "黑体", "微软雅黑", "SimSun", "SimHei", "Microsoft YaHei",
    "Times New Roman", "Arial", "Calibri", "Consolas", "Courier New", "Cambria",
]


def _hard(checks: list, check: str, detail: str, **extra) -> None:
    checks.append({"check": check, "detail": detail, **extra})


def _run_fonts(doc) -> list[tuple[str, str]]:
    """(paragraph-id-or-cell-id, font) for every run that states a font."""
    index = DocIndex(doc)
    findings: list[tuple[str, str]] = []
    for pid, paragraph in index.paragraphs.items():
        for run in paragraph.runs:
            if not run.text.strip():
                continue
            fmt = effective_run_format(doc, paragraph, run)
            for key in ("font_ascii", "font_east_asia"):
                value = fmt.get(key)
                if value:
                    findings.append((pid, value))
    for cid, cell in index.cells.items():
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                if not run.text.strip():
                    continue
                fmt = effective_run_format(doc, paragraph, run)
                for key in ("font_ascii", "font_east_asia"):
                    value = fmt.get(key)
                    if value:
                        findings.append((cid, value))
    return findings


def verify(doc_path: str | Path, ops_payload: dict, *, font_whitelist: list[str] | None = None,
           figure_start: int | None = None, max_figure_width_cm: float = 15.0) -> dict:
    doc = load_docx(doc_path)
    index = DocIndex(doc)
    whitelist = set(font_whitelist or DEFAULT_FONT_WHITELIST)
    start = int(figure_start if figure_start is not None else ops_payload.get("figure_start", 1))

    hard: list[dict] = []
    soft: list[dict] = []
    checked = 0
    counter = start  # figure numbering restarts at the ops-declared start

    # ---- op-level assertions -------------------------------------------
    for position, op in enumerate(ops_payload.get("ops", [])):
        kind = op["op"]
        if kind == "set_text":
            kind_target, node_id, node = resolve_target(index, op["target"])
            actual = cell_text(node).strip() if kind_target == "cell" else logical_text(node)
            checked += 1
            if actual.strip() != str(op["value"]).strip():
                _hard(hard, "set_text", f"ops[{position}] expected {op['value']!r} at {node_id}, found {actual!r}",
                      op_index=position, target=node_id)
        elif kind == "replace_in_paragraph":
            _, node_id, node = resolve_target(index, op["target"])
            actual = logical_text(node)
            checked += 1
            if op["replace"] not in actual:
                _hard(hard, "replace_in_paragraph",
                      f"ops[{position}] replacement missing at {node_id}: {actual!r}",
                      op_index=position, target=node_id)
        elif kind == "append_content":
            _, cell_id, cell = resolve_target(index, op["into"])
            texts = [logical_text(p) for p in cell.paragraphs]
            blob = "\n".join(texts)
            for item in op["items"]:
                checked += 1
                if item["kind"] in ("paragraph", "heading"):
                    if item["text"] not in blob:
                        _hard(hard, "append_content",
                              f"ops[{position}] text missing from {cell_id}: {item['text'][:30]!r}",
                              op_index=position, target=cell_id)
                elif item["kind"] == "figure":
                    if item.get("caption"):
                        expected = item["caption"].replace("{n}", str(counter))
                        counter += 1
                        if expected not in blob:
                            _hard(hard, "append_content",
                                  f"ops[{position}] caption missing from {cell_id}: {expected!r}",
                                  op_index=position, target=cell_id)
        elif kind == "set_format":
            _, node_id, node = resolve_target(index, op["target"])
            spec = op.get("format", op)
            paragraphs = node.paragraphs if isinstance(node, type(node)) and hasattr(node, "paragraphs") else [node]
            for paragraph in paragraphs:
                for run in paragraph.runs:
                    fmt = effective_run_format(doc, paragraph, run)
                    checked += 1
                    if "sz_pt" in spec and fmt.get("sz_pt") != spec["sz_pt"]:
                        _hard(hard, "set_format", f"ops[{position}] size at {node_id} is {fmt.get('sz_pt')}, expected {spec['sz_pt']}",
                              op_index=position, target=node_id)
                    if "font_east_asia" in spec and fmt.get("font_east_asia") != spec["font_east_asia"]:
                        _hard(hard, "set_format", f"ops[{position}] font at {node_id} is {fmt.get('font_east_asia')}, expected {spec['font_east_asia']}",
                              op_index=position, target=node_id)

    # ---- document-wide invariants --------------------------------------
    inserted_figures = sum(1 for op in ops_payload.get("ops", []) if op["op"] == "append_content"
                           for item in op.get("items", []) if item.get("kind") == "figure")
    if inserted_figures:
        expected_images = image_count(doc)
        if expected_images < inserted_figures:
            _hard(hard, "figure_count", f"expected at least {inserted_figures} images, found {expected_images}")

    numbers = sorted(n for text in _all_paragraphs(doc)
                     if (m := CAPTION_RE.match(text.strip())) for n in [int(m.group(1))])
    if numbers:
        expected = list(range(start, start + len(numbers)))
        if numbers != expected:
            _hard(hard, "caption_numbering", f"captions {numbers} are not sequential from {start}")

    for cid_or_pid, font in _run_fonts(doc):
        if font not in whitelist:
            _hard(hard, "font_whitelist", f"{cid_or_pid} uses {font!r}, not in the allowed set")

    for pid, paragraph in DocIndex(doc).paragraphs.items():
        text = logical_text(paragraph)
        if PLACEHOLDER_RE.search(text):
            _hard(hard, "placeholders_left", f"{pid} still contains a placeholder: {text[:40]!r}")

    default_fonts = _doc_default_fonts(doc)
    foreign = sorted({f for f in default_fonts if f and f not in whitelist})
    if foreign:
        soft.append({"check": "platform_default_fonts",
                     "detail": f"document defaults name {foreign}; they will be substituted on other platforms"})

    for shape in doc.inline_shapes:
        width_cm = round(shape.width.cm, 2)
        if width_cm > max_figure_width_cm:
            _hard(hard, "figure_width", f"an image is {width_cm}cm wide, limit is {max_figure_width_cm}cm")
        else:
            soft.append({"check": "figure_width", "detail": f"image width {width_cm}cm within limit"})

    return {
        "schema": VERIFY_SCHEMA,
        "ok": not hard,
        "document": str(doc_path),
        "checked": checked,
        "images": image_count(doc),
        "captions": numbers,
        "hard": hard,
        "soft": soft,
    }


def _doc_default_fonts(doc) -> list[str]:
    from docx.oxml.ns import qn

    defaults = doc.styles.element.find(qn("w:docDefaults"))
    if defaults is None:
        return []
    rpr = defaults.find(qn("w:rPrDefault"))
    rpr = rpr.find(qn("w:rPr")) if rpr is not None else None
    if rpr is None:
        return []
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        return []
    return [fonts.get(qn("w:ascii")) or "", fonts.get(qn("w:eastAsia")) or ""]


def _all_paragraphs(doc) -> list[str]:
    texts = [logical_text(p) for p in doc.paragraphs]
    for cell in DocIndex(doc).cells.values():
        texts.extend(logical_text(p) for p in cell.paragraphs)
    return texts
