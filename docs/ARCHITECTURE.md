# Kintsugi-Code — Architecture

## System overview

```mermaid
flowchart LR
    UI[React frontend<br/>12 screens] -->|/api/*| API[FastAPI backend]
    API --> Scanner[indexing/scanner<br/>+ language detection]
    Scanner --> AST[indexing/ast_parser<br/>tree-sitter]
    AST --> Store[(SQLite<br/>files / symbols / rels / docs)]
    API --> Retrieval[retrieval/hybrid<br/>BM25 + symbol]
    Retrieval --> CtxEngine[retrieval/context_engine<br/>token budget]
    CtxEngine --> LLM[llm/providers<br/>openai | mock]
    API --> Agent[agent/engine<br/>state machine + tools]
    Agent --> Tools[tools/registry<br/>17 tools]
    Tools --> Store
    Tools --> Runner[services/test_runner<br/>allow-listed subprocess]
    Agent --> Runs[(runs / traces)]
    MCP[mcp/server + client<br/>stdio JSON-RPC] <--> API
```

## Components

### 1. Indexing pipeline (backend/app/indexing)

```
normalize_repo_path (validate, resolve)
→ RepositoryScanner (ignore rules, size caps, file caps)
→ classification: language / test / doc / config / manifest / source
→ secret detection + redaction (before anything is stored)
→ AST extraction (tree-sitter; stdlib-ast fallback for Python)
   symbols: name, kind, file, start/end line, parent, signature
   relationships: contains (file→symbol, class→method), imports (→module nodes)
→ SQLite persistence (replace-per-repo, idempotent re-index)
```

Design decisions:
- **Partial failure isolation**: a file that fails to parse is counted and
  skipped — one bad file never aborts indexing.
- **Module pseudo-symbols**: imports create `module:<name>` symbol nodes so
  import edges survive persistence and can be resolved to files later.
- **Byte-offset discipline**: tree-sitter offsets are byte offsets; the
  extractor always slices the UTF-8-encoded buffer (a bug class we found and
  fixed during development — see ADR-002).

### 2. Hybrid retrieval (backend/app/retrieval)

Three retrievers fused by ranked score blending:

| Tier | Mechanism | Notes |
|---|---|---|
| Lexical | Pure-Python BM25 over the in-memory token index | thread-safe, no per-thread SQLite handles |
| Structural | Symbol-name matching with rarity-weighted tokens | exact > substring; rare tokens weigh more; stopwords excluded |
| Importance | File heuristics | manifests ↑, tests ↓, entrypoints ↑ |

Ranked files = lexical score + symbol evidence bonus + importance prior.
Symbol scoring was tuned against the evaluation benchmark (short generic
names like `Task` initially dominated; rarity weighting fixed it — measured
in docs/EVALUATION.md).

### 3. Context engine

```
query → intent detection (locate/explain/analyze/plan)
→ hybrid search (bounded candidates)
→ structural expansion (symbol-defining files included whole-ish)
→ best-line windowing for the rest (±12 lines around token match)
→ hard token budget (chars/4) — files are trimmed, never the whole repo
→ citations with file + line range + confidence
```

### 4. Provider abstraction (backend/app/llm)

- `LLMProvider` interface: `complete(system, prompt, context)`.
- `OpenAIProvider`: any OpenAI-compatible `/chat/completions` endpoint
  (httpx, no vendor SDK) — works with OpenAI, Ollama, vLLM, LM Studio.
- `MockProvider`: deterministic offline answers assembled **from the
  retrieval evidence passed in context** — it never invents repository
  facts, and it labels its own confidence.
- Usage reporting: providers that report tokens are surfaced; the mock
  provider reports honest estimates; UI shows "unavailable" when unknown.

### 5. Tool system (backend/app/tools)

17 tools in a registry. Safety model:

- **Path containment**: `ToolContext.resolve_in_repo` resolves and verifies
  every path stays under the repository root (`Path.relative_to` check) —
  traversal raises `PathSecurityError` (unit-tested).
