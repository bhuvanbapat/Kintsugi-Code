"""Secure recursive repository scanner.

Repositories are untrusted input: paths are normalized, size limits are
enforced, ignore rules exclude generated/vendored directories, and no
repository script is ever executed.
"""
from __future__ import annotations

import hashlib
import time
from pathlib import Path, PurePosixPath

from app.core.config import get_settings
from app.core.logging import get_logger
from app.indexing.language import (
    detect_language,
    is_config_file,
    is_doc_file,
    is_manifest_file,
    is_source_file,
    is_test_file,
)
from app.models.domain import FileEntry, Repository, ScanResult

log = get_logger(__name__)

DEFAULT_IGNORED_DIRS = {
    ".git", ".hg", ".svn", "node_modules", ".venv", "venv", "__pycache__",
    "dist", "build", "target", "out", ".next", ".nuxt", ".cache", ".idea",
    ".vscode", ".tox", ".mypy_cache", ".pytest_cache", "vendor", "pods",
    ".terraform", "coverage", ".circleci", "__snapshots__",
}
DEFAULT_IGNORED_FILES = {
    ".env", ".env.local", ".env.production", ".env.development",
    "id_rsa", "id_ed25519", ".npmrc", ".netrc", ".aws/credentials",
}
IGNORED_FILE_EXTENSIONS = {
    ".pyc", ".pyo", ".so", ".dll", ".exe", ".bin", ".o", ".a", ".class",
    ".jar", ".woff", ".woff2", ".ttf", ".eot", ".png", ".jpg", ".jpeg",
    ".gif", ".ico", ".svgz", ".pdf", ".zip", ".tar", ".gz", ".7z", ".rar",
    ".lock", ".ds_store", ".egg", ".whl", ".wasm", ".mp4", ".mp3",
}
SECRET_FILE_PATTERNS = ("id_rsa", "id_dsa", "id_ed25519", ".pem", ".p12", ".pfx", ".keystore")


def normalize_repo_path(raw_path: str) -> Path:
    """Resolve a user-supplied repository path and validate it exists."""
    p = Path(raw_path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"Repository path does not exist: {raw_path}")
    if not p.is_dir():
        raise NotADirectoryError(f"Repository path is not a directory: {raw_path}")
    return p


def _is_ignored(relative_posix: str, extra_ignores: set[str]) -> bool:
    parts = PurePosixPath(relative_posix).parts
    name = parts[-1] if parts else relative_posix
    lowered = relative_posix.lower()
    for pattern in extra_ignores:
        pat = pattern.strip().lower().rstrip("/")
        if not pat:
            continue
        if any(part == pat for part in parts):
            return True
        if pat.endswith("/*"):
            if any(part == pat[:-2] for part in parts):
                return True
    for part in parts:
        if part.lower() in DEFAULT_IGNORED_DIRS:
            return True
    if name.lower() in DEFAULT_IGNORED_FILES:
        return True
    if PurePosixPath(name).suffix.lower() in IGNORED_FILE_EXTENSIONS:
        return True
    if any(pattern in lowered for pattern in SECRET_FILE_PATTERNS):
        return True
    return False


class RepositoryScanner:
    def __init__(self, extra_ignores: list[str] | None = None) -> None:
        self.settings = get_settings()
        self.extra_ignores = {p for p in (extra_ignores or [])}

    def scan(self, repo: Repository) -> ScanResult:
        start = time.monotonic()
        root = normalize_repo_path(repo.root_path)
        settings = self.settings
        files: list[FileEntry] = []
        languages: dict[str, int] = {}
        ignored = 0
        errors = 0

        for dirpath, dirnames, filenames in os_walk(root):
            # Prune ignored directories in-place for efficiency.
            extra_dir_ignores = {
                p.strip().lower().rstrip("/") for p in self.extra_ignores if "/" not in p
            }
            dirnames[:] = [
                d for d in dirnames
                if d.lower() not in DEFAULT_IGNORED_DIRS
                and d.lower() not in extra_dir_ignores
            ]
            for filename in filenames:
                full = Path(dirpath) / filename
                rel = full.relative_to(root).as_posix()
                if _is_ignored(rel, self.extra_ignores):
                    ignored += 1
                    continue
                try:
                    size = full.stat().st_size
                except OSError:
                    errors += 1
                    continue
                if size > settings.max_index_file_size_bytes:
                    ignored += 1
                    continue
                if len(files) >= settings.max_repository_files:
                    log.warning("Max repository file count reached (%s); truncating scan",
                                settings.max_repository_files)
                    break
                try:
                    text = read_text_safe(full)
                    line_count = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
                    sha = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()
                except Exception:
                    line_count = 0
                    sha = ""
                language = detect_language(rel)
                if language:
                    languages[language] = languages.get(language, 0) + 1
                files.append(FileEntry(
                    path=rel,
                    language=language,
                    size_bytes=size,
                    line_count=line_count,
                    is_test=is_test_file(rel),
                    is_doc=is_doc_file(rel),
                    is_config=is_config_file(rel),
                    is_manifest=is_manifest_file(rel),
                    is_source=is_source_file(rel, language),
                    sha256=sha,
                ))

        source_count = sum(1 for f in files if f.is_source)
        test_count = sum(1 for f in files if f.is_test)
        doc_count = sum(1 for f in files if f.is_doc)
        config_count = sum(1 for f in files if f.is_config)
        duration_ms = int((time.monotonic() - start) * 1000)
        log.info("Scanned %s: %d files (%d ignored) in %dms", repo.name, len(files), ignored, duration_ms)
        return ScanResult(
            repository_id=repo.id,
            root_path=str(root),
            total_files=len(files),
            source_files=source_count,
            test_files=test_count,
            doc_files=doc_count,
            config_files=config_count,
            ignored_files=ignored,
            parse_errors=errors,
            languages=languages,
            files=files,
            duration_ms=duration_ms,
        )


def os_walk(root: Path):
    """Thin wrapper so tests can monkeypatch traversal if needed."""
    import os

    yield from os.walk(root, followlinks=False)


def read_text_safe(path: Path) -> str:
    """Read text files, tolerating encoding issues; return '' for binary-looking data."""
    try:
        data = path.read_bytes()
    except OSError:
        return ""
    if b"\x00" in data[:4096]:
        return ""
    return data.decode("utf-8", errors="replace")
