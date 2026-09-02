"""FastAPI application — all API routes for CodeForge."""
from __future__ import annotations

import asyncio
import difflib
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.logging import get_logger
from app.indexing.language import resolve_module_path
from app.models.domain import (
    Conversation,
    ExecutionMode,
    Message,
    Repository,
    RepositoryKind,
    RepositoryStatus,
    TaskMode,
)
from app.services.indexer import index_repository
from app.services.rag_service import get_retriever, invalidate_retriever
from app.services.store import get_store

log = get_logger(__name__)

app = FastAPI(
    title="CodeForge API",
    version=get_settings().app_version,
    description="AI software engineering workspace — repository-aware, evidence-backed.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# request / response models
# ---------------------------------------------------------------------------

class ImportRepoRequest(BaseModel):
    path: str
    name: str | None = None
    extra_ignores: list[str] = Field(default_factory=list)


class ScanRequest(BaseModel):
    repository_id: str
    extra_ignores: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    repository_id: str
    message: str
    conversation_id: str | None = None
    mode: TaskMode = TaskMode.EXPLAIN
    execution_mode: ExecutionMode = ExecutionMode.ANALYSIS_ONLY


class SearchRequest(BaseModel):
    repository_id: str
    query: str
    mode: Literal["lexical", "symbol", "hybrid"] = "hybrid"
    limit: int = 20
    file_filter: str | None = None
    kind_filter: list[str] | None = None


class SettingsUpdate(BaseModel):
    llm_provider: Literal["openai", "mock"] | None = None
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None
    context_budget_tokens: int | None = None
    agent_max_iterations: int | None = None


class ApplyPatchRequest(BaseModel):
    repository_id: str
    path: str
    content: str
    mode: Literal["full", "append"] = "full"
    run_tests_after: bool = False


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _require_repo(repo_id: str) -> Repository:
    repo = get_store().get_repository(repo_id)
    if repo is None:
        raise HTTPException(404, f"repository not found: {repo_id}")
    return repo


def _run_in_thread(fn, *args):
    """Run blocking indexing in a worker thread."""
    return asyncio.get_running_loop().run_in_executor(None, fn, *args)


# ---------------------------------------------------------------------------
# health / meta
# ---------------------------------------------------------------------------


@app.get("/api/health")
async def health() -> dict[str, Any]:
    s = get_settings()
    return {
        "status": "ok",
        "app": s.app_name,
        "version": s.app_version,
        "provider": s.llm_provider,
        "model": s.llm_model if s.llm_provider == "openai" else "mock-offline",
    }


@app.get("/api/settings")
async def read_settings() -> dict[str, Any]:
    s = get_settings()
    return {
        "llm_provider": s.llm_provider,
        "llm_base_url": s.llm_base_url,
        "llm_model": s.llm_model,
        "llm_api_key_set": bool(s.llm_api_key),
        "context_budget_tokens": s.context_budget_tokens,
        "agent_max_iterations": s.agent_max_iterations,
        "environment": s.environment,
    }


@app.post("/api/settings")
async def update_settings(body: SettingsUpdate) -> dict[str, Any]:
    import app.core.config as cfg

    s = cfg.get_settings()
    changed = []
    for field_name, value in body.model_dump(exclude_none=True).items():
        if field_name == "llm_api_key" and not value:
            continue
        setattr(s, field_name, value)
        changed.append(field_name)
    # persist to kv store for restarts
    get_store().kv_set("runtime_settings", {
        k: v for k, v in body.model_dump(exclude_none=True).items() if k != "llm_api_key"
    })
    from app.llm.providers import reset_provider

    reset_provider()
    return {"ok": True, "changed": changed}


# ---------------------------------------------------------------------------
# repositories
# ---------------------------------------------------------------------------


@app.post("/api/repositories/import")
async def import_repository(body: ImportRepoRequest) -> dict[str, Any]:
    store = get_store()
    from app.indexing.scanner import normalize_repo_path

    try:
        root = normalize_repo_path(body.path)
    except (FileNotFoundError, NotADirectoryError) as e:
        raise HTTPException(400, str(e))
    name = body.name or root.name
    repo = Repository(name=name, root_path=str(root), kind=RepositoryKind.LOCAL)
    store.upsert_repository(repo)
    return {"ok": True, "repository": repo.model_dump()}


@app.get("/api/repositories")
async def list_repositories() -> dict[str, Any]:
    repos = get_store().list_repositories()
    return {"repositories": [r.model_dump() for r in repos]}


@app.get("/api/repositories/{repo_id}")
async def get_repository(repo_id: str) -> dict[str, Any]:
    return {"repository": _require_repo(repo_id).model_dump()}


@app.delete("/api/repositories/{repo_id}")
async def delete_repository(repo_id: str) -> dict[str, Any]:
    _require_repo(repo_id)
    get_store().delete_repository(repo_id)
    invalidate_retriever(repo_id)
    return {"ok": True}


@app.post("/api/index")
async def index(body: ScanRequest) -> dict[str, Any]:
    repo = _require_repo(body.repository_id)
    try:
        scan = await _run_in_thread(index_repository, repo, get_store(), body.extra_ignores)
    except Exception as e:  # noqa: BLE001
        repo.status = RepositoryStatus.FAILED
        repo.error = str(e)
        get_store().upsert_repository(repo)
        raise HTTPException(500, f"indexing failed: {e}")
    invalidate_retriever(repo.id)
    return {
        "ok": True,
        "scan": scan.model_dump(),
        "repository": repo.model_dump(),
    }


# ---------------------------------------------------------------------------
# files / search / symbols / graph
# ---------------------------------------------------------------------------


@app.get("/api/repositories/{repo_id}/files")
async def list_files(repo_id: str, pattern: str | None = None, limit: int = 500) -> dict[str, Any]:
    _require_repo(repo_id)
    files = get_store().list_files(repo_id)
    if pattern:
        import re as _re

        rx = _re.compile(_re.escape(pattern).replace(r"\*", ".*"))
        files = [f for f in files if rx.search(f.path)]
    return {"files": [f.model_dump() for f in files[:limit]], "total": len(files)}


@app.get("/api/repositories/{repo_id}/file")
async def get_file(repo_id: str, path: str) -> dict[str, Any]:
    _require_repo(repo_id)
    repo_root = Path(_require_repo(repo_id).root_path)
    target = (repo_root / path).resolve()
    try:
        target.relative_to(repo_root.resolve())
    except ValueError:
        raise HTTPException(400, f"path escapes repository root: {path}")
    if not target.exists():
        raise HTTPException(404, f"file not found: {path}")
    if target.stat().st_size > get_settings().max_index_file_size_bytes:
        raise HTTPException(413, "file too large to serve")
    data = target.read_bytes()
    if b"\x00" in data[:4096]:
        return {"path": path, "content": "", "binary": True}
    from app.indexing.secrets import redact

    content = redact(data.decode("utf-8", errors="replace"))
    lines = content.splitlines()
    return {"path": path, "content": content, "total_lines": len(lines)}


@app.post("/api/search")
async def search(body: SearchRequest) -> dict[str, Any]:
    _require_repo(body.repository_id)
    retriever = get_retriever(body.repository_id)
    if retriever is None:
        raise HTTPException(409, "repository not indexed")
    return retriever.search(
        body.query, mode=body.mode, limit=body.limit,
        file_filter=body.file_filter, kind_filter=body.kind_filter,
    )


@app.get("/api/symbols")
async def symbols(repo_id: str, query: str | None = None, kind: str | None = None,
                  limit: int = 200) -> dict[str, Any]:
    _require_repo(repo_id)
    syms = get_store().list_symbols(repo_id)
    if query:
        ql = query.lower()
        syms = [s for s in syms if ql in s.name.lower()]
    if kind:
        syms = [s for s in syms if s.kind.value == kind]
    return {"symbols": [s.model_dump() for s in syms[:limit]], "total": len(syms)}


@app.get("/api/graph")
async def graph(repo_id: str, kind: Literal["files", "symbols"] = "files") -> dict[str, Any]:
    _require_repo(repo_id)
    store = get_store()
    files = store.list_files(repo_id)
    symbols = store.list_symbols(repo_id)
    rels = store.list_relationships(repo_id)
    sym_by_id = {s.id: s for s in symbols}

    if kind == "files":
        nodes = [{"id": f.path, "label": f.path.split("/")[-1], "type": "file",
                  "language": f.language, "is_test": f.is_test}
                 for f in files if f.is_source]
        file_set = {f.path for f in files if f.is_source}
        edges = []
        seen = set()
        for r in rels:
            if r.kind.value != "imports":
                continue
            src = sym_by_id.get(r.source)
            if not src:
                continue
            tgt = sym_by_id.get(r.target)
            if tgt is None or tgt.kind.value != "module":
                continue
            module_name = tgt.name.removeprefix("module:")
            target_file = resolve_module_path(module_name, file_set)
            if target_file and target_file != src.file_path:
                key = (src.file_path, target_file)
                if key not in seen:
                    seen.add(key)
                    edges.append({"source": src.file_path, "target": target_file, "kind": "imports"})
        return {"nodes": nodes, "edges": edges}

    # symbols graph
    nodes = [{"id": s.id, "label": s.name, "type": s.kind.value,
              "file": s.file_path, "line": s.start_line}
             for s in symbols if s.kind.value in ("class", "function", "method")]
    edges = [{"source": r.source, "target": r.target, "kind": r.kind.value}
             for r in rels if r.kind.value in ("contains", "imports")]
# ---------------------------------------------------------------------------
# chat / agent
# ---------------------------------------------------------------------------


@app.post("/api/chat")
async def chat(body: ChatRequest) -> dict[str, Any]:
    repo = _require_repo(body.repository_id)
    store = get_store()
    conv = None
    if body.conversation_id:
        conv = store.get_conversation(body.conversation_id)
    if conv is None:
        conv = Conversation(repository_id=repo.id, title=body.message[:60])
    conv.messages.append(Message(role="user", content=body.message))

    from app.agent.engine import Agent

    agent = Agent(store)
    run = await agent.run(
        repository_id=repo.id, task=body.message, mode=body.mode,
        execution_mode=body.execution_mode,
    )
    reply = Message(
        role="assistant", content=run.result or "no result",
        evidence=run.evidence,
    )
    conv.messages.append(reply)
    store.save_conversation(conv)
    return {
        "conversation_id": conv.id,
        "message": reply.model_dump(),
        "run": run.model_dump(),
    }


@app.get("/api/agent/runs")
async def list_runs(repo_id: str | None = None, limit: int = 50) -> dict[str, Any]:
    runs = get_store().list_runs(repo_id, limit)
    return {"runs": [r.model_dump() for r in runs]}


@app.get("/api/agent/runs/{run_id}")
async def get_run(run_id: str) -> dict[str, Any]:
    run = get_store().get_run(run_id)
    if run is None:
        raise HTTPException(404, f"run not found: {run_id}")
    return {"run": run.model_dump()}


# ---------------------------------------------------------------------------
# tools
# ---------------------------------------------------------------------------


@app.get("/api/tools")
async def list_tools() -> dict[str, Any]:
    from app.tools.registry import build_default_registry

    return {"tools": build_default_registry().list_tools()}


class ToolExecRequest(BaseModel):
    repository_id: str
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)


