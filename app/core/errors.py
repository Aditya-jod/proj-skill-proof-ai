from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger("skillproof")


class SkillProofError(Exception):
    """Base application exception for predictable failures."""

    def __init__(self, message: str, *, code: str = "internal_error", context: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.code = code
        self.context = context or {}


class AgentExecutionError(SkillProofError):
    """Raised when an agent fails during observe/decide/act."""


class ServiceError(SkillProofError):
    """Raised for downstream service or CRUD failures."""


@dataclass
class ErrorPayload:
    code: str
    message: str
    details: Dict[str, Any]

    def as_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details}


def build_error_payload(exc: SkillProofError | Exception, *, fallback_code: str = "internal_error") -> ErrorPayload:
    if isinstance(exc, SkillProofError):
        logger.warning("Handled SkillProofError", exc_info=exc)
        return ErrorPayload(code=exc.code, message=str(exc), details=exc.context)
    logger.exception("Unhandled exception", exc_info=exc)
    return ErrorPayload(code=fallback_code, message="Unexpected server error", details={})
