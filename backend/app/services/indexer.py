"""Indexing orchestrator: scan -> classify -> extract symbols -> persist."""
from __future__ import annotations

from app.core.logging import get_logger
from app.indexing.ast_parser import extract_symbols
from app.indexing.language import AST_LANGUAGES, resolve_module_path
from app.indexing.scanner import (
    RepositoryScanner,
    normalize_repo_path,
    read_text_safe,
)
from app.indexing.secrets import find_secrets, redact
from app.models.domain import (
    Relationship,
    Repository,
    RepositoryStatus,
    ScanResult,
    Symbol,
)
from app.services.store import Store

log = get_logger(__name__)

# Languages we can parse structurally with tree-sitter.
_TS_PARSEABLE = AST_LANGUAGES


def index_repository(repo: Repository, store: Store, extra_ignores: list[str] | None = None) -> ScanResult:
    """Full pipeline: scan, parse, extract symbols, store index.

    Partial failures (individual file parse errors) never abort indexing.
    """
    repo.status = RepositoryStatus.SCANNING
    repo.error = None
    store.upsert_repository(repo)

    scanner = RepositoryScanner(extra_ignores=extra_ignores)
    scan = scanner.scan(repo)

    symbols: list[Symbol] = []
    relationships: list[Relationship] = []
    contents: list[tuple[str, str]] = []
    parse_errors = 0
    secret_hits = 0

    root = normalize_repo_path(repo.root_path)
    for entry in scan.files:
        if not entry.is_source and not entry.is_doc:
            continue
        full = root / entry.path
        text = read_text_safe(full)
        if not text:
            continue
        if find_secrets(text):
            secret_hits += 1
        # Redact BEFORE any persistence: raw secret values must never enter
        # the file_docs table (the retriever and every downstream consumer
        # read from storage). Redaction preserves line structure, so symbol
        # line numbers stay correct. sha256 in FileEntry is computed by the
        # scanner over the ORIGINAL bytes and is unchanged by this.
        text = redact(text)
        if entry.language in _TS_PARSEABLE and entry.is_source:
            try:
                file_syms, file_rels = extract_symbols(entry.path, text, entry.language)
                symbols.extend(file_syms)
                relationships.extend(file_rels)
            except Exception as exc:  # noqa: BLE001
                parse_errors += 1
                log.debug("extract failure %s: %s", entry.path, exc)
        if len(text) <= 500_000:
            contents.append((entry.path, text))

    store.replace_files(repo.id, scan.files)
    store.replace_symbols(repo.id, symbols)
    store.replace_relationships(repo.id, relationships)
    store.store_file_contents(repo.id, contents)

    scan.parse_errors = parse_errors
    scan.duration_ms = scan.duration_ms  # scanner timing; extraction tracked below
    repo.status = RepositoryStatus.INDEXED
    repo.scan_stats = {
        "total_files": scan.total_files,
        "source_files": scan.source_files,
        "test_files": scan.test_files,
        "doc_files": scan.doc_files,
        "config_files": scan.config_files,
        "ignored_files": scan.ignored_files,
        "parse_errors": parse_errors,
        "symbols": len(symbols),
        "relationships": len(relationships),
        "languages": scan.languages,
        "secret_flagged_files": secret_hits,
    }
    store.upsert_repository(repo)
    log.info("Indexed %s: %d symbols, %d relationships", repo.name, len(symbols), len(relationships))
    return scan


def build_repository_map(store: Store, repo_id: str) -> dict:
    """Produce a compact structural map used for LLM context and the graph view."""
    files = store.list_files(repo_id)
    symbols = store.list_symbols(repo_id)
    relationships = store.list_relationships(repo_id)

    files_by_path: dict[str, dict] = {}
    for f in files:
        if not f.is_source:
            continue
        files_by_path[f.path] = {"path": f.path, "language": f.language, "symbols": []}

    for s in symbols:
        if s.kind.value in ("function", "class", "method"):
            entry = files_by_path.get(s.file_path)
            if entry is not None:
                entry["symbols"].append({
                    "name": s.name, "kind": s.kind.value,
                    "start_line": s.start_line, "end_line": s.end_line,
                })

    # Import edges file -> file (module symbols resolve to repo files).
    symbol_index = {s.id: s for s in symbols}
    source_file_set = {f.path for f in files if f.is_source}
    import_edges: set[tuple[str, str]] = set()
    for rel in relationships:
        if rel.kind.value != "imports":
            continue
        src = symbol_index.get(rel.source)
        if src is None:
            continue
        tgt = symbol_index.get(rel.target)
        module_name = None
        if tgt is not None and tgt.kind.value == "module":
            module_name = tgt.name.removeprefix("module:")
        if module_name is None:
            continue
        resolved = resolve_module_path(module_name, source_file_set)
        if resolved and resolved != src.file_path:
            import_edges.add((src.file_path, resolved))

    return {
        "files": list(files_by_path.values()),
        "import_edges": [
            {"from": a, "to": b} for a, b in sorted(import_edges)
        ][:500],
        "symbol_count": len(symbols),
        "file_count": len(files_by_path),
    }
