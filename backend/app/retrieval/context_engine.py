"""Context engine: turn a user query into a bounded, evidence-rich LLM context.

USER QUERY -> understanding -> candidate retrieval -> structural expansion ->
relevance ranking -> context budget -> LLM-ready context with provenance.
"""
from __future__ import annotations

import re

from app.core.config import get_settings
from app.models.domain import Confidence, EvidenceCitation
from app.retrieval.hybrid import HybridRetriever

# Rough token estimate: ~4 chars per token for code.
CHARS_PER_TOKEN = 4

LOCATE_WORDS = ("where", "find", "locate", "which file", "show me")
EXPLAIN_WORDS = ("explain", "how does", "what is", "describe", "walk through", "overview")
ANALYZE_WORDS = ("why", "analyze", "fail", "broken", "bug", "error", "diagnose")
PLAN_WORDS = ("plan", "implement", "add", "refactor", "how should", "design")


def detect_query_intent(query: str) -> str:
    q = query.lower()
    if any(w in q for w in LOCATE_WORDS):
        return "locate"
    if any(w in q for w in ANALYZE_WORDS):
        return "analyze"
    if any(w in q for w in PLAN_WORDS):
        return "plan"
    if any(w in q for w in EXPLAIN_WORDS):
        return "explain"
    return "explain"


def _relevant_line_window(content: str, query: str, radius: int = 12) -> tuple[int, int, str]:
    """Find the best line window matching the query inside file content."""
    lines = content.splitlines()
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", query.lower())
    best_line, best_score = 1, -1.0
    for i, line in enumerate(lines):
        line_l = line.lower()
        score = sum(1.0 for t in tokens if t in line_l)
        if "def " in line or "class " in line or "function" in line:
            score += 0.5
        if score > best_score:
            best_score, best_line = score, i + 1
    start = max(1, best_line - radius)
    end = min(len(lines), best_line + radius)
    snippet = "\n".join(lines[start - 1:end])
    return start, end, snippet


class ContextEngine:
    def __init__(self, retriever: HybridRetriever) -> None:
        self.retriever = retriever
        self.settings = get_settings()

    def build_context(self, query: str, max_tokens: int | None = None) -> dict:
        budget = max_tokens or self.settings.context_budget_tokens
        intent = detect_query_intent(query)
        retrieval = self.retriever.search(query, mode="hybrid", limit=self.settings.retrieval_max_candidates)

        citations: list[EvidenceCitation] = []
        included_files: list[dict] = []
        char_budget = budget * CHARS_PER_TOKEN
        used = 0
        header_overhead = 120 * len(retrieval["ranked_files"]) // 10
        used += header_overhead

        # Structural expansion: for top symbol hits, include the defining file.
        symbol_files = {s["file_path"] for s in retrieval["symbol_results"][:8]}

        for ranked in retrieval["ranked_files"]:
            if used >= char_budget:
                break
            path = ranked["path"]
            content = self.retriever.contents.get(path)
            if content is None:
                continue
            if path in symbol_files:
                start, end, snippet = (1, min(self.retriever.files[path].line_count or 9999, 60),
                                        content[:4000])
            else:
                start, end, snippet = _relevant_line_window(content, query)
            # Trim snippet if budget is tight.
            remaining = char_budget - used
            if len(snippet) > remaining:
                snippet = snippet[:remaining]
                end = start + snippet.count("\n")
            included_files.append({
                "path": path,
                "start_line": start,
                "end_line": end,
                "snippet": snippet,
            })
            citations.append(EvidenceCitation(
                file_path=path, start_line=start, end_line=end,
                confidence=Confidence.CONFIRMED,
            ))
            used += len(snippet) + 60

        return {
            "query": query,
            "intent": intent,
            "citations": [c.model_dump() for c in citations],
            "files": included_files,
            "retrieval_stats": {
                "lexical_hits": len(retrieval["lexical_results"]),
                "symbol_hits": len(retrieval["symbol_results"]),
                "files_included": len(included_files),
                "estimated_tokens": used // CHARS_PER_TOKEN,
            },
        }
