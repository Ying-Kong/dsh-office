# Roadmap

Ordered by expected value per unit of work. Nothing here is promised.

## 0.2 — repair loop
- `dsh-office repair <doc> <ops> --max-rounds 3`: verification findings become
  op patches, re-render, re-verify. Hard findings only; soft findings never
  trigger a loop.
- Termination guard: a finding that survives two rounds is escalated, not retried.

## 0.3 — the panel
- `ctx.sidebarRightTabs` tab: tree view of slots and resolved typography,
  inline editing of slot values, "re-fill" button.
- Client plugin lives in `node/src/client/` and stays optional: the core must
  remain usable headless.

## 0.4 — Excel
- `xlsx` source adapter: named ranges + placeholder rows as slots.
- Same op set; `append_content` becomes `append_rows`.
- `fixtures/` needs a spreadsheet sample; no LibreOffice dependency allowed.

## 0.5 — Windows oracle
- Optional verifier backend that drives Word COM to render and compare page
  count / line breaks. Windows-only, opt-in, never a required dependency.

## Nice to have
- `SOURCE_DATE_EPOCH` support for byte-identical packages.
- Presets: one `bindings` file per common form (course report, lab sheet),
  contributed by users.
- `--diff` mode: render two op sets and show the paragraph-level difference.
