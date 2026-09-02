"""Domain models shared across the application."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class TimestampedModel(BaseModel):
    created_at: datetime = Field(default_factory=utcnow)


# ---------------------------------------------------------------------------
# Repository scanning / indexing
# ---------------------------------------------------------------------------


class RepositoryKind(str, Enum):
    LOCAL = "local"
    GIT_URL = "git_url"


class RepositoryStatus(str, Enum):
    REGISTERED = "registered"
    SCANNING = "scanning"
    INDEXED = "indexed"
    FAILED = "failed"


class Repository(TimestampedModel):
    id: str = Field(default_factory=lambda: new_id("repo"))
    name: str
    root_path: str
    kind: RepositoryKind = RepositoryKind.LOCAL
    status: RepositoryStatus = RepositoryStatus.REGISTERED
    scan_stats: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class FileEntry(BaseModel):
    path: str
    language: str | None = None
    size_bytes: int = 0
    line_count: int = 0
    is_test: bool = False
    is_doc: bool = False
    is_config: bool = False
    is_manifest: bool = False
    is_source: bool = False
    sha256: str = ""


class ScanResult(BaseModel):
    repository_id: str
    root_path: str
    total_files: int = 0
    source_files: int = 0
    test_files: int = 0
    doc_files: int = 0
    config_files: int = 0
    ignored_files: int = 0
    parse_errors: int = 0
    languages: dict[str, int] = Field(default_factory=dict)
    files: list[FileEntry] = Field(default_factory=list)
    duration_ms: int = 0


class SymbolKind(str, Enum):
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    IMPORT = "import"
    MODULE = "module"
    OTHER = "other"


class Symbol(BaseModel):
    id: str
    name: str
    kind: SymbolKind
    file_path: str
    start_line: int
    end_line: int
    parent: str | None = None
    language: str | None = None
    signature: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RelationshipKind(str, Enum):
    IMPORTS = "imports"
    CONTAINS = "contains"
    CALLS = "calls"


class Relationship(BaseModel):
    source: str
    target: str
    kind: RelationshipKind
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Conversations / agent runs
# ---------------------------------------------------------------------------


class AgentState(str, Enum):
    IDLE = "idle"
    ANALYZING = "analyzing"
    RETRIEVING = "retrieving"
    PLANNING = "planning"
    EXECUTING = "executing"
    TESTING = "testing"
    DIAGNOSING = "diagnosing"
    ITERATING = "iterating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskMode(str, Enum):
    EXPLAIN = "explain"
    LOCATE = "locate"
    ANALYZE = "analyze"
    PLAN = "plan"
    TEST = "test"
    FIX = "fix"
    REVIEW = "review"


class ExecutionMode(str, Enum):
    ANALYSIS_ONLY = "analysis_only"
    PLAN_ONLY = "plan_only"
    REVIEW_REQUIRED = "review_required"
    CONTROLLED_EXECUTION = "controlled_execution"


class Confidence(str, Enum):
    CONFIRMED = "confirmed_from_code"
    INFERRED = "inference"
    UNCERTAIN = "uncertain"


class EvidenceCitation(BaseModel):
    file_path: str
    start_line: int | None = None
    end_line: int | None = None
    symbol_id: str | None = None
    snippet: str | None = None
    confidence: Confidence = Confidence.CONFIRMED


class ToolCallRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("tc"))
    run_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result_summary: str | None = None
    error: str | None = None
    duration_ms: int = 0
    started_at: datetime = Field(default_factory=utcnow)


class AgentRun(TimestampedModel):
    id: str = Field(default_factory=lambda: new_id("run"))
    repository_id: str
    task: str
    mode: TaskMode = TaskMode.EXPLAIN
    execution_mode: ExecutionMode = ExecutionMode.ANALYSIS_ONLY
    state: AgentState = AgentState.IDLE
    iterations: int = 0
    max_iterations: int = 12
    status_message: str = ""
    result: str | None = None
    evidence: list[EvidenceCitation] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    finished_at: datetime | None = None
    usage: dict[str, Any] = Field(default_factory=dict)


class Message(BaseModel):
    id: str = Field(default_factory=lambda: new_id("msg"))
    role: Literal["user", "assistant", "system"]
    content: str
    evidence: list[EvidenceCitation] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)


class Conversation(TimestampedModel):
    id: str = Field(default_factory=lambda: new_id("conv"))
    repository_id: str
    title: str = "New conversation"
    messages: list[Message] = Field(default_factory=list)


class EvaluationCase(BaseModel):
    id: str
    category: Literal[
        "architecture", "symbol_location", "dependency_lookup",
        "bug_finding", "relevant_file", "planning", "test_diagnosis",
    ]
    question: str
    expected_files: list[str] = Field(default_factory=list)
    expected_symbols: list[str] = Field(default_factory=list)
    notes: str = ""


class EvaluationResult(BaseModel):
    case_id: str
    retrieved_files: list[str] = Field(default_factory=list)
    expected_files_hit: int = 0
    recall: float = 0.0
    precision: float = 0.0
    latency_ms: int = 0
    passed: bool = False

