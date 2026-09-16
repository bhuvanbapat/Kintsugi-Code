"""Structured logging that never logs secrets.

Redaction is enforced at THREE layers, so it holds regardless of which
logger/handler topology a record travels through:

1. LogRecord FACTORY (primary): `logging.setLogRecordFactory` wraps record
   creation for the whole process. Every record — from any logger,
   including uvicorn/uvicorn.access and third-party libraries that
   propagate to root — is redacted at creation, before any handler,
   filter, or formatter can see the raw values.

2. Logger-level filters on root + the uvicorn logger family (defense in
   depth for handlers attached later that might bypass the factory,
   e.g. a subprocess re-importing logging differently).

3. Handler-level filter on loggers built via get_logger().

Secrets covered: values in `record.msg`, in `record.args` (tuple or dict),
and in exception text. Python logging formats `record.exc_info` at emit
time through the handler's Formatter — after any filter could act — so
exc-carrying records are pre-formatted once, redacted, cached in
`record.exc_text`, and `exc_info` is cleared. The standard Formatter emits
the cached `exc_text` rather than re-formatting the tuple, which makes the
redacted traceback the one that reaches the console.
"""
from __future__ import annotations

import logging
import re
import traceback

_SECRET_PATTERNS = [
    re.compile(r"(sk-[A-Za-z0-9_\-]{16,})"),
    re.compile(r"(ghp_[A-Za-z0-9_]{20,})"),
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[=:]\s*\S+", ),
]
_REDACTED = "[REDACTED]"

# Loggers owned by the ASGI server; records logged there never traverse
# application loggers, so they get explicit logger-level filters as well.
_SERVER_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access", "uvicorn.asgi")

_factory_installed = False


def redact_secrets(text: str) -> str:
    out = text
    for pattern in _SECRET_PATTERNS:
        out = pattern.sub(_REDACTED, out)
    return out


def _redact_record(record: logging.LogRecord) -> logging.LogRecord:
    """Redact a record in place: msg, args (tuple or dict), exc text."""
    try:
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: redact_secrets(str(v)) for k, v in record.args.items()}
            else:
                record.args = tuple(redact_secrets(str(a)) for a in record.args)
        if hasattr(record, "msg") and record.msg:
            record.msg = redact_secrets(str(record.msg))
        if record.exc_info and not getattr(record, "exc_text", None):
            text = "".join(traceback.format_exception(*record.exc_info))
            record.exc_text = redact_secrets(text)
            record.exc_info = None  # formatter must not re-format the raw tuple
        elif getattr(record, "exc_text", None):
            record.exc_text = redact_secrets(record.exc_text or "")
    except Exception:  # noqa: BLE001 — redaction must never break logging
        pass
    return record


def _redacting_record_factory(*args: object, **kwargs: object) -> logging.LogRecord:
    record = _original_factory(*args, **kwargs)  # type: ignore[misc]
    return _redact_record(record)


_original_factory = logging.getLogRecordFactory()


class SecretRedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        _redact_record(record)
        return True


def _add_filter(target: logging.Logger | logging.Handler) -> None:
    if not any(isinstance(f, SecretRedactingFilter) for f in target.filters):
        target.addFilter(SecretRedactingFilter())


def install() -> None:
    """Install redaction on every relevant logging path.

    - global LogRecord factory (all records, all loggers, all handlers);
    - root logger + uvicorn logger family (defense in depth);
    - handlers currently attached to those loggers.
    """
    global _factory_installed, _original_factory
    if not _factory_installed:
        _original_factory = logging.getLogRecordFactory()
        logging.setLogRecordFactory(_redacting_record_factory)
        _factory_installed = True
    root = logging.getLogger()
    _add_filter(root)
    for name in _SERVER_LOGGERS:
        lg = logging.getLogger(name)
        _add_filter(lg)
        for handler in lg.handlers:
            _add_filter(handler)


def get_logger(name: str) -> logging.Logger:
    install()
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
        logger.propagate = False
        # Local handler filter as well: covered even if some other tool
        # resets the global record factory.
        _add_filter(handler)
    return logger
