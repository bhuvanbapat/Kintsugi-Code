"""Tool registry and secure tool execution for the agent.

Read-only tools: read_file, search_code, search_symbols, get_symbol,
get_repository_map, get_dependencies, get_git_status, get_git_diff,
get_git_history, list_files, run_tests, run_static_check, inspect_project_config.

Modification tools: apply_patch, write_file, create_file.

Security: path containment inside the active repository (no traversal),
allow-listed git/test commands, subprocess timeouts, output size caps, and no
arbitrary shell.
"""
from __future__ import annotations

import difflib
import re
import subprocess
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.indexing.secrets import redact
from app.models.domain import Repository

log = get_logger(__name__)


class ToolError(Exception):
    pass


class PathSecurityError(ToolError):
    pass


@dataclass
class ToolContext:
    repository: Repository
    store: Any  # app.services.store.Store
    root: Path = field(default_factory=lambda: Path("."))

    def resolve_in_repo(self, rel_path: str) -> Path:
        """Resolve rel_path inside repo root; block traversal outside it."""
        root = self.root.resolve()
        candidate = (root / rel_path).resolve()
        if candidate == root:
            raise ToolError("path must reference a file, not the repository root")
        try:
            candidate.relative_to(root)
        except ValueError:
            raise PathSecurityError(f"path escapes repository root: {rel_path}")
        if not candidate.exists():
            raise ToolError(f"path not found: {rel_path}")
        if not candidate.is_file():
            raise ToolError(f"path is not a file: {rel_path}")
        return candidate


@dataclass
class Tool:
    name: str
    description: str
    handler: Callable[[ToolContext, dict[str, Any]], Awaitable[dict[str, Any]]]
    modifies_files: bool = False
    parameters: dict[str, str] = field(default_factory=dict)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        tool = self._tools.get(name)
        if tool is None:
            raise ToolError(f"unknown tool: {name}")
        return tool

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {"name": t.name, "description": t.description,
             "modifies_files": t.modifies_files, "parameters": t.parameters}
            for t in self._tools.values()
        ]

    async def execute(self, name: str, ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
        tool = self.get(name)
        try:
            result = await tool.handler(ctx, args)
            return {"ok": True, "tool": name, "result": result}
        except ToolError as e:
            return {"ok": False, "tool": name, "error": _sanitize_error(str(e), ctx)}
        except Exception as e:  # noqa: BLE001
            log.warning("tool %s failed: %s", name, e)
            return {"ok": False, "tool": name, "error": _sanitize_error(f"internal error: {e}", ctx)}


def _sanitize_error(message: str, ctx: ToolContext) -> str:
    """Strip the absolute repository path from tool errors (info disclosure)."""
    try:
        root = str(ctx.root.resolve())
        return message.replace(root, "<repo>")
    except Exception:  # noqa: BLE001
        return message


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _read_text(path: Path) -> str:
    data = path.read_bytes()
    if b"\x00" in data[:4096]:
        return "(binary file)"
    return data.decode("utf-8", errors="replace")


def _run_command(cmd: list[str], cwd: Path, timeout: float) -> dict[str, Any]:
    settings = get_settings()
    out = subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout, shell=False,
    )
    stdout = redact(out.stdout or "")
    stderr = redact(out.stderr or "")
    max_out = settings.max_tool_output_bytes
    if len(stdout) > max_out:
        stdout = stdout[:max_out] + "\n...[truncated]"
    if len(stderr) > max_out:
        stderr = stderr[:max_out] + "\n...[truncated]"
    return {"exit_code": out.returncode, "stdout": stdout, "stderr": stderr}


DANGEROUS_COMMAND_PATTERNS = re.compile(
    r"(rm\s+-rf|del\s+/[sq]|format\s+[a-z]:|mkfs|shutdown|reboot|:\(\)\{.*\};:|curl.*\|\s*(ba)?sh|wget.*\|\s*(ba)?sh)",
    re.IGNORECASE,
)


def assert_safe_command(cmd: list[str]) -> None:
    joined = " ".join(cmd)
    if DANGEROUS_COMMAND_PATTERNS.search(joined):
        raise ToolError("command rejected by safety policy")


# ---------------------------------------------------------------------------
# tool implementations
# ---------------------------------------------------------------------------

