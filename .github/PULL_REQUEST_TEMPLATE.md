## What & why

<!-- one paragraph; link the issue if there is one -->

## Checklist

- [ ] Every new op has a **verifier assertion** (`python/office_core/verify.py`)
- [ ] Locators raise `TargetNotFound` instead of falling back
- [ ] Tests added/updated (python and/or node), suite green locally (`make test`)
- [ ] No new mandatory dependency in the core
- [ ] `CHANGELOG.md` updated if behaviour changes
- [ ] Determinism untouched **or** explained (`content_sha256` change)

## Verification

<!-- paste `make test` summary and, if rendering changed, `dsh-office verify` output -->
