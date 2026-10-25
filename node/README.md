# @dsh-office/plugin

DSH adapter for [`dsh-office-core`](../python). Registers three model-facing
tools — `office_extract`, `office_fill`, `office_verify` — and forwards them to
the Python CLI. No document logic lives here, and there are no runtime
dependencies by design.

```bash
dsh plugin --profile web add @dsh-office/plugin
```

Configuration (all optional):

| option | default | meaning |
|---|---|---|
| `pythonPath` | `$DSH_OFFICE_PYTHON`, repo `.venv`, `python3` | interpreter that can `import office_core` |
| `cwd` | process cwd | base directory for relative paths in tool arguments |

Tests run without DSH installed (`defineTool` is injected):

```bash
node --test "test/*.test.mjs"
```
