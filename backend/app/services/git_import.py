"""Git clone import: securely clone a remote repository for indexing.

Security: clones into a dedicated, sandboxed directory with a timeout,
depth limit, and rejects non-http(s) URLs (no ssh/file/transport tricks).
The resulting tree is then treated exactly like a local repo by the scanner.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
import tempfile
from pathlib import Path

from app.core.logging import get_logger

log = get_logger(__name__)

_ALLOWED_URL = re.compile(r"^https://[A-Za-z0-9._\-]+(:443)?/[A-Za-z0-9._\-/~%]+/?$")
MAX_DEPTH = 50
CLONE_TIMEOUT_SECONDS = 300


def validate_git_url(url: str) -> None:
    """Accept only https GitHub-style URLs; reject everything else."""
    url = url.strip()
    if not _ALLOWED_URL.match(url):
        raise ValueError(
            "only https:// git URLs are supported "
            "(e.g. https://github.com/owner/repo)"
        )
    if ".." in url:
        raise ValueError("traversal sequences are not allowed in URLs")


def clone_repository(url: str, target_root: Path | None = None) -> Path:
    """Clone `url` (https only, depth-limited) and return the local path."""
    validate_git_url(url)
    base = target_root or Path(tempfile.gettempdir()) / "codeforge-clones"
    base.mkdir(parents=True, exist_ok=True)
    # Deterministic dir name from the URL: stable digest (PYTHONHASHSEED-proof)
    # so the same URL maps to the same cache dir across process restarts.
    url_digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:8]
    tail = url.rstrip("/").split("/")[-1].replace(".git", "") or "repo"
    dest = base / f"{tail}-{url_digest}"
    if dest.exists():
        # Reuse an existing clone; caller can re-index to refresh.
        return dest
    cmd = [
        "git", "clone", "--depth", str(MAX_DEPTH), "--single-branch",
        "--filter=blob:none", url, str(dest),
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=CLONE_TIMEOUT_SECONDS,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(f"clone timed out after {CLONE_TIMEOUT_SECONDS}s") from exc
    if result.returncode != 0:
        raise RuntimeError(f"git clone failed: {result.stderr[:300]}")
    log.info("cloned %s -> %s", url, dest)
    return dest
