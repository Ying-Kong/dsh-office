"""Command line entry point: extract / fill / verify.

Every command prints one JSON object to stdout so the Node adapter (and any
other agent runtime) can consume it without parsing prose. Diagnostics go to
stderr. Exit codes are stable:

    0  success
    2  ops rejected (schema or reference)
    3  verification failed (hard errors)
    4  template mismatch
    5  target not found
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from . import __version__
from .errors import (OfficeCoreError, OpsRejected, TargetNotFound, TemplateMismatch,
                     VerificationFailed)
from .extract import extract as extract_facts
from .ops import apply_ops
from .verify import verify as verify_doc

EXIT_MAP = {
    OpsRejected: 2,
    VerificationFailed: 3,
    TemplateMismatch: 4,
    TargetNotFound: 5,
}


def _emit(payload: dict) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def _fail(error: OfficeCoreError) -> int:
    json.dump({"ok": False, **error.as_dict()}, sys.stderr, ensure_ascii=False, indent=2)
    sys.stderr.write("\n")
    for kind, code in EXIT_MAP.items():
        if isinstance(error, kind):
            return code
    return 1


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="dsh-office")
def main() -> None:
    """Deterministic OOXML template filling: facts, ops, verification."""


@main.command()
@click.argument("document", type=click.Path(exists=True, dir_okay=False))
@click.option("-o", "--output", type=click.Path(dir_okay=False), default=None,
              help="Write the facts JSON here instead of stdout.")
def extract(document: str, output: str | None) -> None:
    """Read a .docx and emit its fact table (paragraphs, tables, slots)."""
    try:
        facts = extract_facts(document)
    except OfficeCoreError as error:
        raise SystemExit(_fail(error))
    if output:
        Path(output).write_text(json.dumps(facts, ensure_ascii=False, indent=2), encoding="utf-8")
        _emit({"ok": True, "output": output, "slots": len(facts["slots"]),
               "paragraphs": facts["stats"]["paragraphs"]})
    else:
        _emit(facts)


@main.command()
@click.argument("template", type=click.Path(exists=True, dir_okay=False))
@click.argument("ops", type=click.Path(exists=True, dir_okay=False))
@click.option("-o", "--output", required=True, type=click.Path(dir_okay=False), help="Rendered .docx path.")
@click.option("--force", is_flag=True, help="Ignore the template fingerprint in the ops file.")
def fill(template: str, ops: str, output: str, force: bool) -> None:
    """Replay an ops file onto the template and write a new .docx."""
    payload = json.loads(Path(ops).read_text(encoding="utf-8"))
    try:
        result = apply_ops(template, payload, output, force=force, base_dir=Path(ops).parent)
    except OfficeCoreError as error:
        raise SystemExit(_fail(error))
    _emit(result)


@main.command()
@click.argument("document", type=click.Path(exists=True, dir_okay=False))
@click.argument("ops", type=click.Path(exists=True, dir_okay=False))
@click.option("-o", "--output", type=click.Path(dir_okay=False), default=None, help="Write the report here.")
@click.option("--font-whitelist", default=None, help="Comma separated font names that may appear.")
@click.option("--max-width-cm", default=15.0, show_default=True, type=float)
@click.option("--allow-fail", is_flag=True, help="Exit 0 even when hard errors are found.")
def verify(document: str, ops: str, output: str | None, font_whitelist: str | None,
           max_width_cm: float, allow_fail: bool) -> None:
    """Re-read a rendered document and prove the ops landed."""
    payload = json.loads(Path(ops).read_text(encoding="utf-8"))
    whitelist = [f.strip() for f in font_whitelist.split(",")] if font_whitelist else None
    try:
        report = verify_doc(document, payload, font_whitelist=whitelist, max_figure_width_cm=max_width_cm)
    except OfficeCoreError as error:
        raise SystemExit(_fail(error))
    if output:
        Path(output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _emit(report)
    if not report["ok"] and not allow_fail:
        raise SystemExit(_fail(VerificationFailed(report)))


if __name__ == "__main__":  # pragma: no cover
    main()
