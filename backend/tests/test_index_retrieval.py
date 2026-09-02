"""Indexing, AST symbols, retrieval, and context engine tests."""
from __future__ import annotations

from app.retrieval.context_engine import ContextEngine, detect_query_intent


def test_index_extracts_symbols(indexed_repo, temp_store):
    symbols = temp_store.list_symbols(indexed_repo.id)
    names = {s.name for s in symbols}
    assert "TaskService" in names
    assert "TaskRepository" in names
    assert "complete_task" in names
    assert "validate_priority" in names


def test_index_relationships(indexed_repo, temp_store):
    rels = temp_store.list_relationships(indexed_repo.id)
    assert any(r.kind.value == "imports" for r in rels)
    assert any(r.kind.value == "contains" for r in rels)


def test_scan_stats(indexed_repo):
    stats = indexed_repo.scan_stats
    assert stats["total_files"] >= 5
    assert stats["source_files"] >= 4
    assert stats["test_files"] >= 1
    assert stats["symbols"] >= 10
    assert stats["languages"]["python"] >= 4


def test_retrieval_symbol_search(indexed_repo):
    from app.services.rag_service import get_retriever

    r = get_retriever(indexed_repo.id)
    assert r is not None
    result = r.search("TaskRepository", mode="symbol")
    sym_names = [s["name"] for s in result["symbol_results"]]
    assert "TaskRepository" in sym_names


def test_retrieval_lexical_search(indexed_repo):
    from app.services.rag_service import get_retriever

    r = get_retriever(indexed_repo.id)
    result = r.search("priority validation", mode="lexical")
    assert any("validators.py" in item["path"] for item in result["lexical_results"])


def test_retrieval_hybrid_ranking(indexed_repo):
    from app.services.rag_service import get_retriever

    r = get_retriever(indexed_repo.id)
    result = r.search("complete a todo task", mode="hybrid")
    paths = [f["path"] for f in result["ranked_files"]]
    assert "services/task_service.py" in paths[:3]


def test_query_intent_detection() -> None:
    assert detect_query_intent("Where is authentication?") == "locate"
    assert detect_query_intent("Explain the service layer") == "explain"
    assert detect_query_intent("Why does this test fail?") == "analyze"
    assert detect_query_intent("Plan adding OAuth") == "plan"


def test_context_engine_bounded(indexed_repo):
    from app.services.rag_service import get_retriever

    r = get_retriever(indexed_repo.id)
    engine = ContextEngine(r)
    ctx = engine.build_context("Where is task completion implemented?", max_tokens=2000)
    assert len(ctx["files"]) >= 1
    assert ctx["citations"], "context must include evidence citations"
    assert ctx["retrieval_stats"]["estimated_tokens"] <= 2600
    top_path = ctx["files"][0]["path"]
    assert top_path.endswith("task_service.py")


def test_context_engine_no_match(indexed_repo):
    from app.services.rag_service import get_retriever

    r = get_retriever(indexed_repo.id)
    engine = ContextEngine(r)
    ctx = engine.build_context("xyzzyplugh qwertyuiop frobnicate", max_tokens=1000)
    assert ctx["files"] == []
    assert ctx["citations"] == []
