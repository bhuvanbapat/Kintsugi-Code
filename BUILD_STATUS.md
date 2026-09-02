# BUILD STATUS — CodeForge

Last updated: 2026-09-02 (completion round) · Overall: **COMPLETE — all systems verified**

## Phases

- [x] Environment inspection (Python 3.13, Node 24, Git 2.55, Docker 29)
- [x] OpenCode skill discovery (graphify skill loaded; relevant skills identified)
- [x] Graphify discovery (v0.9.48 installed system-wide)
- [x] Graphify integration (knowledge graph refreshed post-changes: 629 nodes /
      1526 edges / 34 communities; queries verified against new code)
- [x] Foundation (FastAPI app, config, logging, React/Vite frontend)
- [x] Backend (modular monolith: indexing, retrieval, llm, tools, agent, services, mcp)
- [x] Frontend (12 screens, strict TS, production build)
- [x] Repository scanner (ignore rules, classification, caps — tested)
- [x] AST / tree-sitter (symbols, relationships, byte-offset fix — tested)
- [x] Symbols + repository map (module pseudo-symbols, shared import resolver)
- [x] Retrieval (pure-Python BM25 + symbol + importance — tested; FTS5 removed
      for thread safety, quality unchanged at 8/8)
- [x] AI provider abstraction (OpenAI-compatible + offline mock — tested)
- [x] Mock mode (default, deterministic, evidence-grounded)
- [x] Chat with evidence citations (file:line chips deep-link into explorer)
- [x] Tool registry (17 tools incl. find_path, containment, command policy — tested)
- [x] Agent skill specs (§54: purpose/inputs/tools/workflow/output/failure
      conditions for all 7 modes; engine tool policy derives from specs)
- [x] Agent (state machine validated, bounded loop, trace — tested)
- [x] Test runner (ecosystem detection, output parsing, duration_ms — e2e verified)
- [x] Failure diagnosis (failing tests → context → fix proposal — e2e step 9)
- [x] Diff workflow (apply + validate + auto-rollback — integration tested)
- [x] Git URL import (https-only validation, depth-limited clone — live-verified
      against a real GitHub repo; 10 rejection tests)
- [x] MCP (server: 8 tools incl. find_path, live stdio verification; client; docs)
- [x] Security (threat model, redaction, traversal/injection/command guards — tested)
- [x] Evaluation (8/8 cases, recall 0.875, precision 0.331, documented honestly)
- [x] Observability (per-tool timings, run traces, usage reporting)
- [x] Docker (backend + frontend images, compose; sqlite on mounted volume)
- [x] CI (GitHub Actions: mypy + pytest + evaluation + eslint + tsc + build)
- [x] Documentation (README, ARCHITECTURE, SECURITY, EVALUATION, MCP, DEMO,
      RESUME_NOTES, INTERVIEW_GUIDE, CONTRIBUTING, CHANGELOG, 7 ADRs — all
      FTS5/16-tool stale references corrected)
- [x] Git repository initialized, clean history, no artifacts/secrets
- [x] Final QA (full 16-step e2e demo ALL PASS; 53/53 backend tests;
      mypy/ruff/eslint/tsc clean; all verification scripts green)

## Dead-code cleanup round (2026-09-02)

Swept the entire codebase; removed: unused `PlannedChange`/`TestResult`
models, `_PythonFallbackParser` (dead), `_ts_available` flag,
`extract_symbols_async` wrapper, `asyncio_wait_for` class hack (now plain
asyncio), unused `store_file_content`, no-op tool-filter line, duplicate
module-resolver (consolidated into `indexing/language.resolve_module_path`),
4 unused frontend API wrappers, leftover imports/vars in tests+scripts.
Fixed real bug found during sweep: SQLite default path resolved to
`backend/app/` instead of `backend/` (config.py parents index).

## Audit round (2026-09-02) — 8 defects found and fixed

1. `/api/graph kind=symbols` returned None (missing return) — restored,
   regression-tested, live-verified (23 nodes / 22 edges).
2. FTS5 thread-affinity crash in `/api/evaluation/run` — FTS layer removed,
   BM25 single path, benchmark unchanged (ADR-003 amended).
3. `write_file` tool falsely claimed `wrote: True` — now reports `proposed`.
4. Git URL import (§27B) missing — implemented + live-verified.
5. eslint was a fake script — installed, 4 real errors fixed, enforced in CI.
6. mypy never run — 6 type errors fixed (incl. #1), enforced in CI.
7. ExecutionMode not selectable in UI — added, live-verified.
8. Docker volume unused, render-phase setState ×3, "17 tools" claim — fixed.

## Completion round (2026-09-02)

- Product skill architecture (§54): `app/agent/skills.py` — SkillSpec for all
  7 task modes (purpose, inputs, tools, workflow, output, failure conditions);
  engine MODE_TOOLS now derives from specs; spec-completeness tested.
- `find_path` tool (§47): BFS shortest import chain between files, exposed in
  tools + MCP + skills; verified on sample repo (routes→repositories = 1 hop,
  correct), unreachable and invalid-input cases tested.
- TestRunner now reports real `duration_ms` (§38).
- FIX-mode workflow extended (tests → read failing code → diff context).
- Graphify graph refreshed post-change (629 nodes); query verified.
- All stale FTS5/16-tool doc references corrected; ADR-003 amended honestly.

## Verification log (completion round)

| Check | Result |
|---|---|
| Backend pytest | 53 passed |
| mypy | 0 errors in 34 source files |
| ruff (app+tests+scripts) | All checks passed |
| Evaluation benchmark | 8/8, mean recall 0.875 |
| E2E demo (live API, 16 steps) | ALL PASS |
| MCP stdio round-trip (8 tools) | ALL PASS |
| Final live verification (graph/eval/modes/git-url) | ALL PASS |
| Frontend eslint / tsc / build | 0 / 0 / success |
| Graphify graph freshness | refreshed; queries return new symbols |
| Git commit artifact scan | 0 db/venv/node_modules files, 0 secrets |
| Sample repo pytest | 6 passed, 1 failed (intentional — by design) |

## Known limitations

Documented in README (AST depth for Python/JS/TS only; templated mock
answers; heuristic import resolution; deterministic graph layout; no API auth
— local-first tool).
