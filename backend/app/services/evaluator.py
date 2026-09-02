"""Evaluation subsystem: benchmark retrieval quality against known answers.

Measures real retrieval hit rate / recall / precision / latency on curated
cases for the sample repository. Metrics are computed from actual retriever
output — nothing is fabricated.
"""
from __future__ import annotations

import time

from app.models.domain import EvaluationCase, EvaluationResult
from app.services.rag_service import get_retriever
from app.services.store import Store


def get_benchmark() -> list[EvaluationCase]:
    """Curated benchmark against examples/sample_repo."""
    return [
        EvaluationCase(
            id="arch-1", category="architecture",
            question="Explain the repository layering: services, data, API.",
            expected_files=["api/routes.py", "services/task_service.py", "data/repositories.py"],
            notes="Architecture question must surface all three layers.",
        ),
        EvaluationCase(
            id="sym-1", category="symbol_location",
            question="Where is the TaskRepository class defined?",
            expected_files=["data/repositories.py"],
            expected_symbols=["TaskRepository"],
        ),
        EvaluationCase(
            id="sym-2", category="symbol_location",
            question="Find the function that validates task priority.",
            expected_files=["services/validators.py"],
            expected_symbols=["validate_priority"],
        ),
        EvaluationCase(
            id="dep-1", category="dependency_lookup",
            question="Which module does the API import from the service layer?",
            expected_files=["api/routes.py", "services/task_service.py"],
        ),
        EvaluationCase(
            id="bug-1", category="bug_finding",
            question="Why might complete_task fail for tasks with status todo?",
            expected_files=["services/task_service.py", "tests/test_task_service.py"],
        ),
        EvaluationCase(
            id="file-1", category="relevant_file",
            question="Show the persistence layer for tasks.",
            expected_files=["data/repositories.py"],
        ),
        EvaluationCase(
            id="plan-1", category="planning",
            question="Plan adding a due-date filter to task listing.",
            expected_files=["api/routes.py", "services/task_service.py", "data/repositories.py"],
        ),
        EvaluationCase(
            id="testdiag-1", category="test_diagnosis",
            question="Diagnose the failing test about completing todo tasks.",
            expected_files=["tests/test_task_service.py", "services/task_service.py"],
        ),
    ]


def run_evaluation_for_repo(repo_id: str, store: Store) -> dict:
    retriever = get_retriever(repo_id)
    if retriever is None:
        return {"ok": False, "error": "repository not indexed"}
    cases = get_benchmark()
    results: list[EvaluationResult] = []
    for case in cases:
        start = time.monotonic()
        retrieval = retriever.search(case.question, mode="hybrid", limit=10)
        latency_ms = int((time.monotonic() - start) * 1000)
        retrieved_files = [r["path"] for r in retrieval.get("ranked_files", [])]
        hits = [f for f in case.expected_files if f in retrieved_files]
        recall = len(hits) / len(case.expected_files) if case.expected_files else 1.0
        precision = len(hits) / len(retrieved_files) if retrieved_files else 0.0
        symbol_hit = False
        if case.expected_symbols:
            found_names = {s["name"] for s in retrieval.get("symbol_results", [])}
            symbol_hit = all(s in found_names for s in case.expected_symbols)
        passed = recall >= 0.5 and (not case.expected_symbols or symbol_hit)
        results.append(EvaluationResult(
            case_id=case.id, retrieved_files=retrieved_files,
            expected_files_hit=len(hits), recall=round(recall, 3),
            precision=round(precision, 3), latency_ms=latency_ms, passed=passed,
        ))
    n = len(results)
    summary = {
        "ok": True,
        "cases": [r.model_dump() for r in results],
        "summary": {
            "total_cases": n,
            "passed": sum(r.passed for r in results),
            "mean_recall": round(sum(r.recall for r in results) / n, 3) if n else 0,
            "mean_precision": round(sum(r.precision for r in results) / n, 3) if n else 0,
            "mean_latency_ms": round(sum(r.latency_ms for r in results) / n, 1) if n else 0,
        },
    }
    store.kv_set(f"evaluation:{repo_id}", summary)
    return summary
