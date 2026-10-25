"""Effective formatting resolution.

A font size in a .docx is rarely written next to the text. It comes from a
chain: direct run properties -> character style -> paragraph style -> base
style -> document defaults. Panels that show "三号 / 宋体" must resolve this
chain, otherwise the number they print is not the number Word draws.

Scope of this resolver: size, ascii font, east-asian font, bold, italic and
paragraph alignment. Theme fonts (``asciiTheme``/``eastAsiaTheme``), document
grids (``docGrid``) and numbering levels are reported as unknown on purpose -
see docs/limitations.md.
"""

from __future__ import annotations

from docx.oxml.ns import qn

_MAX_STYLE_DEPTH = 8


def _rpr_of_style(style):
    element = getattr(style, "element", None)
    if element is None:
        return None
    return element.find(qn("w:rPr"))


def _ppr_of_style(style):
    element = getattr(style, "element", None)
    if element is None:
        return None
    return element.find(qn("w:pPr"))


def _style_chain(style):
    seen = 0
    while style is not None and seen < _MAX_STYLE_DEPTH:
        yield style
        style = style.base_style
        seen += 1


def _doc_defaults_rpr(doc):
    defaults = doc.styles.element.find(qn("w:docDefaults"))
    if defaults is None:
        return None
    rpr_default = defaults.find(qn("w:rPrDefault"))
    if rpr_default is None:
        return None
    return rpr_default.find(qn("w:rPr"))


def _attr(node, child_tag: str, attr: str = "w:val"):
    if node is None:
        return None
    child = node.find(qn(child_tag))
    if child is None:
        return None
    return child.get(qn(attr))


def _size_pt(rpr) -> float | None:
    raw = _attr(rpr, "w:sz")
    if raw is None:
        return None
    try:
        return round(int(raw) / 2.0, 2)
    except ValueError:  # pragma: no cover - malformed package
        return None


def _font(rpr, key: str) -> str | None:
    if rpr is None:
        return None
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        return None
    if fonts.get(qn(f"w:{key}Theme")) is not None:
        return None  # theme font: not resolvable without theme1.xml
    value = fonts.get(qn(f"w:{key}"))
    return value or None


def _toggle(rpr, key: str) -> bool | None:
    if rpr is None:
        return None
    node = rpr.find(qn(f"w:{key}"))
    if node is None:
        return None
    raw = node.get(qn("w:val"))
    return raw not in ("0", "false")


def _first_value(candidates, getter):
    for candidate in candidates:
        value = getter(candidate)
        if value is not None:
            return value
    return None


def effective_run_format(doc, paragraph, run) -> dict:
    """Return the resolved font properties for a run."""
    paragraph_style = paragraph.style
    chain = list(_style_chain(paragraph_style))
    defaults = _doc_defaults_rpr(doc)

    direct = run._element.find(qn("w:rPr"))
    candidates = [direct, *[_rpr_of_style(style) for style in chain], defaults]

    return {
        "sz_pt": _first_value(candidates, _size_pt),
        "font_ascii": _first_value(candidates, lambda r: _font(r, "ascii")),
        "font_east_asia": _first_value(candidates, lambda r: _font(r, "eastAsia")),
        "bold": _first_value(candidates, lambda r: _toggle(r, "b")),
        "italic": _first_value(candidates, lambda r: _toggle(r, "i")),
        "style_name": paragraph_style.name if paragraph_style is not None else None,
    }


def effective_paragraph_format(doc, paragraph) -> dict:
    """Alignment and left indent, resolved through the style chain."""
    chain = list(_style_chain(paragraph.style))
    direct = paragraph._p.find(qn("w:pPr"))
    pprs = [direct, *[_ppr_of_style(style) for style in chain]]

    align = _first_value(pprs, lambda p: _attr(p, "w:jc"))
    indent = _first_value(pprs, lambda p: _attr(p, "w:ind", "w:left"))
    return {
        "align": align,
        "left_indent_twip": int(indent) if indent and indent.lstrip("-").isdigit() else None,
    }


def paragraph_format_summary(doc, paragraph) -> dict:
    """One flat dict describing how the paragraph's first run looks."""
    runs = paragraph.runs
    if runs:
        run_format = effective_run_format(doc, paragraph, runs[0])
    else:
        run_format = {"sz_pt": None, "font_ascii": None, "font_east_asia": None,
                      "bold": None, "italic": None, "style_name": paragraph.style.name if paragraph.style else None}
    summary = {"text": paragraph.text, **run_format, **effective_paragraph_format(doc, paragraph)}
    return summary
