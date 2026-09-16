"""Secret detection and redaction during indexing.

Repository content is untrusted. Likely secrets are detected with conservative
regex patterns and redacted before storage/retrieval so they never reach logs,
the database, or the LLM.
"""
from __future__ import annotations

import re

REDACTED = "[REDACTED_SECRET]"

# (pattern, description) — deliberately conservative to limit false positives.
_GENERIC_CREDENTIAL = re.compile(
    r"(?i)\b(api[_-]?key|secret[_-]?key|auth[_-]?token|access[_-]?token)"
    r"\s*[=:]\s*['\"]?[A-Za-z0-9_\-\.]{12,}"
)
SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(sk-[A-Za-z0-9_\-]{20,})"), "OpenAI-style API key"),
    (re.compile(r"\b(ghp_[A-Za-z0-9]{30,})"), "GitHub PAT"),
    (re.compile(r"\b(gho_[A-Za-z0-9]{30,})"), "GitHub OAuth token"),
    (re.compile(r"\b(xox[baprs]-[A-Za-z0-9\-]{10,})"), "Slack token"),
    (re.compile(r"\b(AKIA[0-9A-Z]{16})\b"), "AWS access key id"),
    (re.compile(r"-----BEGIN (RSA |EC |OPENSSH |PGP |DSA )?PRIVATE KEY-----"), "private key block"),
    (re.compile(r"(?i)\b(password|passwd|pwd)\s*[=:]\s*['\"]?[^'\"\s]{6,}"), "password assignment"),
    (_GENERIC_CREDENTIAL, "generic credential assignment"),
]


def find_secrets(text: str) -> list[tuple[int, int, int, str]]:
    """Return list of (line_number, start_col, end_col, description)."""
    findings: list[tuple[int, int, int, str]] = []
    for pattern, description in SECRET_PATTERNS:
        for m in pattern.finditer(text):
            line_no = text.count("\n", 0, m.start()) + 1
            line_start = text.rfind("\n", 0, m.start()) + 1
            line_end = text.find("\n", m.end())
            if line_end == -1:
                line_end = len(text)
            findings.append((line_no, m.start() - line_start, m.end() - line_start, description))
    return findings


def redact(text: str) -> str:
    """Replace likely secret values with REDACTED, preserving key names.

    Quoted values keep their quotes in the replacement so the result stays a
    syntactically valid string literal: `key = "secret"` -> `key = "[REDACTED_SECRET]"`.
    Some patterns consume the opening quote inside the match while the closing
    quote lies just outside it (the match ends at the value's last char), so
    the replacement re-balances by wrapping REDACTED in the detected quote.
    """
    out = text
    for pattern, _ in SECRET_PATTERNS:
        def _sub(m: re.Match[str]) -> str:
            whole = m.group(0)
            for sep in ("=", ":"):
                idx = whole.find(sep)
                if idx != -1:
                    prefix = whole[: idx + 1]
                    rest = whole[idx + 1:]
                    stripped = rest.lstrip()
                    if stripped[:1] in ("'", '"'):
                        # The opening quote was consumed inside the match; the
                        # source's own closing quote sits just past the match
                        # end. Re-emit only the opening quote so the string
                        # literal stays balanced and parseable.
                        return prefix + rest[: len(rest) - len(stripped)] + stripped[0] + REDACTED
                    return prefix + REDACTED
            return REDACTED
        out = pattern.sub(_sub, out)
    return out
