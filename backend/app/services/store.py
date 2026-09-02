"""SQLite persistence layer for repositories, indexes, runs, and conversations.

A deliberately simple data-access layer over sqlite3 (no heavy ORM) — the
index itself lives in SQLite tables; conversation/run history is stored as
JSON documents for auditability.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.domain import (
    AgentRun,
    Conversation,
    FileEntry,
    Relationship,
    Repository,
    Symbol,
)

log = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS repositories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    root_path TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'local',
    status TEXT NOT NULL DEFAULT 'registered',
    scan_stats TEXT NOT NULL DEFAULT '{}',
    error TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS files (
    repository_id TEXT NOT NULL,
    path TEXT NOT NULL,
    language TEXT,
    size_bytes INTEGER NOT NULL DEFAULT 0,
    line_count INTEGER NOT NULL DEFAULT 0,
    is_test INTEGER NOT NULL DEFAULT 0,
    is_doc INTEGER NOT NULL DEFAULT 0,
    is_config INTEGER NOT NULL DEFAULT 0,
    is_manifest INTEGER NOT NULL DEFAULT 0,
    is_source INTEGER NOT NULL DEFAULT 0,
    sha256 TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (repository_id, path)
);
CREATE INDEX IF NOT EXISTS idx_files_repo ON files(repository_id);
CREATE TABLE IF NOT EXISTS symbols (
    id TEXT NOT NULL,
    repository_id TEXT NOT NULL,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    file_path TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    parent TEXT,
    language TEXT,
    signature TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (repository_id, id)
);
CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(repository_id, name);
CREATE INDEX IF NOT EXISTS idx_symbols_file ON symbols(repository_id, file_path);
CREATE TABLE IF NOT EXISTS relationships (
    repository_id TEXT NOT NULL,
    source TEXT NOT NULL,
    target TEXT NOT NULL,
    kind TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (repository_id, source, target, kind)
);
CREATE INDEX IF NOT EXISTS idx_rel_source ON relationships(repository_id, source);
CREATE INDEX IF NOT EXISTS idx_rel_target ON relationships(repository_id, target);
CREATE TABLE IF NOT EXISTS file_docs (
    repository_id TEXT NOT NULL,
    path TEXT NOT NULL,
    content TEXT NOT NULL,
    PRIMARY KEY (repository_id, path)
);
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    repository_id TEXT NOT NULL,
    task TEXT NOT NULL,
    mode TEXT NOT NULL,
    execution_mode TEXT NOT NULL,
    state TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    repository_id TEXT NOT NULL,
    title TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS kv (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class Store:
    """Thread-local SQLite store. All project data lives in one DB file."""

    def __init__(self, db_path: str | None = None) -> None:
        path = db_path or get_settings().sqlite_path
        self.db_path = str(Path(path).resolve())
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_schema()

    @property
    def conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return conn

    def _init_schema(self) -> None:
        conn = self.conn
        conn.executescript(_SCHEMA)
        conn.commit()

    # -- repositories ------------------------------------------------------
    def upsert_repository(self, repo: Repository) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO repositories VALUES (?,?,?,?,?,?,?,?)",
            (repo.id, repo.name, repo.root_path, repo.kind.value, repo.status.value,
             json.dumps(repo.scan_stats), repo.error, repo.created_at.isoformat()),
        )
        self.conn.commit()

    def get_repository(self, repo_id: str) -> Repository | None:
        row = self.conn.execute("SELECT * FROM repositories WHERE id=?", (repo_id,)).fetchone()
        if not row:
            return None
        return Repository(
            id=row["id"], name=row["name"], root_path=row["root_path"],
            kind=row["kind"], status=row["status"],
            scan_stats=json.loads(row["scan_stats"]), error=row["error"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def list_repositories(self) -> list[Repository]:
        rows = self.conn.execute("SELECT * FROM repositories ORDER BY created_at DESC").fetchall()
        out = []
        for row in rows:
            out.append(Repository(
                id=row["id"], name=row["name"], root_path=row["root_path"],
                kind=row["kind"], status=row["status"],
                scan_stats=json.loads(row["scan_stats"]), error=row["error"],
                created_at=datetime.fromisoformat(row["created_at"]),
            ))
        return out

    def delete_repository(self, repo_id: str) -> None:
        for table in ("files", "symbols", "relationships", "file_docs"):
            self.conn.execute(f"DELETE FROM {table} WHERE repository_id=?", (repo_id,))
        self.conn.execute("DELETE FROM repositories WHERE id=?", (repo_id,))
        self.conn.commit()

    # -- scan / index ------------------------------------------------------
    def replace_files(self, repo_id: str, files: list[FileEntry]) -> None:
        conn = self.conn
        conn.execute("DELETE FROM files WHERE repository_id=?", (repo_id,))
        conn.executemany(
            "INSERT OR REPLACE INTO files VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [(repo_id, f.path, f.language, f.size_bytes, f.line_count, int(f.is_test),
              int(f.is_doc), int(f.is_config), int(f.is_manifest), int(f.is_source), f.sha256)
             for f in files],
        )
        conn.commit()

    def replace_symbols(self, repo_id: str, symbols: list[Symbol]) -> None:
        conn = self.conn
        conn.execute("DELETE FROM symbols WHERE repository_id=?", (repo_id,))
        conn.executemany(
            "INSERT OR REPLACE INTO symbols VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [(s.id, repo_id, s.name, s.kind.value, s.file_path, s.start_line, s.end_line,
              s.parent, s.language, s.signature, json.dumps(s.metadata, default=str))
             for s in symbols],
        )
        conn.commit()

    def replace_relationships(self, repo_id: str, rels: list[Relationship]) -> None:
        conn = self.conn
        conn.execute("DELETE FROM relationships WHERE repository_id=?", (repo_id,))
        conn.executemany(
            "INSERT OR REPLACE INTO relationships VALUES (?,?,?,?,?)",
            [(repo_id, r.source, r.target, r.kind.value, json.dumps(r.metadata, default=str)) for r in rels],
        )
        conn.commit()

    def store_file_contents(self, repo_id: str, items: list[tuple[str, str]]) -> None:
        self.conn.executemany(
            "INSERT OR REPLACE INTO file_docs VALUES (?,?,?)",
            [(repo_id, p, c) for p, c in items],
        )
        self.conn.commit()

    def get_file_content(self, repo_id: str, path: str) -> str | None:
        row = self.conn.execute(
            "SELECT content FROM file_docs WHERE repository_id=? AND path=?", (repo_id, path)
        ).fetchone()
        return row["content"] if row else None

    def list_files(self, repo_id: str) -> list[FileEntry]:
        rows = self.conn.execute("SELECT * FROM files WHERE repository_id=?", (repo_id,)).fetchall()
        return [FileEntry(
            path=r["path"], language=r["language"], size_bytes=r["size_bytes"],
            line_count=r["line_count"], is_test=bool(r["is_test"]), is_doc=bool(r["is_doc"]),
            is_config=bool(r["is_config"]), is_manifest=bool(r["is_manifest"]),
            is_source=bool(r["is_source"]), sha256=r["sha256"],
        ) for r in rows]

    def list_symbols(self, repo_id: str) -> list[Symbol]:
        from app.models.domain import SymbolKind

        rows = self.conn.execute("SELECT * FROM symbols WHERE repository_id=?", (repo_id,)).fetchall()
        return [Symbol(
            id=r["id"], name=r["name"], kind=SymbolKind(r["kind"]), file_path=r["file_path"],
            start_line=r["start_line"], end_line=r["end_line"], parent=r["parent"],
            language=r["language"], signature=r["signature"],
            metadata=json.loads(r["metadata_json"] or "{}"),
        ) for r in rows]

    def list_relationships(self, repo_id: str) -> list[Relationship]:
        from app.models.domain import RelationshipKind

        rows = self.conn.execute("SELECT * FROM relationships WHERE repository_id=?", (repo_id,)).fetchall()
        return [Relationship(
            source=r["source"], target=r["target"], kind=RelationshipKind(r["kind"]),
            metadata=json.loads(r["metadata_json"] or "{}"),
        ) for r in rows]

    # -- runs / conversations ----------------------------------------------
    def save_run(self, run: AgentRun) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?,?,?)",
            (run.id, run.repository_id, run.task, run.mode.value,
             run.execution_mode.value, run.state.value, run.model_dump_json(), run.created_at.isoformat()),
        )
        self.conn.commit()

    def get_run(self, run_id: str) -> AgentRun | None:
        row = self.conn.execute("SELECT payload FROM runs WHERE id=?", (run_id,)).fetchone()
        return AgentRun.model_validate_json(row["payload"]) if row else None

    def list_runs(self, repo_id: str | None = None, limit: int = 50) -> list[AgentRun]:
        if repo_id:
            rows = self.conn.execute(
                "SELECT payload FROM runs WHERE repository_id=? ORDER BY created_at DESC LIMIT ?",
                (repo_id, limit)).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT payload FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [AgentRun.model_validate_json(r["payload"]) for r in rows]

    def save_conversation(self, conv: Conversation) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO conversations VALUES (?,?,?,?,?)",
            (conv.id, conv.repository_id, conv.title, conv.model_dump_json(),
             conv.created_at.isoformat()),
        )
        self.conn.commit()

    def get_conversation(self, conv_id: str) -> Conversation | None:
        row = self.conn.execute("SELECT payload FROM conversations WHERE id=?", (conv_id,)).fetchone()
        return Conversation.model_validate_json(row["payload"]) if row else None

    def list_conversations(self, repo_id: str | None = None, limit: int = 50) -> list[Conversation]:
        if repo_id:
            rows = self.conn.execute(
                "SELECT payload FROM conversations WHERE repository_id=? ORDER BY created_at DESC LIMIT ?",
                (repo_id, limit)).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT payload FROM conversations ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [Conversation.model_validate_json(r["payload"]) for r in rows]

    # -- kv ------------------------------------------------------------------
    def kv_get(self, key: str) -> Any | None:
        row = self.conn.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
        return json.loads(row["value"]) if row else None

    def kv_set(self, key: str, value: Any) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO kv VALUES (?,?)", (key, json.dumps(value))
        )
        self.conn.commit()

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None


_store: Store | None = None


def get_store() -> Store:
    global _store
    if _store is None:
        _store = Store()
    return _store
