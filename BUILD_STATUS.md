# BUILD STATUS — CodeForge

Last updated: 2026-09-02 (post dead-code cleanup round) · Overall: **COMPLETE — all systems verified**

## Phases

- [x] Environment inspection (Python 3.13, Node 24, Git 2.55, Docker 29)
- [x] OpenCode skill discovery (graphify skill loaded; relevant skills identified)
- [x] Graphify discovery (v0.9.48 installed system-wide)
- [x] Graphify integration (knowledge graph built: 597 nodes / 1467 edges / 34 communities)
- [x] Foundation (FastAPI app, config, logging, React/Vite frontend)
- [x] Backend (modular monolith: indexing, retrieval, llm, tools, agent, services, mcp)
- [x] Frontend (12 screens, strict TS, production build)
- [x] Repository scanner (ignore rules, classification, caps — tested)
- [x] AST / tree-sitter (symbols, relationships, byte-offset fix — tested)
- [x] Symbols + repository map (module pseudo-symbols, shared import resolver)
- [x] Retrieval (FTS5 + BM25 fallback + symbol + importance — tested)
- [x] AI provider abstraction (OpenAI-compatible + offline mock — tested)
- [x] Mock mode (default, deterministic, evidence-grounded)
- [x] Chat with evidence citations (file:line chips deep-link into explorer)
- [x] Tool registry (17 tools, containment, command policy — tested)
- [x] Agent (state machine validated, bounded loop, trace — tested)
- [x] Test runner (ecosystem detection, output parsing — e2e verified)
- [x] Failure diagnosis (failing tests → context → fix proposal — e2e step 9)
- [x] Diff workflow (apply + validate + auto-rollback — integration tested)
- [x] MCP (server: 7 tools, live stdio verification; client; docs)
- [x] Security (threat model, redaction, traversal/injection/command guards — tested)
- [x] Evaluation (8/8 cases, recall 0.875, precision 0.331, documented honestly)
- [x] Observability (per-tool timings, run traces, usage reporting)
- [x] Docker (backend + frontend images, compose)
- [x] CI (GitHub Actions: pytest + evaluation + tsc + build)
- [x] Documentation (README, ARCHITECTURE, SECURITY, EVALUATION, MCP, DEMO,
      RESUME_NOTES, INTERVIEW_GUIDE, CONTRIBUTING, CHANGELOG, 7 ADRs)
- [x] Git repository initialized, clean initial commit (no artifacts/secrets)
- [x] Final QA (full 16-step e2e demo ALL PASS; 34/34 backend tests;
      frontend typecheck+build clean; all 12 routes HTTP 200; proxy OK)

## Dead-code cleanup round (2026-09-02)

Swept the entire codebase; removed: unused `PlannedChange`/`TestResult`
models, `_PythonFallbackParser` (dead), `_ts_available` flag,
`extract_symbols_async` wrapper, `asyncio_wait_for` class hack (now plain
asyncio), unused `store_file_content`, no-op tool-filter line, duplicate
module-resolver (consolidated into `indexing/language.resolve_module_path`),
4 unused frontend API wrappers, leftover imports/vars in tests+scripts.
Fixed real bug found during sweep: SQLite default path resolved to
`backend/app/` instead of `backend/` (config.py parents index).

## Verification log (post-cleanup run)

| Check | Result |
|---|---|
| Backend pytest | 34 passed |
| Ruff (app + tests + scripts) | All checks passed |
| Dead-code scan | 0 candidates remaining |
| Evaluation benchmark | 8/8, mean recall 0.875 |
| E2E demo (live API, 16 steps) | ALL PASS |
| MCP stdio round-trip (subprocess) | ALL PASS |
| Frontend `tsc -b --noEmit` | 0 errors |
| Frontend `vite build` | success |
| Evaluation via live API (`/api/evaluation/run`) | 200, 8/8 |
| Git commit artifact scan | 0 db/venv/node_modules files, 0 secrets |
| Sample repo pytest | 6 passed, 1 failed (intentional — by design) |

## Known limitations

Documented in README (AST depth for Python/JS/TS only; templated mock
answers; heuristic import resolution; deterministic graph layout; no API auth
— local-first tool).
