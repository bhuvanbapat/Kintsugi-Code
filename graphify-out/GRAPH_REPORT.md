# Graph Report - CodeForge  (2026-09-03)

## Corpus Check
- 100 files · ~44,258 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 886 nodes · 1821 edges · 59 communities (55 shown, 4 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 146 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `eedd9131`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- logging.py
- main.tsx
- registry.py
- test_agent_api.py
- main.py
- TaskRepository
- get_settings
- devDependencies
- get_retriever
- Store
- MCPServer
- ast_parser.py
- compilerOptions
- domain.py
- 3. The backend — module by module, line counts included
- test_scanner_secrets.py
- adversarial_wave2.py
- conftest.py
- indexer.py
- final_verify.py
- verify_mcp.py
- adversarial_api.py
- refresh_graph.py
- campus-tasks
- codeforge-backend
- Components
- The 10 demo workflows
- CodeForge
- CodeForge — Interview Guide
- BUILD STATUS — CodeForge
- CodeForge — Résumé Notes
- CodeForge — MCP Integration
- CodeForge — Security
- [0.1.0] - 2026-09-02
- Contributing to CodeForge
- ADR-003: Hybrid retrieval without a vector database
- CodeForge — Evaluation
- ADR-001: Modular monolith
- ADR-002: Tree-sitter for structural parsing (with stdlib-ast fallback)
- ADR-004: Provider abstraction with a deterministic offline mock
- ADR-005: Controlled execution, never blind file writes
- ADR-006: Local-first demo mode as default
- ADR-007: MCP as the integration layer (tools-first, stdio)
- Campus Task Management (sample_repo)
- CodeForge development skill

## God Nodes (most connected - your core abstractions)
1. `Store` - 51 edges
2. `ToolContext` - 41 edges
3. `build_default_registry()` - 37 edges
4. `Agent` - 25 edges
5. `get_settings()` - 25 edges
6. `get_store()` - 24 edges
7. `redact()` - 23 edges
8. `index_repository()` - 23 edges
9. `TaskMode` - 21 edges
10. `get_retriever()` - 21 edges

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

## Communities (59 total, 4 thin omitted)

### Community 0 - "logging.py"
Cohesion: 0.07
Nodes (41): _add_filter(), get_logger(), install(), Logger, Structured logging that never logs secrets. Redaction is enforced at THREE…, Redact a record in place: msg, args (tuple or dict), exc text., Install redaction on every relevant logging path. - global LogRecord factory…, _redact_record() (+33 more)

### Community 1 - "main.tsx"
Cohesion: 0.08
Nodes (41): api, EmptyState(), ErrorBox(), Spinner(), StatRow(), useAsync(), Layout(), NAV (+33 more)

### Community 2 - "registry.py"
Cohesion: 0.08
Nodes (57): Map a dotted module name (e.g. 'data.repositories') to a repo file. Shared by…, resolve_module_path(), build_repository_map(), Produce a compact structural map used for LLM context and the graph view., detect_project_type(), parse_test_output(), Any, Path (+49 more)

### Community 3 - "test_agent_api.py"
Cohesion: 0.07
Nodes (39): Agent, AgentRun, Any, Controlled engineering agent. State machine (AgentState) with validated…, Deterministic, explainable tool-selection policy., Merge useful tool output into LLM context (bounded)., _summarize(), Product-level agent skills (directive §54). Each TaskMode maps to a SkillSpec:… (+31 more)

### Community 4 - "main.py"
Cohesion: 0.13
Nodes (48): reset_provider(), apply_patch(), ApplyPatchRequest, benchmark_cases(), chat(), ChatRequest, conversations(), delete_repository() (+40 more)

### Community 5 - "TaskRepository"
Cohesion: 0.09
Nodes (29): make_app(), Any, Campus Task Management — HTTP API routes (framework-free simulation)., Campus Task Management — data layer (in-memory repositories). A small realistic…, In-memory persistence for Task entities., Task, TaskRepository, InvalidTaskError (+21 more)

### Community 6 - "get_settings"
Cohesion: 0.08
Nodes (26): ABC, AsyncClient, get_settings(), Application configuration via environment variables with .env support., Settings, create_provider(), get_provider(), LLMProvider (+18 more)

### Community 7 - "devDependencies"
Cohesion: 0.05
Nodes (36): eslint, @eslint/js, eslint-plugin-react-hooks, dependencies, react, react-dom, react-router-dom, devDependencies (+28 more)

### Community 8 - "get_retriever"
Cohesion: 0.11
Nodes (20): EvidenceCitation, ContextEngine, detect_query_intent(), Context engine: turn a user query into a bounded, evidence-rich LLM context.…, Find the best line window matching the query inside file content., _relevant_line_window(), HybridRetriever, FileEntry (+12 more)

### Community 9 - "Store"
Cohesion: 0.09
Nodes (9): Conversation, AgentRun, Any, FileEntry, Repository, Symbol, Thread-local SQLite store. All project data lives in one DB file., Store (+1 more)

### Community 10 - "MCPServer"
Cohesion: 0.11
Nodes (16): MCPClient, Minimal stdio MCP client for tool discovery and invocation., MCPServer, Any, CodeForge MCP server — exposes CodeForge repository tools over the Model…, Line-delimited JSON-RPC over stdin/stdout (MCP stdio transport)., serve_stdio(), asyncio (+8 more)

### Community 11 - "ast_parser.py"
Cohesion: 0.17
Nodes (23): _attr_name(), _extract_python_ast(), extract_symbols(), _extract_tree_sitter(), _get_parser(), _import_name_for_node(), _kind_from_node_type(), _name_for_node() (+15 more)

### Community 12 - "compilerOptions"
Cohesion: 0.10
Nodes (19): compilerOptions, isolatedModules, jsx, lib, module, moduleResolution, noEmit, noFallthroughCasesInSwitch (+11 more)

### Community 13 - "domain.py"
Cohesion: 0.12
Nodes (23): Confidence, EvaluationCase, EvaluationResult, Message, BaseModel, Domain models shared across the application., RepositoryKind, RepositoryStatus (+15 more)

### Community 14 - "3. The backend — module by module, line counts included"
Cohesion: 0.06
Nodes (35): 10. Documentation set (all committed), 11. Test inventory (64 functions → 71 pytest cases), 12. Infrastructure, 13. Project-local OpenCode skill, 14. Known limitations (honest, documented everywhere), 15. How to experience it in 90 seconds, 1. What CodeForge IS, 2. Repository map — every directory and why it exists (+27 more)

### Community 15 - "test_scanner_secrets.py"
Cohesion: 0.17
Nodes (23): detect_language(), is_config_file(), is_doc_file(), is_manifest_file(), is_source_file(), is_test_file(), Language detection and file classification for repository scanning., _is_ignored() (+15 more)

### Community 16 - "adversarial_wave2.py"
Cohesion: 0.27
Nodes (8): call(), check(), mixed(), one_chat(), Second adversarial wave: concurrency, unicode, size limits, agent internals., call(), main(), End-to-end demonstration against the LIVE backend. Executes the full product…

### Community 17 - "conftest.py"
Cohesion: 0.33
Nodes (8): client(), indexed_repo(), fixture, Path, Shared fixtures: temp repo, store, and FastAPI client., Copy of the sample repo so tests can index/patch without touching the original., sample_repo_copy(), temp_store()

### Community 18 - "indexer.py"
Cohesion: 0.15
Nodes (20): RepositoryScanner, find_secrets(), Secret detection and redaction during indexing. Repository content is…, Return list of (line_number, start_col, end_col, description)., Replace likely secret values with REDACTED, preserving key names. Quoted values…, redact(), Repository, ScanResult (+12 more)

### Community 19 - "final_verify.py"
Cohesion: 0.67
Nodes (3): call(), main(), Final live verification: graph-symbols regression, eval, execution modes.

### Community 20 - "verify_mcp.py"
Cohesion: 0.67
Nodes (3): call_api(), main(), Verify the CodeForge MCP server over real stdio (subprocess round-trip).

### Community 39 - "Components"
Cohesion: 0.11
Nodes (17): 10. Persistence (backend/app/services/store), 1. Indexing pipeline (backend/app/indexing), 2. Hybrid retrieval (backend/app/retrieval), 3. Context engine, 4. Provider abstraction (backend/app/llm), 5. Tool system (backend/app/tools), 6. Agent (backend/app/agent), 7. Test runner (backend/app/services/test_runner) (+9 more)

### Community 40 - "The 10 demo workflows"
Cohesion: 0.12
Nodes (15): 10. Show the agent trace, 1. Explain the architecture, 2. Locate authentication-equivalent functionality, 3. Find the dependency chain, 4. Find the intentional bug, 5. Generate an implementation plan, 6. Produce a diff, 7. Apply the controlled fix (+7 more)

### Community 41 - "CodeForge"
Cohesion: 0.12
Nodes (15): Architecture, CodeForge, Configuration, Demo walkthrough, Docker, Evaluation results (measured, sample_repo benchmark), License, Limitations (+7 more)

### Community 42 - "CodeForge — Interview Guide"
Cohesion: 0.15
Nodes (12): Agent architecture, CodeForge — Interview Guide, Failure handling, Human oversight, Observability, RAG & evidence, Repository indexing & parsing, Retrieval & context (+4 more)

### Community 43 - "BUILD STATUS — CodeForge"
Cohesion: 0.20
Nodes (9): Audit round (2026-09-02) — 8 defects found and fixed, BUILD STATUS — CodeForge, Completion round (2026-09-02), Dead-code cleanup round (2026-09-02), Known limitations, Phases, Post-audit remediation round (2026-09-03), Verification log (completion round) (+1 more)

### Community 44 - "CodeForge — Résumé Notes"
Cohesion: 0.20
Nodes (9): Actual technology stack, Architecture discussion points, CodeForge — Résumé Notes, Five interview talking points, Measured metrics (reproducible), One-line description, Strongest technical capabilities, Three résumé bullet candidates (+1 more)

### Community 45 - "CodeForge — MCP Integration"
Cohesion: 0.22
Nodes (8): Client usage, CodeForge — MCP Integration, Exposed tools, Limitations, Protocol level, Purpose, Running the server, Security considerations

### Community 46 - "CodeForge — Security"
Cohesion: 0.25
Nodes (7): CodeForge — Security, Input boundaries, Reporting, Secret detection patterns, Secret-storage remediation for existing databases, Threat model, What is deliberately NOT protected against

### Community 47 - "[0.1.0] - 2026-09-02"
Cohesion: 0.29
Nodes (6): [0.1.0] - 2026-09-02, [0.1.1] - 2026-09-03 — post-audit remediation, Added, Changelog, Fixed, Fixed during development (regression-protected)

### Community 48 - "Contributing to CodeForge"
Cohesion: 0.29
Nodes (6): Adding a tool, Adding an evaluation case, Commit style, Contributing to CodeForge, Development setup, Ground rules

### Community 49 - "ADR-003: Hybrid retrieval without a vector database"
Cohesion: 0.33
Nodes (5): ADR-003: Hybrid retrieval without a vector database, Amendment (FTS5 removed), Consequences, Context, Decision

### Community 50 - "CodeForge — Evaluation"
Cohesion: 0.33
Nodes (5): CodeForge — Evaluation, Honest notes on the numbers, Measured results (this build), Method, What is NOT measured

### Community 51 - "ADR-001: Modular monolith"
Cohesion: 0.40
Nodes (4): ADR-001: Modular monolith, Consequences, Context, Decision

### Community 52 - "ADR-002: Tree-sitter for structural parsing (with stdlib-ast fallback)"
Cohesion: 0.40
Nodes (4): ADR-002: Tree-sitter for structural parsing (with stdlib-ast fallback), Consequences, Context, Decision

### Community 53 - "ADR-004: Provider abstraction with a deterministic offline mock"
Cohesion: 0.40
Nodes (4): ADR-004: Provider abstraction with a deterministic offline mock, Consequences, Context, Decision

### Community 54 - "ADR-005: Controlled execution, never blind file writes"
Cohesion: 0.40
Nodes (4): ADR-005: Controlled execution, never blind file writes, Consequences, Context, Decision

### Community 55 - "ADR-006: Local-first demo mode as default"
Cohesion: 0.40
Nodes (4): ADR-006: Local-first demo mode as default, Consequences, Context, Decision

### Community 56 - "ADR-007: MCP as the integration layer (tools-first, stdio)"
Cohesion: 0.40
Nodes (4): ADR-007: MCP as the integration layer (tools-first, stdio), Consequences, Context, Decision

### Community 57 - "Campus Task Management (sample_repo)"
Cohesion: 0.40
Nodes (4): Architecture, Campus Task Management (sample_repo), Running tests, The intentional bug

### Community 58 - "CodeForge development skill"
Cohesion: 0.50
Nodes (3): CodeForge development skill, Commands, Rules

## Knowledge Gaps
- **196 isolated node(s):** `codeforge-backend`, `campus-tasks`, `name`, `private`, `version` (+191 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Store` connect `Store` to `registry.py`, `test_agent_api.py`, `main.py`, `get_settings`, `ast_parser.py`, `domain.py`, `test_scanner_secrets.py`, `conftest.py`, `indexer.py`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Why does `ToolContext` connect `registry.py` to `indexer.py`, `MCPServer`, `test_agent_api.py`, `main.py`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Why does `get_logger()` connect `logging.py` to `registry.py`, `test_agent_api.py`, `main.py`, `get_settings`, `ast_parser.py`, `domain.py`, `test_scanner_secrets.py`, `indexer.py`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `Store` (e.g. with `Agent` and `run_evaluation_for_repo()`) actually correct?**
  _`Store` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `ToolContext` (e.g. with `Agent` and `diff()`) actually correct?**
  _`ToolContext` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `build_default_registry()` (e.g. with `apply_patch()` and `create_file()`) actually correct?**
  _`build_default_registry()` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `Agent` (e.g. with `AgentStateMachine` and `LLMProvider`) actually correct?**
  _`Agent` has 16 INFERRED edges - model-reasoned connections that need verification._