@app.post("/api/tools/execute")
async def execute_tool(body: ToolExecRequest) -> dict[str, Any]:
    repo = _require_repo(body.repository_id)
    from app.tools.registry import ToolContext, build_default_registry

    registry = build_default_registry()
    try:
        registry.get(body.tool)
    except Exception:
        raise HTTPException(404, f"unknown tool: {body.tool}")
    ctx = ToolContext(repository=repo, store=get_store(), root=Path(repo.root_path).resolve())
    result = await registry.execute(body.tool, ctx, body.args)
    return result


# ---------------------------------------------------------------------------
# tests / diff
# ---------------------------------------------------------------------------


class RunTestsRequest(BaseModel):
    repository_id: str
    scope: str | None = None
    timeout: float | None = None


@app.post("/api/tests/run")
async def run_tests(body: RunTestsRequest) -> dict[str, Any]:
    repo = _require_repo(body.repository_id)
    from app.services.test_runner import TestRunner

    runner = TestRunner(Path(repo.root_path))
    result = await runner.run(body.scope or "auto", body.timeout)
    return result


@app.get("/api/diff")
async def diff(repo_id: str, staged: bool = False) -> dict[str, Any]:
    repo = _require_repo(repo_id)
    from app.tools.registry import ToolContext, build_default_registry

    registry = build_default_registry()
    ctx = ToolContext(repository=repo, store=get_store(), root=Path(repo.root_path).resolve())
    return await registry.execute("get_git_diff", ctx, {"staged": staged})


