"""dsh-office core: OOXML template filling with a deterministic op interpreter."""

__version__ = "0.1.0"

from .extract import extract  # noqa: F401
from .ops import OpRunner, apply_ops, validate_ops  # noqa: F401
from .verify import verify  # noqa: F401

__all__ = ["__version__", "extract", "apply_ops", "validate_ops", "OpRunner", "verify"]
