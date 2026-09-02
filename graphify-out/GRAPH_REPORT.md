# Graph Report - CodeForge  (2026-09-02)

## Corpus Check
- Corpus is ~24,214 words - fits in a single context window. You may not need a graph.

## Summary
- 597 nodes · 1467 edges · 34 communities (31 shown, 3 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 130 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Frontend UI & Pages
- Language Detection
- FastAPI Routes
- Test Runner & Indexing
- Sample Repo (Campus Tasks)
- Agent Engine
- AST Parser
- MCP Server & Context Engine
- Persistence Store
- Core Config
- MCP Client
- Frontend Dependencies
- Scanner & Retrieval
- Models & Tools
- LLM Providers
- Module Group 15
- Module Group 16
- Module Group 17
- Module Group 32
- Module Group 33

## God Nodes (most connected - your core abstractions)
1. `Store` - 50 edges
2. `ToolContext` - 33 edges
3. `build_default_registry()` - 30 edges
4. `Agent` - 25 edges
5. `get_store()` - 24 edges
6. `get_settings()` - 23 edges
7. `get_retriever()` - 21 edges
8. `redact()` - 20 edges
9. `index_repository()` - 20 edges
10. `Repository` - 19 edges

## Surprising Connections (you probably didn't know these)
- `Agent` --uses--> `LLMProvider`  [INFERRED]
  backend/app/agent/engine.py → backend/app/llm/providers.py
- `Agent` --uses--> `EvidenceCitation`  [INFERRED]
  backend/app/agent/engine.py → backend/app/models/domain.py
- `Agent` --uses--> `ContextEngine`  [INFERRED]
  backend/app/agent/engine.py → backend/app/retrieval/context_engine.py
- `Agent` --uses--> `Store`  [INFERRED]
  backend/app/agent/engine.py → backend/app/services/store.py
- `Agent` --uses--> `ToolContext`  [INFERRED]
  backend/app/agent/engine.py → backend/app/tools/registry.py

## Import Cycles
- None detected.

## Communities (34 total, 3 thin omitted)

### Community 0 - "Frontend UI & Pages"
Cohesion: 0.08
Nodes (41): api, EmptyState(), ErrorBox(), Spinner(), StatRow(), useAsync(), Layout(), NAV (+33 more)

### Community 1 - "Language Detection"
Cohesion: 0.08
Nodes (50): detect_language(), is_config_file(), is_doc_file(), is_manifest_file(), is_source_file(), is_test_file(), Language detection and file classification for repository scanning., _is_ignored() (+42 more)

### Community 2 - "FastAPI Routes"
Cohesion: 0.10
Nodes (56): reset_provider(), apply_patch(), ApplyPatchRequest, benchmark_cases(), chat(), ChatRequest, conversations(), delete_repository() (+48 more)

### Community 3 - "Test Runner & Indexing"
Cohesion: 0.11
Nodes (41): Replace likely secret values with REDACTED, preserving key names., redact(), build_repository_map(), Produce a compact structural map used for LLM context and the graph view., detect_project_type(), parse_test_output(), Any, Path (+33 more)

### Community 4 - "Sample Repo (Campus Tasks)"
Cohesion: 0.09
Nodes (29): make_app(), Any, Campus Task Management — HTTP API routes (framework-free simulation)., Campus Task Management — data layer (in-memory repositories). A small realistic…, In-memory persistence for Task entities., Task, TaskRepository, InvalidTaskError (+21 more)

### Community 5 - "Agent Engine"
Cohesion: 0.09
Nodes (30): Agent, asyncio_wait_for, AgentRun, Any, Controlled engineering agent. State machine (AgentState) with validated…, Deterministic, explainable tool-selection policy., Merge useful tool output into LLM context (bounded)., Small helper so we don't import asyncio at module top for one call. (+22 more)

### Community 6 - "AST Parser"
Cohesion: 0.11
Nodes (36): _attr_name(), _extract_python_ast(), extract_symbols(), extract_symbols_async(), _extract_tree_sitter(), _get_parser(), _import_name_for_node(), _kind_from_node_type() (+28 more)

### Community 7 - "MCP Server & Context Engine"
Cohesion: 0.09
Nodes (24): CodeForge MCP server — exposes CodeForge repository tools over the Model…, EvidenceCitation, ContextEngine, detect_query_intent(), Context engine: turn a user query into a bounded, evidence-rich LLM context.…, Find the best line window matching the query inside file content., _relevant_line_window(), HybridRetriever (+16 more)

### Community 8 - "Persistence Store"
Cohesion: 0.08
Nodes (10): Conversation, TimestampedModel, AgentRun, Any, FileEntry, Repository, Symbol, Thread-local SQLite store. All project data lives in one DB file. (+2 more)

### Community 9 - "Core Config"
Cohesion: 0.12
Nodes (15): ABC, get_settings(), Application configuration via environment variables with .env support., Settings, create_provider(), get_provider(), LLMProvider, LLMResponse (+7 more)

### Community 10 - "MCP Client"
Cohesion: 0.12
Nodes (15): MCPClient, Minimal stdio MCP client for tool discovery and invocation., MCPServer, Any, Line-delimited JSON-RPC over stdin/stdout (MCP stdio transport)., serve_stdio(), asyncio, Tests for the CodeForge MCP server (stdio JSON-RPC). (+7 more)

### Community 11 - "Frontend Dependencies"
Cohesion: 0.07
Nodes (28): dependencies, react, react-dom, react-router-dom, devDependencies, @types/react, @types/react-dom, typescript (+20 more)

### Community 12 - "Scanner & Retrieval"
Cohesion: 0.10
Nodes (19): compilerOptions, isolatedModules, jsx, lib, module, moduleResolution, noEmit, noFallthroughCasesInSwitch (+11 more)

### Community 13 - "Models & Tools"
Cohesion: 0.21
Nodes (9): get_logger(), Structured logging that never logs secrets., redact_secrets(), SecretRedactingFilter, load_mcp_config(), MCP client: connect CodeForge to external MCP servers over stdio. Lets the…, Read MCP server configuration from env or mcp_servers.json., Logger (+1 more)

### Community 14 - "LLM Providers"
Cohesion: 0.40
Nodes (5): Controlled agent loop, CodeForge, Controlled code modification, Hybrid retrieval, Repository indexing

### Community 15 - "Module Group 15"
Cohesion: 0.67
Nodes (3): call(), main(), End-to-end demonstration against the LIVE backend. Executes the full product…

### Community 16 - "Module Group 16"
Cohesion: 0.67
Nodes (3): call_api(), main(), Verify the CodeForge MCP server over real stdio (subprocess round-trip).

## Knowledge Gaps
- **47 isolated node(s):** `codeforge-backend`, `campus-tasks`, `name`, `private`, `version` (+42 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Store` connect `Persistence Store` to `Language Detection`, `FastAPI Routes`, `Test Runner & Indexing`, `Agent Engine`, `AST Parser`, `MCP Server & Context Engine`, `Core Config`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Why does `ToolContext` connect `Test Runner & Indexing` to `Language Detection`, `FastAPI Routes`, `Agent Engine`, `MCP Server & Context Engine`, `MCP Client`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Why does `get_retriever()` connect `MCP Server & Context Engine` to `Language Detection`, `FastAPI Routes`, `Test Runner & Indexing`, `Agent Engine`, `MCP Client`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `Store` (e.g. with `Agent` and `run_evaluation_for_repo()`) actually correct?**
  _`Store` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `ToolContext` (e.g. with `Agent` and `diff()`) actually correct?**
  _`ToolContext` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `build_default_registry()` (e.g. with `apply_patch()` and `create_file()`) actually correct?**
  _`build_default_registry()` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `Agent` (e.g. with `AgentStateMachine` and `LLMProvider`) actually correct?**
  _`Agent` has 16 INFERRED edges - model-reasoned connections that need verification._