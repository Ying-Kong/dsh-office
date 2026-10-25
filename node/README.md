# @dsh-office/plugin

DSH adapter for [`dsh-office-core`](../python). Registers three model-facing
tools — `office_extract`, `office_fill`, `office_verify` — and forwards them to
the Python CLI. No document logic lives here, and there are no runtime
dependencies by design.

Not published to npm yet:

```bash
npm pack                                   # dsh-office-plugin-0.1.2.tgz
dsh plugin --profile web add ./dsh-office-plugin-0.1.2.tgz
# or, while developing:
dsh plugin --profile web add /absolute/path/to/dsh-office/node
```

The bundle patch mounts the row on install, so nothing to enable manually. Make sure the Python core is
importable: `export DSH_OFFICE_PYTHON=/path/to/dsh-office/.venv/bin/python`.

Configuration (all optional):

| option | default | meaning |
|---|---|---|
| `pythonPath` | `$DSH_OFFICE_PYTHON`, repo `.venv`, `python3` | interpreter that can `import office_core` |
| `cwd` | process cwd | base directory for relative paths in tool arguments |

Compatibility: tested against DSH `0.2.1-rc.2`; declares `engines.dsh >=0.2.0-0`
and peer `@deepseek-ai/dsh-tools >=0.2.0-0`. If the host changes
`defineTool`'s required options, the plugin fails at load with a clear error
rather than registering half-broken tools.

Tests run without DSH installed (`defineTool` is injected):

```bash
node --test test/core.test.mjs test/plugin.test.mjs
```
