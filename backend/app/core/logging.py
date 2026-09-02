"""Structured logging that never logs secrets."""
from __future__ import annotations

import logging
import re

_SECRET_PATTERNS = [
    re.compile(r"(sk-[A-Za-z0-9_\-]{16,})"),
    re.compile(r"(ghp_[A-Za-z0-9_]{20,})"),
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[=:]\s*\S+", ),
]
_REDACTED = "[REDACTED]"


def redact_secrets(text: str) -> str:
    out = text
    for pattern in _SECRET_PATTERNS:
        out = pattern.sub(_REDACTED, out)
    return out


class SecretRedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.args:
            record.args = tuple(redact_secrets(str(a)) for a in record.args)
        if hasattr(record, "msg") and record.msg:
            record.msg = redact_secrets(str(record.msg))
        return True


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        handler.addFilter(SecretRedactingFilter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger
