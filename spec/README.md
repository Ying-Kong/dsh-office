# Spec: facts and ops

These two JSON documents are the public contract of dsh-office. Everything else
(the panel, the adapter, the repair loop) is a consumer.

- [`facts.schema.json`](facts.schema.json) — what `extract` reports about a document.
- [`ops.schema.json`](ops.schema.json) — what `fill` is allowed to do.

## Why the split exists

`facts` is **observation**: read from the tree, never invented. `ops` is
**intent**: authored by a human or a model, validated before execution.

Keeping them apart is what makes the verifier possible: verification is
"re-observe, then diff against intent".

## Identifier rules

| kind | format | assigned by |
|---|---|---|
| paragraph | `p{n}` | body order |
| table | `t{n}` | body order |
| cell | `t{n}r{row}c{col}` | row/column order, merged cells deduplicated |
| slot | `s{n}` | detection order |
| figure number | `1..n` | `figure_start` + order of `append_content` |

Ids are stable for a given template build. They are **not** stable across
template edits — that is why `ops.template.content_sha256` exists and why `fill`
refuses to run on a different build unless `--force` is passed.

## Adding an op

1. Add the shape to `ops.schema.json` (closed `oneOf`, no free-form `additionalProperties`).
2. Implement it in `python/office_core/ops.py` (`OpRunner` handler, whitelisted).
3. Add the matching assertion to `python/office_core/verify.py` — an op you
   cannot verify is an op you cannot ship.
4. Add a test to `python/tests/test_ops.py` and one to `test_verify.py`.
5. Update the README table and `CHANGELOG.md`.

Ops must be idempotent in the sense that replaying the same list on the same
template yields the same content fingerprint. If your op depends on wall-clock
time, random values or network state, it does not belong here.

## Adding a locator

Locators are resolved in `python/office_core/index.py::resolve_target`.
A new locator must:

- raise `TargetNotFound` when it cannot resolve (never silently do nothing);
- be deterministic (no "closest match" scoring);
- appear in `ops.schema.json` and in the README preference table.