- **Command policy**: git and test commands are hardcoded allow-lists; a
  regex layer blocks `rm -rf`, `curl|sh`, fork bombs (unit-tested).
- **Subprocess hardening**: `shell=False`, timeouts, output truncation,
  secret redaction on all captured output.
- **Mode policy**: each TaskMode (explain/locate/analyze/plan/test/fix/review)
  has an explicit tool allow-list; modification tools are additionally gated
  by ExecutionMode.

### 6. Agent (backend/app/agent)

Validated state machine:

```
IDLE → ANALYZING → RETRIEVING → PLANNING → EXECUTING ⇄ TESTING
                    ↑    ↓         ↓          ↓
                ITERATING  DIAGNOSING  COMPLETED/FAILED/CANCELLED
```

Invalid transitions raise (unit-tested). Loop protection:
- max iterations (configurable, default 12)
- repeated identical tool-call detection
- no-progress counter (2 repeats or 3 consecutive failures stop the run)
- per-tool timeout

Tool selection is a deterministic, explainable policy per mode (iteration 1:
run_tests for TEST/FIX, get_git_diff for REVIEW, search_symbols for LOCATE,
get_repository_map otherwise) — no hidden LLM tool-choice loop in mock mode.

### 7. Test runner (backend/app/services/test_runner)

Detects project type from manifest files (pyproject/package.json/go.mod/
Cargo.toml/pom.xml/build.gradle), builds the test command, runs it with a
timeout, and parses pass/fail/error/skipped counts + failed test names from
pytest and JS/go/rust/maven output formats.

### 8. Controlled modification workflow

```
request → old content read → new content composed
→ unified diff generated → applied (atomic write with backup)
→ tests run when requested → rollback if exit code != 0 and file existed
→ response: diff, additions/deletions, test result, rollback flag
```

The rollback path is integration-tested: a syntax-breaking patch is applied,
tests fail, the original file is restored byte-identically.

### 9. MCP layer (backend/app/mcp)

- **Server**: `python -m app.mcp.server` — stdio transport, JSON-RPC 2.0,
  implements initialize/tools/list/tools/call per MCP 2024-11-05. Verified
  with a live subprocess round-trip (scripts/verify_mcp.py).
- **Client**: `MCPClient` spawns any external MCP server (e.g. graphify),
  initializes, lists tools, calls them — so the agent can incorporate external
  capabilities without code changes.

### 10. Persistence (backend/app/services/store)

Single SQLite file (WAL mode). Tables: repositories, files, symbols,
relationships, file_docs (redacted content for retrieval), runs, conversations,
kv. Thread-local connections; all payloads JSON-serialized Pydantic models.

## Data flow: repository question

```
1. POST /api/chat {message, mode}
2. Conversation loaded/created
3. Agent.run: state ANALYZING → RETRIEVING
4. ContextEngine.build_context(task) → citations + snippets
5. Tool loop (bounded): map → deps → status per policy
6. Provider.complete(system, task, context) → grounded answer
7. Evidence + run (with tool timings) persisted
8. Response: message + run trace
```

## Data flow: controlled fix

```
1. POST /api/diff/apply {path, content, run_tests_after}
2. Path containment check
3. Diff computed; backup taken; file written
4. Tests run (allow-listed command)
5. Non-zero exit → restore backup → {rolled_back: true, test_result}
6. Success → {diff, additions, deletions, test_result}
```

## Development tooling

This codebase was itself built with structural tooling:
- **Graphify** knowledge graph (`graphify-out/`) — 597 nodes / 1467 edges /
  34 communities; used to verify architectural boundaries (e.g. agent engine
  community contains only agent+state machine files).
- The `graphify` OpenCode skill was the primary skill used during development
  (structural understanding, change-impact queries); a project-local skill
  (`.opencode/skills/Kintsugi-Code-dev`) captures the repo's own conventions.

## Deployment

- Local: uvicorn + vite dev (default).
- Docker: `docker compose up --build` — frontend build is served by nginx,
  backend by uvicorn; single compose network.
- CI: GitHub Actions runs backend tests + frontend typecheck/build on push.

