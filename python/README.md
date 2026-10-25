# dsh-office-core (Python)

Deterministic OOXML template filling: fact extraction, declarative ops,
verification. This package has no DSH dependency and no network access.

```bash
pip install -e ".[dev]"
python -m pytest
dsh-office extract template.docx -o facts.json
dsh-office fill template.docx ops.json -o rendered.docx
dsh-office verify rendered.docx ops.json
```

Library use:

```python
from office_core import extract, apply_ops, verify

facts = extract("template.docx")
result = apply_ops("template.docx", ops_dict, "rendered.docx")
report = verify("rendered.docx", ops_dict)
assert report["ok"], report["hard"]
```

Exit codes and schemas are documented in the top-level `README.md` and `spec/`.
