# Known limitations

Honest list. Everything here was observed while building the reference fixture,
not copied from documentation.

## 1. Byte identity is not promised; content identity is

`zipfile` stores per-entry timestamps, so rendering the same template twice
produces different `.docx` **bytes**. What must be identical is the content
parts:

```
sha256 over (word/document.xml, word/styles.xml, word/numbering.xml, word/media/*)
```

Exposed as `content_sha256` in `fill` output and checked by
`python/tests/test_determinism.py`. If you need byte-identical output for
reproducible builds, pin `SOURCE_DATE_EPOCH` before zipping - not implemented
yet (good first issue).

## 2. Pagination is engine-dependent

LibreOffice and Word break lines differently, and a table row that grows across
a page boundary can move an image to the next page. Verification is therefore
split:

- **structure** (slot values, fonts, figure count, caption numbering) is
  engine-independent and enforced as hard errors;
- **pagination** is not asserted at all.

If you need a layout oracle, render on the target engine (Word COM on Windows,
or a fixed LibreOffice build in CI) and diff page rasters. That is out of scope
for 0.1.0 - see `docs/roadmap.md`.

## 3. Theme fonts and document grids are reported as unknown

`w:rFonts w:asciiTheme="…"` and `w:docGrid w:linePitch="…"` mean the effective
font/size is decided by `theme1.xml` and the section grid, not by the run. The
resolver returns `null` for those rather than guessing.

Consequence: on documents that use theme fonts, the panel's "font" field may be
empty, and a font-whitelist check cannot see the real font. The reference
template does not use theme fonts; the check is exercised in tests.

## 4. `w:shd`-style ordering is enforced manually

python-docx appends new `pPr` children at the end, which violates the OOXML
sequence (`w:shd` must precede `w:tabs`/`w:spacing`/`w:ind`/`w:jc`). Word may
then report "content unreadable". `ops.py::_shade_paragraph` inserts at the
schema position; if you add ops that create `pPr` children, do the same.

## 5. Legacy `.doc` is rejected

`.doc` is a binary format. `extract` refuses it with a clear error instead of
shelling out to a converter. Converting (`soffice --convert-to docx`) is the
caller's job.

## 6. Scope

- Word (`.docx`) only. Excel is scaffolded; PowerPoint is a non-goal.
- No tracked changes, comments, fields, cross-references, TOC.
- Fillable-slot detection is heuristic. It reports `confidence` and `source`;
  anything below 0.6 should be confirmed by a human.
