"""Security regression tests: secret redaction across logging paths.

Each test inspects ACTUAL EMITTED LOG OUTPUT (captured via handlers), not
merely the redact_secrets helper.
"""
from __future__ import annotations

import logging

from app.core.logging import SecretRedactingFilter, install, redact_secrets

FAKE_OPENAI_KEY = "sk-abcdefghijklmnopqrstuv"
FAKE_GITHUB_PAT = "ghp_abcdefghijklmnopqrstuvwxyz"


def _make_capture() -> logging.Logger:
    """Build a logger whose output we can inspect after emission."""
    logger = logging.getLogger("test.redaction_probe")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    logger.handlers.clear()
    import io

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(name)s %(levelname)s: %(message)s"))
    logger.addHandler(handler)
    logger.addFilter(SecretRedactingFilter())
    logger._test_stream = stream  # type: ignore[attr-defined]
    return logger


def test_normal_message_secret_redacted() -> None:
    logger = _make_capture()
    logger.info(f"processing key {FAKE_OPENAI_KEY} for request")
    out = logger._test_stream.getvalue()  # type: ignore[attr-defined]
    assert FAKE_OPENAI_KEY not in out
    assert "[REDACTED]" in out


def test_secret_in_log_arguments_redacted() -> None:
    logger = _make_capture()
    logger.warning("auth failed for token %s", FAKE_GITHUB_PAT)
    out = logger._test_stream.getvalue()  # type: ignore[attr-defined]
    assert FAKE_GITHUB_PAT not in out
    assert "[REDACTED]" in out


def test_secret_in_exception_text_redacted() -> None:
    """logger.exception(...) emits a traceback; the emitted traceback text
    must not contain the secret."""
    logger = _make_capture()
    try:
        raise RuntimeError(f"connection with token={FAKE_OPENAI_KEY} refused")
    except RuntimeError:
        logger.exception("request handler crashed")
    out = logger._test_stream.getvalue()  # type: ignore[attr-defined]
    assert FAKE_OPENAI_KEY not in out, f"secret leaked into traceback:\n{out}"
    assert "[REDACTED]" in out
    assert "RuntimeError" in out  # traceback structure preserved


def test_secret_in_exc_info_via_root_logger() -> None:
    """Records logged through a logger with no own filter still pass the
    root-level filter installed by install()."""
    install()
    probe = logging.getLogger("some_library_or_server")  # no get_logger
    probe.setLevel(logging.DEBUG)
    probe.propagate = True  # let the record reach root handlers
    import io

    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    saved_level = root.level
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)
    try:
        try:
            raise ValueError(f"bad token {FAKE_GITHUB_PAT}")
        except ValueError:
            logging.getLogger("some_library_or_server").exception("boom")
        out = stream.getvalue()
        assert FAKE_GITHUB_PAT not in out, f"secret leaked via root path:\n{out}"
        assert "[REDACTED]" in out
    finally:
        root.handlers = saved_handlers
        root.setLevel(saved_level)


def test_server_logger_family_covered_by_install() -> None:
    """install() must attach the filter to uvicorn loggers so ASGI-server
    records are redacted too."""
    install()
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        assert any(isinstance(f, SecretRedactingFilter) for f in lg.filters), (
            f"uvicorn logger {name} missing SecretRedactingFilter"
        )
    root = logging.getLogger()
    assert any(isinstance(f, SecretRedactingFilter) for f in root.filters)


def test_redact_secrets_helper_contracts() -> None:
    assert redact_secrets(f"key={FAKE_OPENAI_KEY}") == "key=[REDACTED]"
    assert redact_secrets("no secrets here") == "no secrets here"
