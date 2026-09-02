"""MCP client: connect CodeForge to external MCP servers over stdio.

Lets the agent use external MCP tools (e.g. graphify's MCP server) alongside
built-in tools. Runs a configured server as a subprocess speaking
line-delimited JSON-RPC.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
from pathlib import Path

from app.core.logging import get_logger

log = get_logger(__name__)


class MCPClient:
    """Minimal stdio MCP client for tool discovery and invocation."""

    def __init__(self, command: str, args: list[str] | None = None,
                 env: dict[str, str] | None = None, cwd: str | None = None) -> None:
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.cwd = cwd
        self._proc: asyncio.subprocess.Process | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        if self._proc is not None and self._proc.returncode is None:
            return
        exe = shutil.which(self.command) or self.command
        merged_env = {**os.environ, **self.env}
        self._proc = await asyncio.create_subprocess_exec(
            exe, *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=merged_env,
            cwd=self.cwd,
        )
        log.info("MCP server started: %s %s", self.command, " ".join(self.args))

    async def _send(self, payload: dict) -> dict | None:
        if self._proc is None or self._proc.stdin is None or self._proc.stdout is None:
            raise RuntimeError("MCP client not started")
        async with self._lock:
            self._proc.stdin.write((json.dumps(payload) + "\n").encode())
            await self._proc.stdin.drain()
            # Read one line back (skip empty lines).
            while True:
                raw = await self._proc.stdout.readline()
                if not raw:
                    raise RuntimeError("MCP server closed stdout")
                line = raw.decode().strip()
                if line:
                    return json.loads(line)

    async def initialize(self) -> dict:
        return await self._send({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05",
                       "clientInfo": {"name": "codeforge", "version": "0.1.0"}},
        }) or {}

    async def list_tools(self) -> list[dict]:
        resp = await self._send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        return (resp or {}).get("result", {}).get("tools", [])

    async def call_tool(self, name: str, arguments: dict) -> dict:
        resp = await self._send({
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        })
        return resp or {}

    async def stop(self) -> None:
        if self._proc is not None and self._proc.returncode is None:
            self._proc.terminate()
            try:
                await asyncio.wait_for(self._proc.wait(), timeout=5)
            except TimeoutError:
                self._proc.kill()
        self._proc = None


def load_mcp_config() -> dict:
    """Read MCP server configuration from env or mcp_servers.json."""
    config_path = Path(__file__).resolve().parent.parent / "mcp_servers.json"
    if config_path.exists():
        return json.loads(config_path.read_text(encoding="utf-8"))
    return {}