@app.post("/api/diff/apply")
async def apply_patch(body: ApplyPatchRequest) -> dict[str, Any]:
    """Controlled patch: generate diff, optionally validate by running tests.

    The API intentionally only applies the patch and returns the diff — it
    does not commit. Tests run only when requested.
    """
    repo = _require_repo(body.repository_id)
    root = Path(repo.root_path).resolve()
    target = (root / body.path).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise HTTPException(400, f"path escapes repository root: {body.path}")

    old = target.read_text(encoding="utf-8", errors="replace") if target.exists() else ""
    new = old + body.content if body.mode == "append" else body.content
    if old == new:
        return {"ok": True, "unchanged": True}
    diff_text = "\n".join(difflib.unified_diff(
        old.splitlines(), new.splitlines(),
        fromfile=f"a/{body.path}", tofile=f"b/{body.path}", lineterm="",
    ))
    # Backup + apply atomically.
    backup = None
    try:
        if target.exists():
            backup = target.read_text(encoding="utf-8", errors="replace")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(new, encoding="utf-8")
    except OSError as e:
        if backup is not None and not target.exists():
            target.write_text(backup, encoding="utf-8")
        raise HTTPException(500, f"failed to write file: {e}")

    test_result = None
    if body.run_tests_after:
        from app.services.test_runner import TestRunner

        test_result = await TestRunner(root).run("auto")
        tests_failed = test_result.get("ok") is False
        exit_suggests_failure = test_result.get("exit_code") not in (0, None)
        if tests_failed and backup is not None and exit_suggests_failure:
            # Rollback on failing tests if the file existed before.
            target.write_text(backup, encoding="utf-8")
            return {"ok": False, "rolled_back": True, "diff": diff_text,
                    "test_result": test_result,
                    "message": "patch applied but tests failed — rolled back"}

    additions = sum(1 for l in diff_text.splitlines() if l.startswith("+") and not l.startswith("+++"))
    deletions = sum(1 for l in diff_text.splitlines() if l.startswith("-") and not l.startswith("---"))
    return {
        "ok": True, "diff": diff_text, "path": body.path,
        "additions": additions, "deletions": deletions,
        "test_result": test_result,
    }


