# Contributing

Thanks for considering it. This project is deliberately small; the fastest way
to get a PR merged is to keep it that way.

## Setup

```bash
make setup          # python venv + editable install of python/ (with dev extras)
make test           # python (24 tests) + node (10 tests)
make demo           # render fixtures/reporter -> .scratch/demo.docx
```

Requirements: Python ≥ 3.10, Node ≥ 20.11. No Node runtime dependencies are
allowed in `node/src` (a test enforces that the adapter is dependency-free).

## Ground rules

1. **Every op needs a verifier assertion.** An op you cannot prove landed is an
   op that will silently produce a wrong document. `verify.py` and the test that
   covers it are part of the feature, not follow-up work.
2. **Locators fail loudly.** No "best effort" matching, no fallback that writes
   into a neighbouring cell. `TargetNotFound` is a feature.
3. **No new mandatory dependencies** in the core. Optional backends (Word COM,
   Excel, OCR) must be opt-in and degrade to a documented error.
4. **Tests stay inside the repo.** The suite writes only to `.pytest-work/`,
   `.scratch/` and `.node-work-*/`. Never read or modify paths outside the
   checkout; CI runs with a read-only home to catch violations.
5. **Determinism is testable.** If your change touches rendering, run
   `test_determinism.py` and keep content fingerprints stable.

## Where a change goes

| You want to… | Touch | Keep out of |
|---|---|---|
| support a new document feature | `python/office_core/docx_io.py`, `index.py` | `node/` |
| add an op | `ops.schema.json` → `ops.py` → `verify.py` → tests | `node/src/core.mjs` |
| add a locator | `index.py::resolve_target` + schema + README table | detection heuristics |
| improve slot detection | `extract.py::_detect_slots` + a fixture + confidence | locators |
| change the panel | `node/src/client/` (0.3) | the CLI contract |
| add a format (Excel) | `python/office_core/sources/` (0.4) | `ops.py` semantics |

## Good first issues

- `SOURCE_DATE_EPOCH` support so two renders are byte-identical.
- `--diff` between two op sets (paragraph-level).
- Slot detection for underlined blanks (`w:u val="single"` with spaces).
- A CI job that renders the demo on Windows and uploads the PDF.
- Presets: one ops file per common report form, with the template removed or
  anonymised.

## Reporting a bug

Include the output of:

```bash
dsh-office extract template.docx -o facts.json
dsh-office verify rendered.docx ops.json
```

…plus the template itself when you can share it. Template drift (the ops were
authored for an older build) is the most common cause of `exit code 4`; say so
instead of filing it as a bug.

## Commit style

Conventional-ish and scoped: `feat(ops): add append_table`, `fix(verify): count
captions inside cells`, `docs: explain fingerprint guard`. One behaviour change
per PR.
