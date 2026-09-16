"""Kintsugi-Code MCP server — exposes Kintsugi-Code repository tools over the
Model Context Protocol (JSON-RPC 2.0 over stdio).

Implements the core MCP surface: initialize, tools/list, tools/call with a
configurable active repository. Any MCP client (Claude, OpenCode, etc.) can
attach and use Kintsugi-Code's read-only repository intelligence tools.

Run:  python -m app.mcp.server
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from app.services.rag_service import get_retriever
from app.services.store import get_store
from app.tools.registry import ToolContext, build_default_registry

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "Kintsugi-Code", "version": "0.1.0"}

# MCP-exposed tools: name -> (description, input schema, backend tool name)
MCP_TOOLS: dict[str, dict[str, Any]] = {
    "search_code": {
        "description": "Lexical/hybrid code search over the indexed repository.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "mode": {"type": "string", "enum": ["lexical", "symbol", "hybrid"],
                          "description": "Search mode (default hybrid)"},
                "limit": {"type": "integer", "description": "Max results (default 20)"},
            },
            "required": ["query"],
        },
    },
    "get_symbol": {
        "description": "Look up a symbol (function/class/method) with source snippet.",
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Symbol name"}},
            "required": ["name"],
        },
    },
    "get_repository_map": {
        "description": "Structural map of files and their symbols.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    "get_dependencies": {
        "description": "Import dependency edges between repository files.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    "find_path": {
        "description": "Shortest import chain between two indexed files.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "from": {"type": "string", "description": "Starting file path"},
                "to": {"type": "string", "description": "Target file path"},
            },
            "required": ["from", "to"],
        },
    },
    "list_files": {
        "description": "List indexed files with language/size metadata.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Optional glob-ish filter"},
                "limit": {"type": "integer"},
            },
        },
    },
    "read_file": {
        "description": "Read a file from the repository (with secret redaction).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Repository-relative path"},
                "start_line": {"type": "integer"},
                "end_line": {"type": "integer"},
            },
            "required": ["path"],
        },
    },
}


class MCPServer:
    def __init__(self) -> None:
        self.store = get_store()
        self.registry = build_default_registry()
        self.active_repo_id: str | None = None

    def _require_repo(self) -> Any:
        if self.active_repo_id is None:
            raise ValueError(
                "no active repository — call the set_repository tool first "
                "or set Kintsugi-Code_MCP_REPO_ID"
            )
        repo = self.store.get_repository(self.active_repo_id)
        if repo is None:
            raise ValueError(f"unknown repository: {self.active_repo_id}")
        return repo

    def handle_initialize(self, params: dict) -> dict:
        return {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
        }

    def handle_tools_list(self, params: dict) -> dict:
        tools = [
            {
                "name": "set_repository",
                "description": "Set the active Kintsugi-Code repository by id.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"repository_id": {"type": "string"}},
                    "required": ["repository_id"],
                },
            }
        ] + [
            {"name": name, "description": spec["description"],
             "inputSchema": spec["inputSchema"]}
            for name, spec in MCP_TOOLS.items()
        ]
        return {"tools": tools}

    async def handle_tools_call(self, params: dict) -> dict:
        name = params.get("name")
        args = params.get("arguments", {}) or {}
        try:
            if name == "set_repository":
                repo_id = args.get("repository_id", "")
                repo = self.store.get_repository(repo_id)
                if repo is None:
                    raise ValueError(f"unknown repository: {repo_id}")
                self.active_repo_id = repo_id
                return {"content": [{"type": "text",
                                     "text": f"active repository: {repo.name}"}]}
            if name not in MCP_TOOLS:
                raise ValueError(f"unknown tool: {name}")
            repo = self._require_repo()
            ctx = ToolContext(repository=repo, store=self.store,
                              root=Path(repo.root_path).resolve())
            if name in ("search_code",):
                retriever = get_retriever(repo.id)
                if retriever is None:
                    raise ValueError("repository not indexed")
                result = retriever.search(
                    args.get("query", ""), mode=args.get("mode", "hybrid"),
                    limit=int(args.get("limit", 20)),
                )
            else:
                outcome = await self.registry.execute(name, ctx, args)
                if not outcome.get("ok"):
                    raise ValueError(outcome.get("error", "tool failed"))
                result = outcome.get("result", {})
            return {"content": [{"type": "text", "text": json.dumps(result, default=str)[:100_000]}]}
        except Exception as e:  # noqa: BLE001
            return {
                "content": [{"type": "text", "text": f"error: {e}"}],
                "isError": True,
            }

    async def dispatch(self, message: dict) -> dict | None:
        method = message.get("method")
        msg_id = message.get("id")
        params = message.get("params", {}) or {}
        try:
            if method == "initialize":
                result = self.handle_initialize(params)
            elif method == "notifications/initialized":
                return None
            elif method == "tools/list":
                result = self.handle_tools_list(params)
            elif method == "tools/call":
                result = await self.handle_tools_call(params)
            elif method == "ping":
                result = {}
            else:
                if msg_id is None:
                    return None
                return {"jsonrpc": "2.0", "id": msg_id,
                        "error": {"code": -32601, "message": f"method not found: {method}"}}
            if msg_id is None:
                return None
            return {"jsonrpc": "2.0", "id": msg_id, "result": result}
        except Exception as e:  # noqa: BLE001
            if msg_id is None:
                return None
            return {"jsonrpc": "2.0", "id": msg_id,
                    "error": {"code": -32603, "message": str(e)}}


async def serve_stdio() -> None:
    """Line-delimited JSON-RPC over stdin/stdout (MCP stdio transport)."""
    server = MCPServer()
    import os

    env_repo = os.environ.get("Kintsugi-Code_MCP_REPO_ID")
    if env_repo:
        server.active_repo_id = env_repo
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = await server.dispatch(message)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    import asyncio

    asyncio.run(serve_stdio())

