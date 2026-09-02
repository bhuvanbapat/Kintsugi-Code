# CodeForge

An AI-assisted software engineering workspace: a repository-aware coding agent
that indexes code structurally, answers questions with file:line evidence,
runs tests, proposes diffs, and applies validated fixes — with a full agent
trace for every run.

**Not** a chatbot wrapper. Every answer is grounded in retrieval over the
actual indexed repository; every code change is diffed, tested, and rolled
back automatically if tests break.

## What it does

| Capability | How it works |
|---|---|
| Repository indexing | Recursive scan → language detection → tree-sitter AST → symbols + relationships in SQLite |
| Hybrid retrieval | Lexical (FTS5/BM25-style) + structural symbol search + file-importance ranking |
| Evidence-backed answers | Every response cites `path:line`; confidence marked confirmed/inferred/uncertain |
| Controlled agent loop | Bounded iterations, validated state machine, per-mode tool policy, loop detection |
| Safe code modification | Diff → apply → test → **automatic rollback** if tests fail |
| Test runner | Detects pytest/npm/go/cargo/maven/gradle; captures exit code, stdout, parse failures |
| Failure diagnosis | Failing tests → retrieve related code → diagnose → propose fix |
| Evaluation | 8-case benchmark measuring real retrieval recall/precision/latency |
| MCP integration | CodeForge is both an MCP server (expose tools) and client (consume tools) |
| Observability | Per-tool timings, per-run trace viewer, token usage when provider reports it |

## Architecture

```
frontend/  React 18 + TypeScript + Vite — 12 screens (workspace, explorer,
          search, symbols, graph, tests, diff, trace, evaluation, settings)
backend/   FastAPI + Pydantic — modular monolith
  app/indexing/     scanner, language detection, AST parser, secret redaction
  app/retrieval/    hybrid retriever, context engine (token budgeting)
  app/llm/          provider abstraction: OpenAI-compatible + deterministic mock
  app/tools/        tool registry with path containment + command policy
  app/agent/        state machine + controlled loop
  app/mcp/          MCP stdio server + client
  app/services/     store (SQLite), indexer, test runner, evaluator, RAG cache
examples/sample_repo/  Campus Task Management demo app (intentional bug)
```

See `docs/ARCHITECTURE.md` for the full picture and `graphify-out/graph.html`
for the generated code knowledge graph of this codebase itself.

## Quick start

```bash
# backend
cd backend
python -m venv .venv
.venv\Scripts\pip install fastapi "uvicorn[standard]" pydantic pydantic-settings httpx tree-sitter tree-sitter-language-pack pytest pytest-asyncio
.venv\Scripts\python -m uvicorn app.main:app --port 8000

# frontend (new terminal)
cd frontend
npm install
npm run dev          # http://localhost:5173
```

**Demo mode is the default**: no API key, no network, deterministic answers
composed from retrieval evidence. To use a real model, copy `.env.example` to
`backend/.env` or configure in Settings (see below).

### Demo walkthrough

1. Open http://localhost:5173 → Repositories
2. Import: `<project>\examples\sample_repo` → it scans and indexes
3. AI Workspace → *"Where is complete_task defined?"* (mode: locate) → answer + evidence chips that open the file at the line
4. Tests → Run → 6 passed, 1 failed (`test_complete_todo_task_fails` — the intentional bug)
5. Diff page → paste the fix (see `docs/DEMO.md`) → Apply → tests run → 7 passed, diff shown
6. Agent Trace → every tool call with durations
7. Evaluation → 8/8 benchmark cases with real recall/precision

`docs/DEMO.md` contains the complete scripted demo including the API-level
reproduction of all steps.

## Configuration

Environment variables (prefix `CODEFORGE_`, see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `CODEFORGE_LLM_PROVIDER` | `mock` | `mock` (offline) or `openai` (any OpenAI-compatible endpoint) |
| `CODEFORGE_LLM_BASE_URL` | `https://api.openai.com/v1` | works with Ollama/vLLM/LM Studio too |
| `CODEFORGE_LLM_MODEL` | `gpt-4o-mini` | model name |
| `CODEFORGE_LLM_API_KEY` | *(empty)* | never logged, never committed |
| `CODEFORGE_CONTEXT_BUDGET_TOKENS` | `8000` | context engine budget |
| `CODEFORGE_AGENT_MAX_ITERATIONS` | `12` | agent loop bound |

## Testing

```bash
cd backend && .venv\Scripts\python -m pytest tests -q   # 34 tests
cd examples\sample_repo && python -m pytest -q          # 6 pass, 1 fail (intentional)
cd frontend && npx tsc -b --noEmit && npm run build       # typecheck + build
```

Full end-to-end: `python scripts/e2e_demo.py` (16-step verified workflow
against the live backend).

## Security posture

- Repositories are **untrusted input**: scanning never executes repo code;
  git/test commands come from an allow-list; subprocesses have timeouts and
  output caps.
- Path containment: every file access is resolved and checked against the
  repository root — traversal is rejected (tested).
- Secret redaction: API keys/passwords/private keys in indexed content are
  replaced with `[REDACTED_SECRET]` before storage/retrieval (tested); logs
  pass through a redacting filter.
- Prompt injection: repository content is data, never instructions; the agent
  composes answers from structured retrieval output, not raw repo text.
- Dangerous-command policy blocks `rm -rf`, curl|sh, fork bombs (tested).

See `docs/SECURITY.md` for the threat model.

## Evaluation results (measured, sample_repo benchmark)

8/8 cases passed — mean recall 0.875, mean precision 0.331, sub-millisecond
in-process retrieval latency. Case-level results are reproducible via the
Evaluation page or `backend/scripts/run_evaluation.py`. Nothing is simulated.

## MCP

CodeForge speaks MCP over stdio (JSON-RPC 2.0): run
`python -m app.mcp.server` in `backend/` and any MCP client can call
`search_code`, `get_symbol`, `get_repository_map`, `get_dependencies`,
`list_files`, `read_file`. Verified end-to-end in `scripts/verify_mcp.py`.
An MCP client is also included for consuming external MCP servers. Details:
`docs/MCP.md`.

## Docker

```bash
docker compose up --build
```

## Repository layout

```
backend/    FastAPI app + tests (34 passing)
frontend/   React + TS (12 screens)
examples/sample_repo/   demo app with intentional bug + failing test
docs/       ARCHITECTURE, SECURITY, EVALUATION, MCP, DEMO, ADRs, interview guide
scripts/    e2e_demo.py, verify_mcp.py, run_evaluation.py
graphify-out/  knowledge graph of this codebase (graph.html, GRAPH_REPORT.md)
.github/workflows/  CI (tests + typecheck on push)
```

## Limitations

- AST extraction is deepest for Python/JS/TS; other languages get lexical-only retrieval.
- Mock provider answers are template-composed from retrieval evidence (honest, deterministic, but not prose-fluent); connect an OpenAI-compatible endpoint for natural answers.
- Import→file resolution is heuristic (dotted path matching); dynamic imports are not tracked.
- The graph view is a deterministic layered layout, not force-directed — correctness over visual complexity.
- Single-user, local-first; no auth on the API (run locally, don't expose).

## Roadmap

- Semantic (embedding) retrieval tier behind the same hybrid interface
- Call-graph extraction (currently imports + containment only)
- Multi-file patches with dependency-aware validation
- Real-time collaborative trace viewing

## License

MIT — see `LICENSE`.