async def read_file(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    path = ctx.resolve_in_repo(args["path"])
    text = _read_text(path)
    start = int(args.get("start_line", 1))
    end = int(args.get("end_line", 0)) or None
    lines = text.splitlines()
    selected = lines[start - 1: end if end else len(lines)]
    return {
        "path": args["path"],
        "start_line": start,
        "end_line": start + len(selected) - 1,
        "content": redact("\n".join(selected)),
        "total_lines": len(lines),
    }


async def list_files(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    files = ctx.store.list_files(ctx.repository.id)
    pattern = args.get("pattern")
    if pattern:
        rx = re.compile(re.escape(pattern).replace(r"\*", ".*"))
        files = [f for f in files if rx.search(f.path)]
    include_ignored = args.get("include_non_source", False)
    if not include_ignored:
        files = [f for f in files if f.is_source or f.is_test or f.is_manifest]
    limit = int(args.get("limit", 200))
    return {"files": [
        {"path": f.path, "language": f.language, "is_test": f.is_test,
         "lines": f.line_count, "size": f.size_bytes}
        for f in files[:limit]
    ], "total": len(files)}


async def search_code(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    from app.services.rag_service import get_retriever

    retriever = get_retriever(ctx.repository.id)
    if retriever is None:
        raise ToolError("repository not indexed")
    result = retriever.search(args["query"], mode="lexical", limit=int(args.get("limit", 20)))
    return result


async def search_symbols(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    from app.services.rag_service import get_retriever

    retriever = get_retriever(ctx.repository.id)
    if retriever is None:
        raise ToolError("repository not indexed")
    return retriever.search(args["query"], mode="symbol", limit=int(args.get("limit", 20)))


async def get_symbol(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    name = args["name"].lower()
    matches = [s for s in ctx.store.list_symbols(ctx.repository.id) if s.name.lower() == name]
    if not matches:
        partial = [s for s in ctx.store.list_symbols(ctx.repository.id) if name in s.name.lower()]
        matches = partial[:10]
    out = []
    for s in matches[:20]:
        content = ctx.store.get_file_content(ctx.repository.id, s.file_path) or ""
        lines = content.splitlines()
        snippet = "\n".join(lines[max(0, s.start_line - 1):s.end_line])[:2000]
        out.append(s.model_dump() | {"snippet": redact(snippet)})
    return {"symbols": out}


async def get_repository_map(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    from app.services.indexer import build_repository_map

    return build_repository_map(ctx.store, ctx.repository.id)


async def get_dependencies(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    symbols = ctx.store.list_symbols(ctx.repository.id)
    rels = ctx.store.list_relationships(ctx.repository.id)
    sym_index = {s.id: s for s in symbols}
    edges = []
    for r in rels:
        if r.kind.value != "imports":
            continue
        src = sym_index.get(r.source)
        if not src:
            continue
        tgt = sym_index.get(r.target)
        if tgt is not None and tgt.kind.value == "module":
            module_name = tgt.name.removeprefix("module:")
        else:
            module_name = r.target
        edges.append({
            "from_file": src.file_path,
            "import": module_name,
            "symbol": src.name,
        })
    return {"dependencies": edges[:500]}


async def find_path(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    """Shortest import chain between two files (BFS over resolved import edges)."""
    from collections import deque

    from app.indexing.language import resolve_module_path

    start, end = str(args.get("from", "")), str(args.get("to", ""))
    if not start or not end:
        raise ToolError("find_path requires 'from' and 'to' file paths")
    files = ctx.store.list_files(ctx.repository.id)
    file_set = {f.path for f in files if f.is_source}
    if start not in file_set or end not in file_set:
        raise ToolError("both endpoints must be indexed source files")

    symbols = ctx.store.list_symbols(ctx.repository.id)
    rels = ctx.store.list_relationships(ctx.repository.id)
    sym_by_id = {s.id: s for s in symbols}
    adjacency: dict[str, set[str]] = {}
    for r in rels:
        if r.kind.value != "imports":
            continue
        src = sym_by_id.get(r.source)
        if not src:
            continue
        tgt = sym_by_id.get(r.target)
        if tgt is None or tgt.kind.value != "module":
            continue
        resolved = resolve_module_path(tgt.name.removeprefix("module:"), file_set)
        if resolved and resolved != src.file_path:
            adjacency.setdefault(src.file_path, set()).add(resolved)

    queue = deque([(start, [start])])
    visited = {start}
    while queue:
        node, path = queue.popleft()
        if node == end:
            return {"found": True, "path": path, "hops": len(path) - 1}
        for neighbor in sorted(adjacency.get(node, ())):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))
    return {"found": False, "path": [], "hops": 0,
            "note": f"no import chain from {start} to {end}"}


async def get_git_status(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    res = _run_command(["git", "status", "--porcelain"], cwd=ctx.root, timeout=30)
    if res["exit_code"] != 0:
        raise ToolError("git status failed — not a git repository? " + res["stderr"][:200])
    lines = [l for l in res["stdout"].splitlines() if l.strip()]
    return {"modified": len(lines), "entries": lines[:200]}


async def get_git_diff(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    staged = bool(args.get("staged", False))
    cmd = ["git", "diff", "--staged"] if staged else ["git", "diff"]
    res = _run_command(cmd + ["--stat"], cwd=ctx.root, timeout=60)
    if res["exit_code"] != 0:
        raise ToolError("git diff failed: " + res["stderr"][:200])
    full = _run_command(cmd, cwd=ctx.root, timeout=60)
    diff = redact(full["stdout"])
    settings = get_settings()
    if len(diff) > settings.max_tool_output_bytes:
        diff = diff[: settings.max_tool_output_bytes] + "\n...[truncated]"
    return {"stat": res["stdout"], "diff": diff}


async def get_git_history(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    limit = int(args.get("limit") or 30)
    res = _run_command(
        ["git", "log", "--oneline", "-n", str(limit)],
        cwd=ctx.root, timeout=30,
    )
    if res["exit_code"] != 0:
        raise ToolError("git log failed: " + res["stderr"][:200])
    return {"log": res["stdout"].splitlines()}


async def run_tests(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    from app.services.test_runner import TestRunner

    runner = TestRunner(ctx.root)
    return await runner.run(args.get("scope") or "auto", timeout=args.get("timeout"))


async def run_static_check(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    from app.services.test_runner import TestRunner

    runner = TestRunner(ctx.root)
    return await runner.static_check()


async def inspect_project_config(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    from app.services.test_runner import detect_project_type

    return detect_project_type(ctx.root)


# -- modification tools -------------------------------------------------------

async def write_file(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    """Propose a file write: returns the diff that WOULD be applied.

    Agent tools never touch disk directly — changes are applied only via the
    controlled /api/diff/apply endpoint (which validates and can roll back).
    """
    rel = args["path"]
    root = ctx.root.resolve()
    target = (root / rel).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise PathSecurityError(f"path escapes repository root: {rel}")
    old = _read_text(target) if target.exists() else ""
    new = args["content"]
    diff = "\n".join(difflib.unified_diff(
        old.splitlines(), new.splitlines(),
        fromfile=f"a/{rel}", tofile=f"b/{rel}", lineterm="",
    ))
    return {"path": rel, "diff": diff, "proposed": True, "bytes": len(new)}


async def create_file(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    rel = args["path"]
    root = ctx.root.resolve()
    target = (root / rel).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise PathSecurityError(f"path escapes repository root: {rel}")
    if target.exists():
        raise ToolError(f"file already exists: {rel}")
    return await write_file(ctx, args)


async def apply_patch(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    """Apply a change: 'full' replaces file, 'append' appends, 'patch' is a unified diff."""
    rel = args["path"]
    root = ctx.root.resolve()
    target = (root / rel).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise PathSecurityError(f"path escapes repository root: {rel}")
    old = _read_text(target) if target.exists() else ""
    mode = args.get("mode", "full")
    if mode == "append":
        new = old + ("\n" if old and not old.endswith("\n") else "") + args["content"]
    else:
        new = args["content"]
    diff = "\n".join(difflib.unified_diff(
        old.splitlines(), new.splitlines(),
        fromfile=f"a/{rel}", tofile=f"b/{rel}", lineterm="",
    ))
    additions = sum(1 for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++"))
    deletions = sum(1 for l in diff.splitlines() if l.startswith("-") and not l.startswith("---"))
    return {"path": rel, "diff": diff, "additions": additions, "deletions": deletions}


def build_default_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(Tool("read_file", "Read a file with line range", read_file,
                      parameters={"path": "string", "start_line": "int?", "end_line": "int?"}))
    reg.register(Tool("list_files", "List indexed files", list_files,
                      parameters={"pattern": "string?", "limit": "int?"}))
    reg.register(Tool("search_code", "Lexical code search", search_code,
                      parameters={"query": "string", "limit": "int?"}))
    reg.register(Tool("search_symbols", "Symbol search", search_symbols,
                      parameters={"query": "string", "limit": "int?"}))
    reg.register(Tool("get_symbol", "Get symbol details with snippet", get_symbol,
                      parameters={"name": "string"}))
    reg.register(Tool("get_repository_map", "Structural repository map", get_repository_map,
                      parameters={}))
    reg.register(Tool("get_dependencies", "Import dependency edges", get_dependencies,
                      parameters={}))
    reg.register(Tool("find_path", "Shortest import chain between two files",
                      find_path,
                      parameters={"from": "string", "to": "string"}))
    reg.register(Tool("get_git_status", "Git working tree status", get_git_status,
                      parameters={}))
    reg.register(Tool("get_git_diff", "Git diff (staged or unstaged)", get_git_diff,
                      parameters={"staged": "bool?"}))
    reg.register(Tool("get_git_history", "Recent git history", get_git_history,
                      parameters={"limit": "int?"}))
    reg.register(Tool("run_tests", "Run project tests", run_tests,
                      parameters={"scope": "string?", "timeout": "int?"}))
    reg.register(Tool("run_static_check", "Run static checks (lint)", run_static_check,
                      parameters={}))
    reg.register(Tool("inspect_project_config", "Detect project type and commands", inspect_project_config,
                      parameters={}))
    reg.register(Tool("apply_patch", "Propose a file change (returns diff for approval)", apply_patch,
                      modifies_files=True,
                      parameters={"path": "string", "content": "string", "mode": "full|append?"}))
    reg.register(Tool("write_file", "Write full file content (returns diff)", write_file,
                      modifies_files=True, parameters={"path": "string", "content": "string"}))
    reg.register(Tool("create_file", "Create a new file (returns diff)", create_file,
                      modifies_files=True, parameters={"path": "string", "content": "string"}))
    return reg
