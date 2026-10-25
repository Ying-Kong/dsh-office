"""Exceptions shared across the core.

Every failure mode is distinguishable by exception type so callers (CLI, the
Node adapter, the repair loop) can branch without string matching.
"""


class OfficeCoreError(Exception):
    """Base class for all dsh-office errors."""

    code = "office_error"

    def __init__(self, message: str, **detail):
        super().__init__(message)
        self.detail = detail

    def as_dict(self) -> dict:
        return {"code": self.code, "message": str(self), **self.detail}


class TemplateMismatch(OfficeCoreError):
    """The document is not the template the ops were authored against."""

    code = "template_mismatch"


class UnsupportedDocument(OfficeCoreError):
    """Not a .docx/OOXML package we can read (e.g. legacy .doc, .docm)."""

    code = "unsupported_document"


class OpsRejected(OfficeCoreError):
    """Ops file failed schema validation or references something missing."""

    code = "ops_rejected"


class TargetNotFound(OfficeCoreError):
    """A locator did not resolve. Always an error, never a silent no-op."""

    code = "target_not_found"


class VerificationFailed(OfficeCoreError):
    """Hard verification errors were found in the rendered document."""

    code = "verification_failed"

    def __init__(self, report: dict):
        super().__init__(f"{len(report.get('hard', []))} hard verification error(s)", report=report)
        self.report = report
