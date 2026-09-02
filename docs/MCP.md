# CodeForge — MCP Integration

## Purpose

The [Model Context Protocol](https://modelcontextprotocol.io) standardizes how
LLM applications expose and consume tools. CodeForge participates on both
sides:

1. **Server** — external MCP clients (Claude Desktop, OpenCode, IDEs) can use
   CodeForge's repository intelligence tools.
2. **Client** — CodeForge can call tools exposed by other MCP servers
   (e.g. a graphify server), keeping the integration layer modular.

## Protocol level

Implements the MCP 2024-11-05 base surface over the stdio transport
(line-delimited JSON-RPC 2.0):

- `initialize` → serverInfo + capabilities
- `notifications/initialized` (accepted, no response)
- `tools/list` → tool descriptors with JSON-Schema inputs
- `tools/call` → content responses (`text` blocks), `isError` on failure
- `ping` → `{}`

## Running the server

```bash
cd backend
.venv\Scripts\python -m app.mcp.server
# optional: preselect a repository
set CODEFORGE_MCP_REPO_ID=<repo id>
```

### Exposed tools

| Tool | Input | Description |
|---|---|---|
| `set_repository` | `repository_id` | select the active indexed repository |
| `search_code` | `query`, `mode?`, `limit?` | hybrid/lexical/symbol search |
| `get_symbol` | `name` | symbol lookup with source snippet (redacted) |
| `get_repository_map` | — | structural file/symbol map |
| `get_dependencies` | — | import dependency edges |
| `list_files` | `pattern?`, `limit?` | indexed file inventory |
| `read_file` | `path`, line range | content with secret redaction |

Verified end-to-end (subprocess stdio round-trip): `scripts/verify_mcp.py` —
initialize, tools/list, set_repository, get_symbol (TaskService found),
search_code (correct top file). All PASS.

## Client usage

```python
from app.mcp.client import MCPClient

client = MCPClient("python", ["-m", "graphify.cli", "--mcp"], cwd=repo_root)
await client.start()
info = await client.initialize()
tools = await client.list_tools()
result = await client.call_tool("query", {"question": "Where is auth?"})
await client.stop()
```

External servers are configured via `backend/mcp_servers.json` (not committed
by default) — loaded by `load_mcp_config()`.

## Security considerations

- The server speaks stdio only (no network listener).
- Tool calls run through the same tool registry: path containment, secret
  redaction, and output caps apply identically to MCP-originated calls.
- No repository mutation tools are exposed over MCP (read-only surface +
  `set_repository`).
- External MCP servers spawned by the client inherit the process
  environment; operators should scope credentials accordingly.

## Limitations

- Base protocol only: no resources/prompts/sampling yet — tools are the
  useful surface for this product today and keep the surface auditable.
- One active repository per server process (switchable via `set_repository`).
- Windows-first testing; stdio line framing is platform-agnostic but CI runs
  Linux, where the same code path is exercised via pytest.
