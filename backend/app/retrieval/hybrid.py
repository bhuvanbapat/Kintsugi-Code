"""Hybrid retrieval: lexical, structural (symbol), and metadata-filtered search.

Deliberately dependency-free (no external vector DB): lexical search runs over
SQLite FTS5 when available with a LIKE-based fallback; symbol search queries
the symbols table; ranking blends BM25-ish lexical score, symbol-name match,
and file importance heuristics. The goal is the smallest useful context.
"""
from __future__ import annotations

import math
import re
import sqlite3
from collections import Counter
from typing import Literal

from app.models.domain import FileEntry, Symbol

SearchMode = Literal["lexical", "symbol", "hybrid"]

_SYMBOL_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "where",
    "which", "what", "how", "why", "find", "show", "get", "set", "all",
    "new", "use", "used", "using", "one", "two", "may", "might", "should",
    "would", "could", "does", "did", "task", "tasks", "function", "class",
    "method", "module", "file", "files", "code", "test", "tests",
}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z_][A-Za-z0-9_]{1,}", text.lower())


class HybridRetriever:
    def __init__(self, files: list[FileEntry], symbols: list[Symbol],
                 contents: dict[str, str]) -> None:
        self.files = {f.path: f for f in files}
        self.symbols = symbols
        self.contents = contents
        self._symbol_by_name: dict[str, list[Symbol]] = {}
        for s in symbols:
            self._symbol_by_name.setdefault(s.name.lower(), []).append(s)
        self._df: Counter = Counter()
        self._doc_tokens: dict[str, list[str]] = {}
        self._doc_len: dict[str, int] = {}
        for path, content in contents.items():
            tokens = _tokenize(content)
            self._doc_tokens[path] = tokens
            self._doc_len[path] = len(tokens)
            for t in set(tokens):
                self._df[t] += 1
        self._avg_len = (sum(self._doc_len.values()) / len(self._doc_len)) if self._doc_len else 1.0
        self._total_docs = max(len(self._doc_len), 1)
        self._fts_ok = self._try_init_fts(contents)
    # -- FTS ----------------------------------------------------------------
    def _try_init_fts(self, contents: dict[str, str]) -> bool:
        """FTS5 available check — try creating an in-memory FTS index."""
        try:
            conn = sqlite3.connect(":memory:")
            conn.execute("CREATE VIRTUAL TABLE t USING fts5(path, content)")
            for path, content in contents.items():
                conn.execute("INSERT INTO t VALUES (?,?)", (path, content))
            self._fts = conn
            return True
        except sqlite3.OperationalError:
            self._fts = None
            return False

    def _fts_search(self, query: str, limit: int) -> list[tuple[str, float]]:
        if not self._fts_ok or not query.strip():
            return []
        tokens = _tokenize(query)
        fts_query = " OR ".join(f'"{t}"' for t in tokens)
        try:
            rows = self._fts.execute(
                "SELECT path, rank FROM t WHERE t MATCH ? ORDER BY rank LIMIT ?",
                (fts_query, limit),
            ).fetchall()
            # Lower rank (more negative) = better in FTS5.
            return [(r[0], -float(r[1]) if r[1] else 1.0) for r in rows]
        except sqlite3.OperationalError:
            return []

    # -- lexical BM25-ish -----------------------------------------------------
    def _lexical_scores(self, query: str, limit: int) -> dict[str, float]:
        scores: dict[str, float] = {}
        tokens = _tokenize(query)
        if not tokens:
            return scores
        k1, b = 1.5, 0.75
        for path, tokens_list in self._doc_tokens.items():
            tf = Counter(tokens_list)
            score = 0.0
            for t in tokens:
                f = tf.get(t, 0)
                if f == 0:
                    continue
                df = self._df.get(t, 0)
                if df == 0:
                    continue
                idf = math.log(1 + (self._total_docs - df + 0.5) / (df + 0.5))
                denom = f + k1 * (1 - b + b * (self._doc_len.get(path, self._avg_len) / self._avg_len))
                score += idf * (f * (k1 + 1)) / denom
            if score > 0:
                scores[path] = score
        return dict(sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:limit])

    def _symbol_scores(self, query: str, limit: int) -> list[tuple[Symbol, float]]:
        results: list[tuple[Symbol, float]] = []
        ql = query.lower().strip()
        if not ql:
            return results
        tokens = [t for t in _tokenize(query) if len(t) >= 3 and t not in _SYMBOL_STOPWORDS]
        # Rare tokens (appearing in few symbol names) are more informative.
        name_df: Counter = Counter()
        for sym in self.symbols:
            for t in set(_tokenize(sym.name)):
                name_df[t] += 1

        for sym in self.symbols:
            if sym.kind.value == "import":
                continue
            name_l = sym.name.lower()
            score = 0.0
            if ql == name_l:
                score += 50.0
            else:
                # Name appearing inside the query: scaled by name length so
                # short generic names ("Task") cannot dominate.
                if len(name_l) >= 5 and name_l in ql:
                    score += 25.0 * min(len(name_l) / 10.0, 1.0)
                for t in tokens:
                    stem = t.rstrip("s")
                    weight = 8.0 / (1.0 + name_df.get(t, 0) / 10.0)
                    if t == name_l:
                        score += weight * 2.0
                    elif t in name_l or (len(stem) >= 4 and stem in name_l):
                        score += weight
            if score > 0:
                if sym.kind.value in ("class", "function"):
                    score += 2.0
                results.append((sym, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def _file_importance(self, path: str) -> float:
        f = self.files.get(path)
        if f is None:
            return 0.0
        score = 0.0
        if f.is_manifest:
            score += 5.0
        if f.is_test:
            score -= 2.0
        lowered = path.lower()
        if any(k in lowered for k in ("readme", "main", "app", "index", "service", "api")):
            score += 1.5
        return score

    # -- public API ------------------------------------------------------------
    def search(self, query: str, mode: SearchMode = "hybrid", limit: int = 20,
               file_filter: str | None = None, kind_filter: list[str] | None = None,
               include_tests: bool = True) -> dict:
        """Return ranked retrieval result with lexical + symbol evidence."""
        out: dict = {
            "query": query,
            "mode": mode,
            "lexical_results": [],
            "symbol_results": [],
            "ranked_files": [],
        }
        if file_filter:
            pattern = re.compile(re.escape(file_filter).replace(r"\*", ".*"))
        else:
            pattern = None

        lexical: dict[str, float] = {}
        if mode in ("lexical", "hybrid"):
            if self._fts_ok:
                lexical = dict(self._fts_search(query, limit * 2))
                if not lexical:
                    lexical = self._lexical_scores(query, limit * 2)
            else:
                lexical = self._lexical_scores(query, limit * 2)

        symbols: list[tuple[Symbol, float]] = []
        if mode in ("symbol", "hybrid"):
            symbols = self._symbol_scores(query, limit)

        for path, score in lexical.items():
            if pattern and not pattern.search(path):
                continue
            f = self.files.get(path)
            if f is not None and f.is_test and not include_tests:
                continue
            out["lexical_results"].append({
                "path": path, "score": round(score, 3),
                "language": f.language if f else None,
            })

        seen_kinds = set()
        for sym, score in symbols:
            if kind_filter and sym.kind.value not in kind_filter:
                continue
            if pattern and not pattern.search(sym.file_path):
                continue
            key = (sym.file_path, sym.name, sym.kind)
            if key in seen_kinds:
                continue
            seen_kinds.add(key)
            out["symbol_results"].append({
                "id": sym.id, "name": sym.name, "kind": sym.kind.value,
                "file_path": sym.file_path, "start_line": sym.start_line,
                "end_line": sym.end_line, "score": round(score, 3),
                "parent": sym.parent, "signature": sym.signature,
            })

        # Ranked files: blend lexical score, symbol evidence, importance.
        file_scores: dict[str, float] = {}
        for item in out["lexical_results"]:
            file_scores[item["path"]] = file_scores.get(item["path"], 0) + item["score"]
        for item in out["symbol_results"]:
            bonus = min(item["score"] / 10.0, 5.0)
            file_scores[item["file_path"]] = file_scores.get(item["file_path"], 0) + bonus
        for path in file_scores:
            file_scores[path] += self._file_importance(path)
        ranked = sorted(file_scores.items(), key=lambda kv: kv[1], reverse=True)[:limit]
        out["ranked_files"] = [
            {"path": p, "score": round(s, 3), "language": self.files[p].language if p in self.files else None}
            for p, s in ranked
        ]
        return out
