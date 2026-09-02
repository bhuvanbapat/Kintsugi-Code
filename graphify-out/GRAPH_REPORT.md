# Graph Report - CodeForge  (2026-09-02)

## Corpus Check
- Corpus is ~33,814 words - fits in a single context window. You may not need a graph.

## Summary
- 629 nodes · 1526 edges · 34 communities (31 shown, 3 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 139 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 32
- Community 33

## God Nodes (most connected - your core abstractions)
1. `Store` - 49 edges
2. `ToolContext` - 38 edges
3. `build_default_registry()` - 35 edges
4. `Agent` - 25 edges
5. `get_store()` - 24 edges
6. `get_settings()` - 23 edges
7. `TaskMode` - 21 edges
8. `get_retriever()` - 21 edges
9. `redact()` - 20 edges
10. `index_repository()` - 20 edges

## Surprising Connections (you probably didn't know these)
- `Agent` --uses--> `LLMProvider`  [INFERRED]
  backend/app/agent/engine.py → backend/app/llm/providers.py
- `Agent` --uses--> `Store`  [INFERRED]
  backend/app/agent/engine.py → backend/app/services/store.py
- `Agent` --uses--> `ToolContext`  [INFERRED]
  backend/app/agent/engine.py → backend/app/tools/registry.py
- `Agent` --uses--> `ToolRegistry`  [INFERRED]
  backend/app/agent/engine.py → backend/app/tools/registry.py
- `chat()` --uses--> `Agent`  [INFERRED]
  backend/app/main.py → backend/app/agent/engine.py

## Import Cycles
- None detected.

## Communities (34 total, 3 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (53): Agent, AgentRun, Any, Controlled engineering agent. State machine (AgentState) with validated…, Deterministic, explainable tool-selection policy., Merge useful tool output into LLM context (bounded)., _summarize(), Product-level agent skills (directive §54). Each TaskMode maps to a SkillSpec:… (+45 more)

### Community 1 - "Community 1"
Cohesion: 0.08
Nodes (41): api, EmptyState(), ErrorBox(), Spinner(), StatRow(), useAsync(), Layout(), NAV (+33 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (32): Conversation, EvaluationCase, EvaluationResult, Repository, get_benchmark(), Evaluation subsystem: benchmark retrieval quality against known answers.…, Curated benchmark against examples/sample_repo., run_evaluation_for_repo() (+24 more)

### Community 3 - "Community 3"
Cohesion: 0.11
Nodes (44): Map a dotted module name (e.g. 'data.repositories') to a repo file. Shared by…, resolve_module_path(), build_repository_map(), Produce a compact structural map used for LLM context and the graph view., TestRunner, apply_patch(), assert_safe_command(), build_default_registry() (+36 more)

### Community 4 - "Community 4"
Cohesion: 0.13
Nodes (48): reset_provider(), apply_patch(), ApplyPatchRequest, benchmark_cases(), chat(), ChatRequest, conversations(), delete_repository() (+40 more)

### Community 5 - "Community 5"
Cohesion: 0.09
Nodes (29): make_app(), Any, Campus Task Management — HTTP API routes (framework-free simulation)., Campus Task Management — data layer (in-memory repositories). A small realistic…, In-memory persistence for Task entities., Task, TaskRepository, InvalidTaskError (+21 more)

### Community 6 - "Community 6"
Cohesion: 0.08
Nodes (25): MCPClient, Minimal stdio MCP client for tool discovery and invocation., MCPServer, Any, CodeForge MCP server — exposes CodeForge repository tools over the Model…, Line-delimited JSON-RPC over stdin/stdout (MCP stdio transport)., serve_stdio(), detect_query_intent() (+17 more)

### Community 7 - "Community 7"
Cohesion: 0.07
Nodes (27): get_logger(), Structured logging that never logs secrets., redact_secrets(), SecretRedactingFilter, load_mcp_config(), MCP client: connect CodeForge to external MCP servers over stdio. Lets the…, Read MCP server configuration from env or mcp_servers.json., clone_repository() (+19 more)

### Community 8 - "Community 8"
Cohesion: 0.12
Nodes (32): detect_language(), is_config_file(), is_doc_file(), is_manifest_file(), is_source_file(), is_test_file(), Language detection and file classification for repository scanning., _is_ignored() (+24 more)

### Community 9 - "Community 9"
Cohesion: 0.05
Nodes (36): eslint, @eslint/js, eslint-plugin-react-hooks, dependencies, react, react-dom, react-router-dom, devDependencies (+28 more)

### Community 10 - "Community 10"
Cohesion: 0.11
Nodes (17): ABC, AsyncClient, get_settings(), Application configuration via environment variables with .env support., Settings, create_provider(), get_provider(), LLMProvider (+9 more)

### Community 11 - "Community 11"
Cohesion: 0.14
Nodes (26): _attr_name(), _extract_python_ast(), extract_symbols(), _extract_tree_sitter(), _get_parser(), _import_name_for_node(), _kind_from_node_type(), _name_for_node() (+18 more)

### Community 12 - "Community 12"
Cohesion: 0.10
Nodes (19): compilerOptions, isolatedModules, jsx, lib, module, moduleResolution, noEmit, noFallthroughCasesInSwitch (+11 more)

### Community 13 - "Community 13"
Cohesion: 0.26
Nodes (6): HybridRetriever, FileEntry, Symbol, Return ranked retrieval result with lexical + symbol evidence., _tokenize(), SearchMode

### Community 14 - "Community 14"
Cohesion: 0.67
Nodes (3): call(), main(), End-to-end demonstration against the LIVE backend. Executes the full product…

### Community 15 - "Community 15"
Cohesion: 0.67
Nodes (3): call(), main(), Final live verification: graph-symbols regression, eval, execution modes.

### Community 16 - "Community 16"
Cohesion: 0.67
Nodes (3): call_api(), main(), Verify the CodeForge MCP server over real stdio (subprocess round-trip).

## Knowledge Gaps
- **46 isolated node(s):** `codeforge-backend`, `campus-tasks`, `name`, `private`, `version` (+41 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Store` connect `Community 2` to `Community 0`, `Community 3`, `Community 4`, `Community 8`, `Community 10`, `Community 11`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Why does `ToolContext` connect `Community 3` to `Community 0`, `Community 2`, `Community 4`, `Community 6`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Why does `Agent` connect `Community 0` to `Community 3`, `Community 10`, `Community 2`, `Community 4`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `Store` (e.g. with `Agent` and `run_evaluation_for_repo()`) actually correct?**
  _`Store` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `ToolContext` (e.g. with `Agent` and `diff()`) actually correct?**
  _`ToolContext` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `build_default_registry()` (e.g. with `apply_patch()` and `create_file()`) actually correct?**
  _`build_default_registry()` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `Agent` (e.g. with `AgentStateMachine` and `LLMProvider`) actually correct?**
  _`Agent` has 16 INFERRED edges - model-reasoned connections that need verification._