"""Stable identifiers for a document's nodes.

Ids are assigned by walking the body in document order, so the same template
always yields the same ids. Both ``extract`` and the op interpreter use this
module; if they disagreed, a locator would silently point at the wrong node.
"""

from __future__ import annotations

from docx.oxml.ns import qn

from .docx_io import cell_text, logical_text
from .errors import TargetNotFound


class DocIndex:
    def __init__(self, doc):
        self.doc = doc
        self.paragraphs: dict[str, object] = {}
        self.cells: dict[str, object] = {}
        self.cell_order: list[str] = []
        self.label_to_cell: dict[str, str] = {}
        self._build()

    # -- construction -----------------------------------------------------
    def _build(self) -> None:
        body = self.doc.element.body
        p_index = 0
        t_index = 0
        for child in body.iterchildren():
            if child.tag == qn("w:p"):
                from docx.text.paragraph import Paragraph

                pid = f"p{p_index}"
                self.paragraphs[pid] = Paragraph(child, self.doc)
                p_index += 1
            elif child.tag == qn("w:tbl"):
                from docx.table import Table

                table = Table(child, self.doc)
                self._index_table(table, t_index)
                t_index += 1

    def _index_table(self, table, t_index: int) -> None:
        seen: set[int] = set()
        for r_index, row in enumerate(table.rows):
            for c_index, cell in enumerate(row.cells):
                if id(cell._tc) in seen:
                    continue
                seen.add(id(cell._tc))
                cid = f"t{t_index}r{r_index}c{c_index}"
                self.cells[cid] = cell
                self.cell_order.append(cid)
                text = cell_text(cell).strip()
                if text and len(text) <= 14 and "\n" not in text and text not in self.label_to_cell:
                    self.label_to_cell[text] = cid

    # -- lookups ----------------------------------------------------------
    def paragraph(self, pid: str):
        if pid not in self.paragraphs:
            raise TargetNotFound(f"paragraph {pid} does not exist", target={"by": "paragraph-id", "id": pid})
        return self.paragraphs[pid]

    def cell(self, cid: str):
        if cid not in self.cells:
            raise TargetNotFound(f"cell {cid} does not exist", target={"by": "cell-id", "id": cid})
        return self.cells[cid]

    def cell_after_label(self, label: str):
        """The cell immediately to the right of the cell whose text is *label*.

        Returned id is the neighbour, never the label cell itself - writing into
        the label would overwrite the form instead of filling it.
        """
        cid = self.label_to_cell.get(label.strip())
        if cid is None:
            raise TargetNotFound(f"no cell labelled {label!r}", target={"by": "cell-label", "label": label})
        neighbour = self.next_cell_id(cid)
        if neighbour is None:
            raise TargetNotFound(f"cell labelled {label!r} has no cell to its right",
                                 target={"by": "cell-label", "label": label})
        return neighbour, self.cells[neighbour]

    def next_cell_id(self, cid: str) -> str | None:
        """Id of the cell to the right in the same row, or None at the row end."""
        try:
            position = self.cell_order.index(cid)
        except ValueError:  # pragma: no cover - defensive
            return None
        # ids look like t0r1c5: table 0, row 1, column 5
        table, rest = cid[1:].split("r", 1)
        row, col = rest.split("c", 1)
        candidate = f"t{table}r{row}c{int(col) + 1}"
        return candidate if position + 1 < len(self.cell_order) and self.cell_order[position + 1] == candidate else None

    def paragraphs_containing(self, needle: str) -> list[str]:
        from .docx_io import logical_text as _text

        return [pid for pid, p in self.paragraphs.items() if needle in _text(p)]


def resolve_target(index: DocIndex, target: dict):
    """Resolve a target spec into ``("cell", cid, cell)`` or ``("paragraph", pid, paragraph)``."""
    kind = target.get("by")
    if kind == "cell-id":
        cid = target["id"]
        return "cell", cid, index.cell(cid)
    if kind == "cell-label":
        cid, cell = index.cell_after_label(target["label"])
        return "cell", cid, cell
    if kind == "paragraph-id":
        pid = target["id"]
        return "paragraph", pid, index.paragraph(pid)
    if kind == "paragraph-text":
        needle = target["text"]
        matches = index.paragraphs_containing(needle)
        if not matches:
            raise TargetNotFound(f"no paragraph containing {needle!r}", target=target)
        nth = int(target.get("nth", 0))
        if nth >= len(matches):
            raise TargetNotFound(f"paragraph containing {needle!r} has only {len(matches)} match(es)", target=target)
        pid = matches[nth]
        return "paragraph", pid, index.paragraph(pid)
    raise TargetNotFound(f"unsupported locator {kind!r}", target=target)
