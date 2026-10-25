# Changelog

All notable changes to this project. Format: [Keep a Changelog](https://keepachangelog.com/),
versioning: [SemVer](https://semver.org/).

## [0.1.1] - 2026-10-25

Load-time compatibility fix for the DSH adapter. The Python core is unchanged.

### Fixed
- **`defineTool` output** — the host's `defineTool` reads `options.output.render`
  and threw on load; every tool now declares a canonical output schema plus a
  text renderer. Regression test asserts the shape, because a faked `defineTool`
  cannot catch it.
- **Peer resolution for linked installs** — `import('@deepseek-ai/dsh-tools')`
  from the plugin fails when the profile installs it with `link:`, because the
  real files live outside the profile tree. `apply()` now falls back to
  resolving the peer from the profile working directory.

### Changed
- `engines.dsh` and the `@deepseek-ai/dsh-tools` peer range are now
  `>=0.2.0-0`. The previous `*` does not match a prerelease, and the host runs
  `0.2.1-rc.2`.
- Verified against DSH `0.2.1-rc.2` / Node `24.16.0`: the config tree mounts the
  row without warnings and the host's own `defineTool` accepts all three tools.

### Note
`v0.1.0` was tagged before this fix and its adapter does not load. Use `v0.1.1`.

## [0.1.0] - 2026-10-25

First usable cut: extract → fill → verify, Word only.

### Added
- `extract`: run-merged paragraph text, resolved font size/fonts through the
  style chain, stable paragraph/table/cell ids, page geometry, heuristic slot
  detection (`label-right-cell`, `date-line`, `underscore`) with confidence.
- `fill`: op interpreter with a closed whitelist (`set_text`,
  `replace_in_paragraph`, `set_format`, `append_content`) and schema validation
  against `spec/ops.schema.json`.
- `append_content`: paragraphs, headings and figures; `{n}` caption numbering,
  width cap, caption kept with the figure, trailing placeholder paragraphs
  trimmed.
- `verify`: per-op re-checks plus document invariants (font whitelist,
  sequential caption numbers, placeholder leftovers, image width), split into
  hard/soft findings; stable exit codes.
- Template fingerprint guard (`content_sha256`), `--force` override.
- DSH adapter (`node/src/plugin.mjs`) with three tools; dependency-free CLI
  wrapper (`node/src/core.mjs`).
- Reference fixture built from a real course report form, anonymised
  (`张三` / `2023000000001` / `李老师`) and shipping unwatermarked full-size
  screenshots: 25 Python tests, 10 Node tests, deterministic content fingerprint.
- `tools/sanitize_fixture.py`: redact a contributed form without collapsing run
  formatting; exits non-zero when a token is split across runs.

### Known limitations
- Pagination is not asserted (engine-dependent).
- Theme fonts / document grids resolve to `null`.
- Excel and PowerPoint are not implemented.
