# Security policy

## Supported versions

`main` and the latest tagged release.

## Reporting

Open a **private security advisory** on GitHub
(Security → Advisories → Report a vulnerability). Do not open a public issue.

## Threat model, briefly

dsh-office parses untrusted `.docx` packages provided by third parties (a
teacher's form, a template downloaded from a forum).

| Surface | Mitigation |
|---|---|
| zip bombs / malformed packages | python-docx raises; `fill` writes nothing on failure (tmp file replaced only at the end) |
| macros / OLE | never executed; macros live in `.docm`, which is rejected |
| external images / linked fields | images are embedded by path, never fetched over the network; `verify` has no network access |
| path traversal via ops | image paths are resolved relative to the ops file; absolute paths are the caller's explicit choice |
| model-authored code | **there is no scripting op** — the op set is closed and validated by JSON schema |

The DSH adapter shells out to the Python CLI; it does not pass model text to a
shell. Arguments are passed as argv, not through a shell string.

## Out of scope

Files that are already open in Word (file locks aside), and OS-level
compromise of the machine running the CLI.
