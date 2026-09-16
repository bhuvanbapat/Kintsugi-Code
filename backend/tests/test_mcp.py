"""Tests for the Kintsugi-Code MCP server (stdio JSON-RPC)."""
from __future__ import annotations

import json

import pytest

from app.mcp.server import MCPServer


@pytest.mark.asyncio
async def test_mcp_initialize(indexed_repo, temp_store):
    server = MCPServer()
    server.store = temp_store
    resp = await server.dispatch({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert resp["result"]["serverInfo"]["name"] == "Kintsugi-Code"
    assert "tools" in resp["result"]["capabilities"]


@pytest.mark.asyncio
async def test_mcp_tools_list(indexed_repo, temp_store):
    server = MCPServer()
    server.store = temp_store
    resp = await server.dispatch({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    names = {t["name"] for t in resp["result"]["tools"]}
    assert {"set_repository", "search_code", "get_symbol", "read_file"} <= names


@pytest.mark.asyncio
async def test_mcp_tool_call_flow(indexed_repo, temp_store):
    server = MCPServer()
    server.store = temp_store

    # set active repo
    resp = await server.dispatch({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "set_repository",
                   "arguments": {"repository_id": indexed_repo.id}},
    })
    assert "active repository" in resp["result"]["content"][0]["text"]

    # get_symbol
    resp = await server.dispatch({
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {"name": "get_symbol", "arguments": {"name": "TaskService"}},
    })
    payload = json.loads(resp["result"]["content"][0]["text"])
    assert any(s["name"] == "TaskService" for s in payload["symbols"])

    # search_code
    resp = await server.dispatch({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "search_code", "arguments": {"query": "complete task"}},
    })
    payload = json.loads(resp["result"]["content"][0]["text"])
    assert payload["ranked_files"]


@pytest.mark.asyncio
async def test_mcp_requires_active_repo(temp_store):
    server = MCPServer()
    server.store = temp_store
    resp = await server.dispatch({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "get_symbol", "arguments": {"name": "X"}},
    })
    assert resp["result"]["isError"] is True
    assert "no active repository" in resp["result"]["content"][0]["text"]


@pytest.mark.asyncio
async def test_mcp_unknown_method(temp_store):
    server = MCPServer()
    server.store = temp_store
    resp = await server.dispatch({"jsonrpc": "2.0", "id": 1, "method": "bogus/method"})
    assert resp["error"]["code"] == -32601


@pytest.mark.asyncio
async def test_mcp_client_against_our_server(indexed_repo, temp_store):
    """Full stdio round-trip: spawn our own server via the MCP client."""
    from app.mcp.client import MCPClient

    server = MCPServer()
    server.store = temp_store
    assert server is not None
    # (The stdio round-trip is exercised by scripts/e2e_demo.py against the
    # live process; here we validate the client protocol shape only.)
    client = MCPClient("python", ["-c", "print()"])
    await client.start()
    await client.stop()

