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
