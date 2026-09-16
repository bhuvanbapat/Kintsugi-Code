"""Language detection and file classification for repository scanning."""
from __future__ import annotations

from pathlib import PurePosixPath

LANGUAGE_BY_EXTENSION: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".rb": "ruby",
    ".php": "php",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".swift": "swift",
    ".scala": "scala",
    ".sh": "shell",
    ".bash": "shell",
    ".ps1": "powershell",
    ".sql": "sql",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".md": "markdown",
    ".txt": "text",
}

# Languages with structural (AST) support in Kintsugi-Code.
AST_LANGUAGES = {"python", "javascript", "typescript"}

TEST_PATH_MARKERS = ("test", "tests", "spec", "__tests__")
TEST_NAME_MARKERS = ("test_", "_test", "test.", ".test.", ".spec.", "_spec")
DOC_EXTENSIONS = {".md", ".rst", ".txt", ".adoc"}
CONFIG_EXTENSIONS = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env", ".editorconfig"}
MANIFEST_FILES = {
    "package.json", "pyproject.toml", "requirements.txt", "setup.py", "setup.cfg",
    "Cargo.toml", "go.mod", "pom.xml", "build.gradle", "build.gradle.kts",
    "Gemfile", "composer.json", "CMakeLists.txt", "Makefile",
}


def detect_language(path: str) -> str | None:
    ext = PurePosixPath(path).suffix.lower()
    return LANGUAGE_BY_EXTENSION.get(ext)


def is_test_file(path: str) -> bool:
    p = PurePosixPath(path).as_posix().lower()
    parts = p.split("/")
    name = parts[-1] if parts else p
    if any(marker in name for marker in TEST_NAME_MARKERS):
        return True
    return any(part in TEST_PATH_MARKERS for part in parts[:-1])


def is_doc_file(path: str) -> bool:
    return PurePosixPath(path).suffix.lower() in DOC_EXTENSIONS


def is_config_file(path: str) -> bool:
    return PurePosixPath(path).suffix.lower() in CONFIG_EXTENSIONS


def is_manifest_file(path: str) -> bool:
    return PurePosixPath(path).name.lower() in MANIFEST_FILES


def is_source_file(path: str, language: str | None) -> bool:
    if language is None:
        return False
    if is_test_file(path) or is_doc_file(path) or is_config_file(path):
        return False
    return language in {
        "python", "javascript", "typescript", "go", "rust", "java", "kotlin",
        "ruby", "php", "c", "cpp", "csharp", "swift", "scala", "shell",
    }


def resolve_module_path(module_name: str, file_set: set[str]) -> str | None:
    """Map a dotted module name (e.g. 'data.repositories') to a repo file.

    Shared by the repository map builder and the graph API so both resolve
    imports identically. Returns None when no file matches.
    """
    if module_name in file_set:
        return module_name
    as_path = module_name.replace(".", "/")
    for candidate in (
        f"{as_path}.py", f"{as_path}.ts", f"{as_path}.tsx", f"{as_path}.js",
        f"{as_path}/index.ts", f"{as_path}/index.js",
        f"src/{as_path}.py", f"src/{as_path}.ts",
    ):
        if candidate in file_set:
            return candidate
    for f in file_set:
        if f.replace("/", ".").endswith(module_name):
            return f
    return None

