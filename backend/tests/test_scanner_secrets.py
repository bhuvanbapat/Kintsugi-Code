"""Scanner / language / ignore rules / secret redaction tests."""
from __future__ import annotations

from pathlib import Path

from app.indexing.language import detect_language, is_source_file, is_test_file
from app.indexing.scanner import RepositoryScanner, _is_ignored
from app.indexing.secrets import find_secrets, redact
from app.models.domain import Repository


def test_detect_language() -> None:
    assert detect_language("a/b.py") == "python"
    assert detect_language("src/x.ts") == "typescript"
    assert detect_language("img.png") is None


def test_is_test_file() -> None:
    assert is_test_file("tests/test_x.py")
    assert is_test_file("src/x.test.ts")
    assert not is_test_file("src/x.ts")


def test_is_source_file() -> None:
    assert is_source_file("src/x.ts", "typescript")
    assert not is_source_file("tests/test_x.py", "python")
    assert not is_source_file("x.md", "markdown")


def test_ignore_rules() -> None:
    assert _is_ignored("node_modules/pkg/index.js", set())
    assert _is_ignored(".git/config", set())
    assert _is_ignored("app/__pycache__/x.cpython-311.pyc", set())
    assert _is_ignored("private/id_rsa", set())
    assert _is_ignored("logo.png", set())
    assert not _is_ignored("src/main.py", set())
    assert _is_ignored("dist/bundle.js", set())
    assert _is_ignored("Pods/Alamofire/Source.swift", set())  # was ' Pods' typo


def test_scanner_skips_ignored_and_large(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("def main():\n    pass\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.js").write_text("var a = 1;")
    big = tmp_path / "big.py"
    big.write_text("x = 1\n" * 100)

    from app.core.config import Settings

    settings = Settings(sqlite_path=str(tmp_path / "s.db"), max_index_file_size_bytes=50)
    import app.indexing.scanner as scanner_mod

    original = scanner_mod.get_settings
    scanner_mod.get_settings = lambda: settings  # type: ignore[assignment]
    try:
        repo = Repository(name="t", root_path=str(tmp_path))
        scanner = RepositoryScanner()
        result = scanner.scan(repo)
        paths = [f.path for f in result.files]
        assert "src/main.py" in paths
        assert all("node_modules" not in p for p in paths)
        assert "big.py" not in paths
        assert result.languages.get("python") == 1
    finally:
        scanner_mod.get_settings = original  # type: ignore[assignment]


def test_secret_detection_and_redaction() -> None:
    text = 'api_key = "sk-abcdefghijklmnopqrstuvwx"\npassword = "hunter2secret"\nnormal = 1\n'
    findings = find_secrets(text)
    assert len(findings) >= 1
    redacted = redact(text)
    assert "sk-abcdefghijklmnopqrstuvwx" not in redacted
    assert "[REDACTED_SECRET]" in redacted
    assert "normal = 1" in redacted


def test_redact_preserves_key_names() -> None:
    out = redact("API_KEY=sk-abcdefghijklmnopqrstuvwxyz123")
    assert out.startswith("API_KEY=")
    assert "[REDACTED_SECRET]" in out


def test_redact_output_stays_parseable() -> None:
    """Redaction must not corrupt source into unparseable text (the redacted
    text is what feeds AST extraction at ingestion time)."""
    import ast

    src = 'password = "hunter2secret"\n\ndef f():\n    return 1\n'
    out = redact(src)
    ast.parse(out)  # must not raise
    assert out.splitlines()[0] == 'password = "[REDACTED_SECRET]"'


def test_secrets_never_persist_raw_in_file_docs(tmp_path: Path) -> None:
    """SECURITY REGRESSION: raw secret values must never enter the persisted
    file_docs table. Redaction happens at ingestion, before storage."""
    from app.models.domain import Repository
    from app.services.indexer import index_repository
    from app.services.store import Store

    root = tmp_path / "secretrepo"
    root.mkdir()
    (root / "creds.py").write_text(
        'API_KEY = "sk-abcdefghijklmnopqrstuvwx0123"\n'
        'password = "hunter2secret"\n'
        "def use():\n"
        '    return API_KEY\n',
        encoding="utf-8",
    )
    (root / "clean.py").write_text("def clean():\n    return 2\n", encoding="utf-8")

    store = Store(db_path=str(tmp_path / "t.db"))
    repo = Repository(name="secretrepo", root_path=str(root))
    store.upsert_repository(repo)
    index_repository(repo, store)

    persisted = store.get_file_content(repo.id, "creds.py")
    assert persisted is not None, "creds.py should be persisted"
    # raw values absent
    assert "sk-abcdefghijklmnopqrstuvwx0123" not in persisted
    assert "hunter2secret" not in persisted
    # redacted representation present, key names preserved
    assert "[REDACTED_SECRET]" in persisted
    assert persisted.splitlines()[0] == 'API_KEY = "[REDACTED_SECRET]"'
    # structure preserved: symbols still extractable from redacted source
    names = {s.name for s in store.list_symbols(repo.id)}
    assert "use" in names
    # sha256 contract: FileEntry hash is computed by the scanner over the
    # ORIGINAL file content (read_text_safe round-trip), not over the
    # redacted text that is persisted — so file identity remains verifiable
    # against the on-disk source even after storage redaction.
    import hashlib

    from app.indexing.scanner import read_text_safe

    original = read_text_safe(root / "creds.py")
    expected_sha = hashlib.sha256(original.encode("utf-8", errors="replace")).hexdigest()
    entry = next(f for f in store.list_files(repo.id) if f.path == "creds.py")
    assert entry.sha256 == expected_sha
    # retrieval cannot recover the raw value either
    from app.services.rag_service import build_retriever

    retriever = build_retriever(store, repo.id)
    assert retriever is not None
    hit = retriever.contents.get("creds.py", "")
    assert "sk-abcdefghijklmnopqrstuvwx0123" not in hit
    assert "hunter2secret" not in hit
    assert "[REDACTED_SECRET]" in hit
