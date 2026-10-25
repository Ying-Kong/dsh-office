# Fixtures

Everything here is test-only, anonymised, and safe to publish.

| path | what | notes |
|---|---|---|
| `templates/report.docx` | 2-page course report form: 7-row table, merged cells, `【…】` label cells | anonymised: the student name is `张三`, the id is `2023000000001`. The original `.doc` is **not** shipped |
| `reporter/ops.json` | reference op list: title, teacher, date, content cell with figures, summary | `template.content_sha256` is pinned to the template above |
| `images/fig1.png` | Windows Explorer screenshot (Scala install dir) | no watermark, unmodified full frame |
| `images/fig2.png` | console screenshot, 2524×1136 — used to exercise width capping | no watermark |
| `images/fig3.png` | console screenshot (`scala` greeting) | no watermark |

The template is a real form, which is the point: merged cells, a `【…】` label
cell and a grid-produced `.docx` are what make it a hard case rather than a toy.

## How it was anonymised

```bash
python tools/sanitize_fixture.py fixtures/templates/report.docx \
    --replace "Real Name=张三" \
    --replace "<real-id>=2023000000001"
```

The redaction tool takes its mapping from the command line precisely so the
repository never contains the strings it redacts. If a token is split across
runs the tool exits 1 instead of half-redacting: fix the fixture by hand.

## Adding your own form

1. Convert the form to `.docx`, anonymise it with the command above, and put it
   in `templates/`.
2. `dsh-office extract` it and inspect `slots` + `tables`.
3. Write an `ops.json` by hand — the fixture is the oracle, so don't generate it
   from a model.
4. Pin the new `template.content_sha256` (taken from `extract`) into `ops.json`.
5. Add a test in `python/tests/` that renders and verifies it.