# ---------------------------------------------------------------------------
# evaluation
# ---------------------------------------------------------------------------


class EvalRunRequest(BaseModel):
    repository_id: str


@app.post("/api/evaluation/run")
async def run_evaluation(body: EvalRunRequest) -> dict[str, Any]:
    _require_repo(body.repository_id)
    from app.services.evaluator import run_evaluation_for_repo

    return await _run_in_thread(run_evaluation_for_repo, body.repository_id, get_store())


@app.get("/api/evaluation/benchmark")
async def benchmark_cases() -> dict[str, Any]:
    from app.services.evaluator import get_benchmark

    return {"cases": [c.model_dump() for c in get_benchmark()]}


# ---------------------------------------------------------------------------
# conversations
# ---------------------------------------------------------------------------


@app.get("/api/conversations")
async def conversations(repo_id: str | None = None, limit: int = 50) -> dict[str, Any]:
    convs = get_store().list_conversations(repo_id, limit)
    return {"conversations": [c.model_dump() for c in convs]}


@app.get("/api/conversations/{conv_id}")
async def get_conversation(conv_id: str) -> dict[str, Any]:
    conv = get_store().get_conversation(conv_id)
    if conv is None:
        raise HTTPException(404, f"conversation not found: {conv_id}")
    return {"conversation": conv.model_dump()}
