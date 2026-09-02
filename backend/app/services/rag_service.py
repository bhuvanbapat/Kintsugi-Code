"""Service layer binding repositories to retrievers (process-level cache)."""
from __future__ import annotations

from app.retrieval.hybrid import HybridRetriever
from app.services.store import Store, get_store

_retrievers: dict[str, HybridRetriever] = {}


def build_retriever(store: Store, repo_id: str) -> HybridRetriever | None:
    repo = store.get_repository(repo_id)
    if repo is None:
        return None
    files = store.list_files(repo_id)
    symbols = store.list_symbols(repo_id)
    from app.indexing.secrets import redact

    contents: dict[str, str] = {}
    for f in files:
        if not (f.is_source or f.is_doc):
            continue
        content = store.get_file_content(repo_id, f.path)
        if content:
            contents[f.path] = redact(content)
    return HybridRetriever(files, symbols, contents)


def get_retriever(repo_id: str) -> HybridRetriever | None:
    if repo_id in _retrievers:
        return _retrievers[repo_id]
    retriever = build_retriever(get_store(), repo_id)
    if retriever is not None:
        _retrievers[repo_id] = retriever
    return retriever


def invalidate_retriever(repo_id: str) -> None:
    _retrievers.pop(repo_id, None)
