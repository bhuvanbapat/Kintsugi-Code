# Kintsugi-Code — The Complete Project Reference

> Every inch of what this repository is, what was built, how it works, where
> every line lives, what is verified, and what it honestly cannot do.
> This document is generated from the actual repository state — every number,
> count, and claim below is measured, not estimated.

---

## 1. What Kintsugi-Code IS

**Kintsugi-Code** is an **AI-assisted software engineering workspace** — a local-first
developer tool that:

1. **Indexes a repository structurally** (real AST parsing, not regex)
2. **Answers questions about the codebase with evidence** — every answer cites `file:line`, every citation is clickable and opens the source at that line
3. **Runs the repository's tests** and parses results
4. **Diagnoses failures** by connecting test output to the code that caused it
5. **Proposes and applies controlled code changes** — diff generated, tests run, and if tests break, the change is *automatically rolled back*
6. **Records everything** — every tool call, every duration, every state transition, in an inspectable agent trace

It is explicitly **not**: a chatbot wrapper, a generic dashboard, a
multi-agent demo, or a "ChatGPT over a folder". The AI layer sits at the end
of a pipeline (scan → AST → index → retrieve → budget → answer); every answer
is composed from structured retrieval evidence, and the offline mock provider
*cannot invent repository facts* because it only formats what retrieval found.

### The core product loop

```
REPOSITORY → SCAN → STRUCTURAL ANALYSIS → INDEX → RETRIEVE → REASON
     → TOOL USE → PLAN → PROPOSE → PATCH → TEST → DIAGNOSE → ITERATE → REVIEW → RESULT
```

Every arrow above is a real, inspectable subsystem documented in this file.

### Design stance (worth stating first)

- **Controlled over autonomous**: the agent never silently writes files. Tools propose diffs; only the `/api/diff/apply` endpoint writes, and it writes *with test validation and auto-rollback*. Execution modes (analysis-only vs controlled execution) are user-selectable in the UI.
- **Evidence or silence**: answers carry citations with a confidence label (`confirmed_from_code` / `inference` / `uncertain`); retrieval misses are stated, not papered over.
- **Honest demo mode**: the default provider is a deterministic offline mock that composes answers from retrieval output — no API key, no network, no fabricated content.
- **Correctness over visual complexity**: e.g., the dependency graph uses a deterministic layered layout instead of a physics simulation that collapses on real repos.

---

## 2. Repository map — every directory and why it exists

```
Kintsugi-Code/
├── backend/                    Python FastAPI application (the engine)
│   ├── app/
│   │   ├── main.py             All 25 HTTP routes / 23 paths (§4)
│   │   ├── core/               config (env-driven settings), logging (secret-redacting)
│   │   ├── models/             domain.py — every Pydantic model in one file
│   │   ├── indexing/           scanner, language detection, AST parser, secrets
│   │   ├── retrieval/          hybrid retriever, context engine
│   │   ├── llm/               provider abstraction + mock + OpenAI-compatible
│   │   ├── tools/              17-tool registry with security guards
│   │   ├── agent/              engine loop, state machine, skill specs
│   │   ├── services/           store (SQLite), indexer, test runner, evaluator,
│   │   │                       git_import, rag_service (retriever cache)
│   │   ├── mcp/                MCP stdio server + client
│   │   └── api/                (package placeholder for future route splitting)
│   ├── tests/                  64 test functions across 9 files (§11)
│   ├── scripts/run_evaluation.py   benchmark runner (CI uses it too)
│   ├── Dockerfile              python:3.12-slim + uvicorn
│   └── pyproject.toml          deps + ruff/mypy/pytest config
├── frontend/                   React 18 + TypeScript + Vite SPA
│   ├── src/api/client.ts       typed API client — the ONLY fetch boundary
│   ├── src/types/index.ts      all shared TS interfaces
│   ├── src/components/         Layout (nav shell), common (Spinner/ErrorBox/
│   │                           EmptyState/useAsync/StatRow)
│   ├── src/pages/              12 screens (§6)
│   ├── src/styles.css          GitHub-dark-inspired design tokens
│   ├── Dockerfile              node:20 build → nginx:alpine serve
│   ├── nginx.conf              SPA routing + /api proxy to backend
│   ├── eslint.config.js        typescript-eslint + react-hooks (strict)
│   └── vite.config.ts          dev proxy /api → :8000
├── examples/sample_repo/       Campus Task Management demo app (§7)
├── docs/                       ARCHITECTURE, SECURITY, EVALUATION, MCP, DEMO,
│   ├── adr/                    RESUME_NOTES, INTERVIEW_GUIDE + 7 ADRs (§10)
├── scripts/                    e2e_demo, verify_mcp, final_verify,
│                               adversarial_api, adversarial_wave2, refresh_graph
├── graphify-out/               knowledge graph of Kintsugi-Code itself (§9)
├── .github/workflows/ci.yml    CI: mypy→pytest→eval→eslint→tsc→build (§12)
├── .opencode/skills/Kintsugi-Code-dev/SKILL.md   project-local dev skill (§13)
├── docker-compose.yml          backend+frontend, named volume for SQLite
├── .env.example                every configuration variable documented
├── README.md / CHANGELOG.md / CONTRIBUTING.md / LICENSE / BUILD_STATUS.md
└── PROJECT_REFERENCE.md        ← this file
```

**Measured size** (post-audit remediation round): 119 tracked files · ~5,132
lines of backend Python (4,271 application + 861 test) · ~2,378 lines of
frontend TypeScript/CSS · ~2,155 lines of markdown documentation · 9 commits,
no artifacts or secrets.

---

## 3. The backend — module by module, line counts included

### 3.1 `core/config.py` (65 lines) — configuration
- `pydantic-settings` BaseSettings, every variable prefixed `Kintsugi-Code_`, loaded from `backend/.env` if present.
- Defaults chosen so **nothing is required to run**: provider=mock, SQLite in `backend/`, bounded timeouts everywhere.
- Holds all safety limits in one place: max file size (2 MB), max repo files (20k), agent iterations (12), tool timeout (60 s), command timeout (300 s), output cap (200 KB), context budget (8k tokens), retrieval candidates (50).
- `get_settings()` is a cached singleton; tests can reset it.

### 3.2 `core/logging.py` — leak-proof logging
- Redaction runs at **LogRecord creation** via a global record factory (plus root/uvicorn logger filters as defense in depth) and scrubs OpenAI keys / GitHub PATs / generic `secret=...` patterns from messages, log arguments, and **exception/traceback text** across all logging paths — application loggers, root-level calls, and uvicorn's server loggers alike.

### 3.3 `models/domain.py` (228 lines) — the entire data model
One file, zero hidden state. The important models:

| Model | What it is |
|---|---|
| `Repository` | id, name, root_path, kind (local/git_url), status (registered→scanning→indexed→failed), scan_stats |
| `FileEntry` | path, language, size, line_count, and 5 classification flags (is_test/doc/config/manifest/source), sha256 |
| `Symbol` | id, name, kind (function/class/method/import/module), file_path, start/end line, parent, language, signature |
| `Relationship` | source, target, kind (imports/contains/calls), metadata |
| `AgentRun` | the full trace: task, mode, state, iterations, result, evidence[], tool_calls[], usage{} |
| `ToolCallRecord` | tool name, arguments, result summary, error, duration_ms |
| `EvidenceCitation` | file_path, line range, confidence enum |
| `Conversation` / `Message` | chat history with per-message evidence |
| `EvaluationCase` / `EvaluationResult` | benchmark definition + measured recall/precision/latency |

Enums that matter: `AgentState` (11 states), `TaskMode` (explain/locate/analyze/plan/test/fix/review), `ExecutionMode` (analysis_only / plan_only / review_required / controlled_execution), `Confidence` (confirmed_from_code / inference / uncertain).

### 3.4 `indexing/language.py` (114 lines) — classification
- Extension→language map (25 languages), `AST_LANGUAGES = {python, javascript, typescript}`.
- `is_test_file` (path *and* name markers), `is_doc_file`, `is_config_file`, `is_manifest_file`, `is_source_file`.
- **`resolve_module_path`** — the shared dotted-module→file resolver (e.g. `data.repositories` → `data/repositories.py`), used by the repo map, the graph API, and the `find_path` tool so all three resolve imports identically. (This was a duplicate function until the dead-code round consolidated it.)

### 3.5 `indexing/scanner.py` (183 lines) — the untrusted-input gate
- `normalize_repo_path`: resolves, validates existence, refuses non-directories.
- Ignore engine: 30+ vendored/build dirs (node_modules, .git, __pycache__, dist, target, venv…), 40+ binary extensions, secret-shaped filenames (id_rsa, *.pem, .env files).
- `os.walk(followlinks=False)` — **symlink escapes are impossible**.
- Size cap per file, file-count cap per repo (truncation is logged, never fatal).
- Binary sniff: NUL byte in first 4 KB → skipped as text.
- Output: `ScanResult` with per-language counts, per-file classification, ignored/parse-error tallies, sha256 per file.

### 3.6 `indexing/secrets.py` — redaction before storage
- 8 conservative regex families: OpenAI-style keys, GitHub PATs/OAuth, Slack tokens, AWS access-key IDs, private-key blocks, password/credential assignments.
- `find_secrets` → list of (line, span, description) findings (counted per repo, surfaced in scan stats).
- `redact` → replaces values with `[REDACTED_SECRET]` **preserving key names** (`API_KEY=[REDACTED_SECRET]`) so code stays readable. Quoted values redact to a **syntactically valid string literal** (`password = "[REDACTED_SECRET]"`) so the redacted source remains parseable. Applied at ingestion to every file **before it enters storage** — and therefore before retrieval, tool output, or LLM context. FileEntry sha256 hashes the ORIGINAL content (scanner path), so file identity stays verifiable against disk.

### 3.7 `indexing/ast_parser.py` (279 lines) — real structural parsing
- **Primary: tree-sitter** via `tree_sitter_language_pack` for Python/JS/TS.
- Walks the parse tree: `function_definition/class_definition/method_definition/import_statement` → `Symbol` rows; containment edges (file→symbol, class→method); import edges.
- **The byte-offset discipline** (a bug we shipped and fixed): tree-sitter spans are *byte* offsets; every slice goes through `source.encode("utf-8")` first. The original string-slicing version mis-named every symbol after the first non-ASCII character in a file.
- **Imports are not identifier nodes** — they're built from statement text, and each imported module becomes a synthetic `module:<name>` symbol so import edges survive persistence and can later resolve to files.
- **Fallback**: pure stdlib-`ast` extraction for Python (full parity: functions, classes, methods, imports, inheritance edges) so symbol extraction works even without tree-sitter wheels.
- `extract_symbols` **never raises** — a file that fails parse is counted and skipped.
- `_signature_line`: first source line of a definition, trimmed to 300 chars, redacted.

### 3.8 `retrieval/hybrid.py` (197 lines) — three-tier search
- **Tier 1 — lexical**: pure-Python **BM25** (k1=1.5, b=0.75) over an in-memory token index built once per repository. *History:* originally SQLite FTS5-primary with BM25 fallback; the FTS connection was thread-affine and crashed `/api/evaluation/run` under FastAPI's thread pool — FTS was removed entirely, BM25 promoted to the single path, and the benchmark re-run confirmed identical quality (8/8, recall 0.875). ADR-003 documents the amendment.
- **Tier 2 — structural**: rarity-weighted symbol-name matching. Exact match 50 pts; substring hits scaled by name length; every token weighted by `8 / (1 + df/10)` so **rare tokens dominate**; 26-stopword list; classes/functions boosted. *This scoring exists because the benchmark caught `Task` out-ranking `validate_priority`* — the fix was measured before/after (case sym-2: FAIL → PASS).
- **Tier 3 — file priors**: manifests +5, tests −2, entrypoint-ish names +1.5.
- Fusion: lexical score + symbol-evidence bonus + importance prior → ranked files. Modes: `lexical`, `symbol`, `hybrid`; optional file glob filter, kind filter, test inclusion.

### 3.9 `retrieval/context_engine.py` (114 lines) — the budget keeper
- `detect_query_intent`: keyword-based classify into locate/analyze/plan/explain.
- `build_context`: hybrid search → **structural expansion** (files defining top symbols get included whole) → for the rest, **best-line windowing** (±12 lines around the densest query-token match, +0.5 for definition lines) → hard **token budget** (chars÷4), trimming the *last* file rather than dropping it silently.
- Output: query, intent, citations[] (with confidence), files[{path, lines, snippet}], retrieval_stats (lexical hits, symbol hits, files included, estimated tokens).
- The whole-repo-to-LLM anti-pattern is structurally impossible here: nothing enters a prompt that didn't come through this budget.

### 3.10 `llm/providers.py` (200 lines) — provider abstraction
- `LLMProvider` interface: `complete(system, prompt, context)` → `LLMResponse`.
- **`OpenAIProvider`**: plain httpx against any OpenAI-compatible `/chat/completions` (OpenAI, Ollama, vLLM, LM Studio). Bearer header only if a key is set. Token usage surfaced when the provider reports it.
- **`MockProvider`** (the default): composes answers **from the retrieval context passed in** — LOCATED/ANALYSIS/PLAN header per task mode, top matching files with line ranges, key definitions regex-extracted from the top snippet, EVIDENCE block, and an explicit `CONFIDENCE: confirmed_from_code` label. It cannot invent files: its entire input is structured retrieval output.
- Usage honesty: `usage_available=False` → the UI shows "unavailable". Estimates are labeled as estimates. Nothing fabricated.

### 3.11 `tools/registry.py` (460 lines) — the 17 tools and their cage
| # | Tool | Kind | What it does |
|---|---|---|---|
| 1 | `read_file` | read | line-range file read (redacted, binary-safe) |
| 2 | `list_files` | read | indexed inventory w/ filters |
| 3 | `search_code` | read | hybrid/lexical search |
| 4 | `search_symbols` | read | structural symbol search |
| 5 | `get_symbol` | read | symbol lookup + redacted snippet |
| 6 | `get_repository_map` | read | files→symbols structural map |
| 7 | `get_dependencies` | read | resolved import edges |
| 8 | `find_path` | read | **BFS shortest import chain between two files** (§ directive 47) |
| 9 | `get_git_status` | read | porcelain status |
| 10 | `get_git_diff` | read | staged/unstaged diff (redacted, truncated) |
| 11 | `get_git_history` | read | oneline log |
| 12 | `run_tests` | exec | ecosystem-detected test run (§3.13) |
| 13 | `run_static_check` | exec | detected lint command |
| 14 | `inspect_project_config` | read | project type + commands |
| 15 | `apply_patch` | **modify** | returns the diff a change *would* make (`proposed: true`) — does not write |
| 16 | `write_file` | **modify** | same proposal semantics |
| 17 | `create_file` | **modify** | same, refuses existing files |

**The cage (all unit-tested):**
- `ToolContext.resolve_in_repo`: every path resolved then `relative_to(root)`-checked → traversal raises; **root itself and directories are rejected** (the adversarial round found the directory-read crash).
- `assert_safe_command`: regex policy blocks `rm -rf`, `del /s`, `format`, `mkfs`, fork bombs, `curl|sh` patterns — **enforced at the subprocess execution boundary** (`_run_command`, `TestRunner.run`, `TestRunner.static_check`).
- `_run_command`: `shell=False` always, timeout, output truncation, **redaction on captured output**.
- `_sanitize_error`: host filesystem paths replaced with `<repo>` in every tool error (info-disclosure fix).
- Modification tools are double-gated: by TaskMode allow-lists **and** ExecutionMode.

### 3.12 `agent/` (471 lines) — the controlled loop
**`state_machine.py` (43 lines)**: 11-state machine with an explicit transition table; invalid transitions raise (tested). Terminal states accept nothing.

**`skills.py` (151 lines)** — the product skill architecture (§54 of the build directive): a frozen `SkillSpec` per TaskMode — name (repository-analysis, symbol-location, failure-analysis, implementation-planning, test-analysis, bug-fixing, code-review), purpose, inputs, allowed_tools, workflow steps, expected output, failure conditions. **The engine's tool policy is derived from these specs** (`MODE_TOOLS = {mode: set(spec.allowed_tools)}`), so the documented skill *is* the executable policy — tests assert they can't drift.

**`engine.py` (277 lines)**: the loop —
```
IDLE→ANALYZING→RETRIEVING→PLANNING→[EXECUTING⇄TESTING/DIAGNOSING]→…→COMPLETED/FAILED
```
- Retrieval once per run via ContextEngine (evidence collected).
- **Deterministic tool selection per mode** (iteration 1: run_tests for TEST/FIX, get_git_diff for REVIEW, search_symbols for LOCATE, map otherwise; later iterations fill gaps: read the top failing file, capture diff context).
- Loop protection: max iterations (12 default), repeated-identical-call detection, no-progress counter (2 repeats or 3 consecutive failures stop the run with a reason), per-tool asyncio timeout.
- FIX mode (analysis-only) produces diagnosis + proposal; only `/api/diff/apply` (§4) ever writes.
- Every call recorded as ToolCallRecord (name, args, summary, error, duration_ms) into the run; runs persisted for the trace viewer.

### 3.13 `services/` — persistence, execution, measurement
**`store.py` (319 lines)**: single SQLite file, WAL mode, thread-local connections. Tables: repositories, files, symbols, relationships, file_docs (redacted content), runs, conversations, kv. All payloads are serialized Pydantic models. Idempotent replace-per-repo operations. (`kv` stores runtime settings overrides + evaluation results.)

**`indexer.py` (147 lines)**: the pipeline — scan → classify → redact → AST-extract (per-file, error-isolated) → persist all four tables → build scan_stats (including symbols/relationships counts and secret-flagged files). `build_repository_map` produces the compact file→symbols map used by agents and the UI.

**`test_runner.py` (177 lines)**: `detect_project_type` from manifests — pyproject/setup/requirements→pytest, package.json→npm/pnpm/yarn scripts, go.mod, Cargo.toml, pom.xml, build.gradle. Runs the detected command (timeout, redaction, truncation), parses **passed/failed/errors/skipped + failed test names** from pytest and JS/go/rust/maven formats, reports real `duration_ms`.

**`evaluator.py` (102 lines)**: 8 curated benchmark cases (architecture, 2× symbol location, dependency lookup, bug finding, relevant-file, planning, test diagnosis) with expected files/symbols; computes **recall** (hits@top-10 / expected), **precision**, **latency**, pass rule = recall ≥ 0.5 ∧ all expected symbols found. Persists per-run results.

**`git_import.py` (63 lines)**: §27B — https-only URL regex (rejects ssh://, scp-syntax, file://, plain http, traversal, metacharacters), depth-50 single-branch clone, 300 s timeout, deterministic cache dir per URL.

**`rag_service.py` (38 lines)**: process-level retriever cache; `build_retriever` wires store→files/symbols/redacted-content; invalidation on re-index.

### 3.14 `mcp/` (320 lines) — Model Context Protocol, both directions
**`server.py` (225 lines)**: stdio transport, JSON-RPC 2.0, MCP 2024-11-05 core — `initialize`, `tools/list`, `tools/call`, `ping`. Exposes 8 tools (search_code, get_symbol, get_repository_map, get_dependencies, find_path, list_files, read_file + set_repository). MCP calls flow through the **same registry cage** (containment, redaction, caps). No mutation tools exposed.

**`client.py` (95 lines)**: spawns any external MCP server (stdio), initialize → list_tools → call_tool with a send lock; `load_mcp_config()` reads optional `mcp_servers.json`.

### 3.15 `main.py` — the API surface

25 method-level routes across 23 unique paths (two paths carry two methods:
`/api/settings` GET+POST, `/api/repositories/{id}` GET+DELETE).
| Endpoint | Method | Purpose |
|---|---|---|
| `/api/health` | GET | liveness + provider/model |
| `/api/settings` | GET/POST | read/update runtime config (key masked, never echoed) |
| `/api/repositories/import` | POST | local path **or https git_url** (clone+register) |
| `/api/repositories` | GET | list |
| `/api/repositories/{id}` | GET/DELETE | fetch / remove (cascades index) |
| `/api/index` | POST | full scan+index pipeline (thread-offloaded) |
| `/api/repositories/{id}/files` | GET | inventory |
| `/api/repositories/{id}/file` | GET | single file (redacted; **traversal/root/directory rejected** — regression-tested) |
| `/api/search` | POST | hybrid/symbol/lexical |
| `/api/symbols` | GET | filtered symbol table |
| `/api/graph` | GET | files graph (resolved import edges) / symbols graph (contains+imports) |
| `/api/chat` | POST | conversation + agent run (mode + execution_mode) |
| `/api/agent/runs` | GET | run history |
| `/api/agent/runs/{id}` | GET | full trace of one run |
| `/api/tools` | GET | tool registry listing |
| `/api/tools/execute` | POST | direct tool invocation (same cage) |
| `/api/tests/run` | POST | run repo tests |
| `/api/diff` | GET | git working-tree diff |
| `/api/diff/apply` | POST | **the controlled write**: containment → old/new → unified diff → atomic write w/ backup → optional test run → **auto-rollback on failure or timeout** (restores exact bytes; removes newly created files) → {diff, ±counts, test_result, rolled_back} |
| `/api/evaluation/run` | POST | benchmark against a repo |
| `/api/evaluation/benchmark` | GET | case definitions |
| `/api/conversations` | GET | history |
| `/api/conversations/{id}` | GET | one conversation |

CORS restricted to the dev origin; every repo-scoped route 404s unknown ids; 409 on not-indexed.

---

## 4. The frontend — 12 screens, IDE-grade

**Stack**: React 18, TypeScript strict, Vite 5, react-router 6. No UI framework — a deliberate GitHub-dark token system (`--bg #0d1117` family) in `styles.css`, monospace everything code.

**Shared plumbing**: `api/client.ts` is the single typed fetch boundary (~35 methods); `components/common.tsx` provides `Spinner`, `ErrorBox` (with retry), `EmptyState`, `StatRow`, and the `useAsync` hook (cancellation-safe, tick-based reload).

| Screen | Route | What it shows / does |
|---|---|---|
| Home | `/` | live backend status card, provider/model badges, repo summary, quick tour |
| Repositories | `/repos` | import (path or https URL) + index, per-repo stats bar (files/source/tests/symbols/relationships/parse-errors), re-index |
| AI Workspace | `/workspace` | the chat: 7 task modes + **execution-mode selector (analysis-only default)**, streamed-style evidence chips that deep-link the Explorer to `file:line`, collapsible per-message agent trace (tools + durations + tokens) |
| Code Explorer | `/explore` | filterable file tree (test files flagged ⚑), line-numbered viewer, **evidence deep-link highlighting** of the cited line |
| Search | `/search` | mode selector (hybrid/lexical/symbol), ranked files + symbol hits tables with scores |
| Symbols | `/symbols` | full symbol table: name/kind/file:line/signature, kind + name filters |
| Graph | `/graph` | file-dependency or symbol-relationship graph, deterministic degree-ranked layered layout, click → connected-edges inspector |
| Tests | `/tests` | run + parsed result: PASS/FAIL, counts, failed-test list, full stdout/stderr |
| Diff | `/diff` | live git diff (colored hunks) + **controlled change panel** (path/mode/content → apply + tests), rollback results surfaced |
| Agent Trace | `/trace` | run history list → detail: state, iterations, usage, full ordered tool-call timeline with durations |
| Evaluation | `/eval` | run benchmark → summary stats + per-case recall/precision/latency/pass table |
| Settings | `/settings` | provider switch (mock/openai), base URL/model/key (masked, blank-to-keep), context budget, max iterations |

**Quality gates enforced**: eslint 0 errors (typescript-eslint + react-hooks recommended), `tsc --strict` 0 errors, production build clean. Three render-phase `setState` violations and one conditional-hook violation were found by lint and fixed.

---

## 5. The end-to-end pipeline, concretely

**A repository question** ("Where is complete_task defined?", mode=locate):
1. `POST /api/chat` → conversation loaded/created → Agent.run begins (ANALYZING→RETRIEVING)
2. ContextEngine: hybrid search → citations + budgeted snippets
3. Tool loop (bounded): `search_symbols` → evidence absorbed
4. Provider.complete(system-prompt-with-mode-contract, task, context) → grounded answer
5. Result + evidence + tool trace persisted → response with run id
6. UI renders answer; evidence chips → Explorer opens `services/task_service.py:32` highlighted

**A controlled fix** (the demo bug: `complete_task` compares status to `"open"`, tests create `"todo"`, so `test_complete_todo_task_fails` fails):
1. Tests run → 6 passed / 1 failed + traceback
2. FIX-mode agent: run_tests → retrieve failing file → read it → diff context
3. Correct content composed (`!= "todo"`) → `POST /api/diff/apply {run_tests_after: true}`
4. Server: containment check → diff → **atomic write with backup** → pytest runs → **7 passed** → success response with diff + counts
5. If a patch *breaks* tests instead: backup restored byte-identical, response `{rolled_back: true, test_result}` — **integration-tested with a deliberately breaking patch**

**Git URL import**: `POST /api/repositories/import {git_url}` → https-validated → depth-limited clone (cached per URL) → registered → `/api/index` runs the standard pipeline. Live-verified against `github.com/octocat/Hello-World`.

---

## 6. The sample repository — `examples/sample_repo`

A complete, realistic Campus Task Management app (its own git repo, own commit history):
```
api/routes.py            HTTP simulation: GET/POST routes wired to the service
services/task_service.py  business logic — CONTAINS THE INTENTIONAL BUG:
                         `if task.status != "open":` (should be "todo")
services/validators.py   validate_priority / validate_title
data/repositories.py     Task + TaskRepository (in-memory persistence)
tests/test_task_service.py  7 tests — 6 pass, test_complete_todo_task_fails FAILS
pyproject.toml, README.md, .gitignore
```
Layered imports `api → services → data` exercise the import graph; the bug
exercises the entire FIX pipeline; the README documents the bug so *it* is
also untrusted input for prompt-injection testing. Tests: `6 passed, 1 failed`
— the failure is a **feature** (the demo target), and `scripts/e2e_demo.py`
restores it after fixing, so the demo is endlessly repeatable.

---

## 7. What is actually verified (all measured, nothing claimed)

| Verification | Method | Result |
|---|---|---|
| Backend unit/integration | `pytest tests -q` — 64 test functions / 9 files | **71 passed** (incl. parametrized) |
| Type safety | `mypy app` (CI-enforced) | **0 errors / 34 files** |
| Lint | `ruff check app tests scripts` | **clean** |
| Frontend | `eslint --max-warnings 0`, `tsc --strict`, `vite build` | **0 / 0 / success** |
| Retrieval quality | 8-case benchmark (CI-run) | **8/8, mean recall 0.875, precision 0.331** |
| Full workflow | `scripts/e2e_demo.py` — 16 live steps vs running backend | **ALL PASS** |
| MCP | `scripts/verify_mcp.py` — real subprocess stdio round-trip | **ALL PASS** |
| API edge cases | `scripts/adversarial_api.py` — 36 checks (traversal, unknown ids, empty/directory paths, bad URLs, validation) | **36/36** |
| Concurrency & abuse | `scripts/adversarial_wave2.py` — 12 parallel chats, 10 mixed eval/chat, unicode, 10k-word queries, huge limits | **14/14** |
| Cross-checks | `scripts/final_verify.py` — symbols graph, eval, both execution modes, git-url rejection | **ALL PASS** |
| Sample repo | own pytest suite | 6 pass / 1 intentional fail |
| Git hygiene | artifact/secret scan of tracked tree | 0 artifacts, 0 secrets |

**All of the above run against the committed code in the final round, not historically.**

### Bugs found by adversarial verification during the build (12 total, all fixed, most regression-locked)

1. SQLite INSERT column-count mismatches (repositories/conversations) — found by first test run
2. tree-sitter **byte-offset vs string-offset** symbol corruption — found by symbol-name tests
3. Import nodes unnamed (`dotted_name`, not `identifier`) → zero import edges — found by relationship tests
4. Import module targets unresolvable after persistence → module pseudo-symbols — found by graph E2E
5. State machine blocked TESTING→ANALYZING — found by agent tests
6. **`/api/graph kind=symbols` returned None** (missing return, introduced by an over-aggressive cleanup, survived because no test covered it) — found by mypy
7. **FTS5 thread-affinity crash** in `/evaluation/run` (connection created in one worker thread, used in another) — found by live-API verification on a fresh DB
8. `write_file` tool reported `wrote: True` without writing — found by honest-labeling audit
9. eslint script existed without eslint installed — found by §86 audit
10. 6 mypy type errors incl. #6 — found by enabling mypy in CI
11. **Empty `?path=` → repo-root → directory `read_bytes()` → 500**, same class in diff/apply and read_file tool — found by adversarial wave 1
12. Tool errors leaked absolute host paths — found by adversarial wave 1

Items 2, 3, 6, 7, 11 are the interesting ones: **every one passed the feature's
happy path** and was caught only by adversarial/type/live verification. That
is the actual argument for this project's engineering discipline.

### The evaluation story (why it exists)
The benchmark is not decoration — it caught a real ranking regression (sym-2:
generic `Task` out-ranked `validate_priority`; fixed with rarity-weighted
symbol tokens; measured FAIL→PASS), and it guarded the FTS removal (quality
unchanged). Precision (0.331) is low **by construction of the metric** —
top-10 retrieval vs 1–3 expected files caps it near 0.3; recall is the
meaningful number, and the docs say so plainly.

---

## 8. Security posture (threat-model driven, tested)

**Asset**: developer's machine + any configured LLM credentials.
**Attacker**: malicious content in an imported repository.

| Threat | Mitigation | Test |
|---|---|---|
| Arbitrary code exec from repos | scanning never runs repo code; only allow-listed git/test commands | `test_dangerous_command_policy` |
| Path traversal (tool + API) | resolve + `relative_to` + root/directory rejection | `test_tool_path_security`, `test_api_file_traversal_blocked`, empty/directory regression tests |
| Command injection | fixed argv lists, `shell=False` everywhere | code path review + policy test |
| Dangerous commands | regex policy (rm -rf, curl\|sh, fork bombs…) enforced at the subprocess execution boundary | `test_dangerous_command_policy`, `test_dangerous_command_policy_enforced_in_production_path` |
| Secret exposure | detection → `[REDACTED_SECRET]` at ingestion, before SQLite storage — and therefore before retrieval/LLM/tool output; log redaction at record creation incl. exception text | `test_secret_detection_and_redact*`, `test_secrets_never_persist_raw_in_file_docs`, `test_logging_security.py` |
| Prompt injection | repo content is retrieval **data**, never instructions; system prompt fixed; mock provider formats structured evidence only | design (ADR-005) |
| Oversized inputs | file-size/repo-count caps, output truncation, tool timeouts | scanner test |
| Agent runaway | iteration cap, repeat/no-progress detection, per-tool timeout | engine tests |
| Unsafe modification | double tool gating + apply-with-backup + **auto-rollback on failing tests or timeout** (exact-byte restore; newly created files removed) | `test_api_diff_apply_rollback`, `..._removes_new_file`, `..._on_test_timeout`, `..._success_retained` |
| Symlink escape | `followlinks=False` | scanner code |
| Info disclosure | error sanitization (`<repo>`), settings key masking | adversarial round |
| Git clone abuse | https-only, traversal-free, depth+time limited, no fetch of repo hooks | `test_git_import.py` (10 cases) |

**Explicitly not protected**: running an untrusted repo's own test suite still
executes that project's code — that's the product's purpose; the cage bounds
*which commands* run. Use a container for genuinely hostile repos. The local
API has **no auth** — single-user local tool; don't expose port 8000.

---

## 9. Graphify — the codebase's own knowledge graph

`graphify-out/` holds a **live structural knowledge graph of Kintsugi-Code itself**,
built with the graphify tool (v0.9.48) via its OpenCode skill and refreshed
after every substantial change (`scripts/refresh_graph.py`):

- **886 nodes / 1,821 edges / 59 communities** (AST-derived; refreshed
  2026-09-03 after the post-audit remediation round via `graphify update .`;
  HTML viz at `graph.html`, audit at `GRAPH_REPORT.md` — all three artifacts
  regenerated from the same run). Freshness is content-verified: the
  regenerated graph contains the security fixes (e.g. `_sanitize_error`)
  and both new test modules (`test_logging_security`, `test_config_env`).
- Communities mirror the real architecture (Agent Engine, AST Parser,
  Persistence Store, FastAPI Routes, Frontend UI…), which was used to sanity
  check module boundaries during development.
- Query-verified against new code after the completion round
  (`graphify query "Where are the agent skill specs defined?"` → correctly
  surfaces `backend/app/agent/skills.py` + its tests).
- Honest note: an earlier build reported 10 extraction warnings (5 missing
  `relation`, 5 missing `source_file` on hand-authored semantic edges). The
  current refresh pipeline emits **no extraction warnings** (91% EXTRACTED /
  9% INFERRED / 0% AMBIGUOUS); the historical warning count is not
  reproducible against the current tool state and is recorded here for
  provenance only.

---

## 10. Documentation set (all committed)

| Doc | Content |
|---|---|
| `README.md` | honest product overview, quick start, config table, demo walkthrough, security summary, limitations |
| `docs/ARCHITECTURE.md` | mermaid system diagram, per-component deep dives, data flows, dev tooling, deployment |
| `docs/SECURITY.md` | threat model table with mitigations *and the test that proves each one* |
| `docs/EVALUATION.md` | methodology, measured results, honesty notes (why precision is low, what's *not* measured) |
| `docs/MCP.md` | protocol level, tool table, client usage, security, limitations |
| `docs/DEMO.md` | the 10 scripted demo workflows + API reproduction commands |
| `docs/RESUME_NOTES.md` | 1-liner, stack, 5 strongest capabilities, measured metrics, 3 resume bullets, 5 interview points, weaknesses |
| `docs/INTERVIEW_GUIDE.md` | 40+ technical questions with pointers into code/docs |
| `docs/adr/ADR-001..007` | modular monolith · tree-sitter (byte-offset lesson) · hybrid retrieval (FTS removal amendment) · provider abstraction · controlled execution · local-first demo · MCP scope |
| `BUILD_STATUS.md` | phase checklist + per-round verification logs + bug history |
| `CHANGELOG.md` / `CONTRIBUTING.md` / `LICENSE` | full change history incl. fixed-bugs section · contribution rules (tests required, eval must stay 8/8) · MIT |

---

## 11. Test inventory (64 functions → 71 pytest cases)

| File | Covers |
|---|---|
| `test_scanner_secrets.py` | language detection, test/doc/config classification, ignore rules (node_modules/.git/pycache/secrets/binaries/pods), size caps, secret detection + redaction + key-name preservation + **parse-preserving redaction** + **no-raw-secrets-in-file_docs (ingestion-time storage redaction)** |
| `test_index_retrieval.py` | symbol extraction (names/kinds), relationships (imports/contains), scan stats, symbol/lexical/hybrid search ranking, query-intent detection, context budgeting, no-match behavior |
| `test_agent_api.py` | state-machine validity/invalid transitions, agent EXPLAIN/LOCATE/TEST runs, tool path containment, read+search tools, command policy **(helper + production-path enforcement)**, **full API flow** (import→index→search→symbols→chat→graph→file), traversal blocking, **rollback-on-failing-patch (existing-file / new-file / timeout / success-retained)**, empty/directory path rejections, tool error sanitization |
| `test_mcp.py` | initialize, tools/list, set_repository + get_symbol + search_code over the dispatcher, no-active-repo error, unknown-method error |
| `test_git_import.py` | valid https URLs, 8 rejected URL classes (ssh/scp/file/http/traversal/metacharacters), clone shape, API-level rejection |
| `test_skills.py` | every TaskMode has a complete SkillSpec, read-only modes have zero modification tools, FIX is the only modifying skill, engine policy == specs, find_path (1-hop correct path, unreachable, invalid inputs), tools listing |
| `test_logging_security.py` | secret redaction across logging paths — emitted-output tests for message, arguments, exception text, root-logger propagation, uvicorn logger coverage |
| `test_config_env.py` | `.env` location contract (backend/.env), actual file loading, process-env precedence |
| `conftest.py` | temp-store, sample-repo-copy, indexed-repo, TestClient fixtures with store monkeypatching |

Counting semantics: 64 test functions; `test_git_import.test_rejected_urls` is
parametrized over 8 URL classes, so `pytest` collects **71 cases**.

Plus **five verification suites** in `scripts/` (§7) that run against live
processes — 66 additional live checks beyond pytest.

---

## 12. Infrastructure

- **CI** (`.github/workflows/ci.yml`): backend job (install → **mypy** → pytest → evaluation benchmark) + frontend job (install → **eslint** → **tsc** → build). Free runners only; every gate that exists locally is enforced remotely — nothing passes locally that CI wouldn't.
- **Docker**: backend `python:3.12-slim` + uvicorn (SQLite on the mounted `Kintsugi-Code-data` volume so indexes survive); frontend `node:20` build → `nginx:alpine` serving the SPA with `/api` proxy and SPA fallback routing. `docker compose up --build` runs the whole product.
- **Local dev**: uvicorn + vite dev proxy; `.env.example` documents all 16 config variables.

---

## 13. Project-local OpenCode skill

`.opencode/skills/Kintsugi-Code-dev/SKILL.md` — makes the repo's own conventions
executable for future agents: exact commands (pytest/eval/e2e), and five
rules that encode this project's hard-won lessons: **ranking changes require
a benchmark re-run (8/8 or revert)**; tool/file-access changes require a
security test; **the sample repo's bug must never be fixed** (it's the demo
fixture); Store schema changes must update INSERT column lists (two past
bugs); the mock provider must stay offline-deterministic.

---

## 14. Known limitations (honest, documented everywhere)

1. **AST depth**: Python/JS/TS only; other indexed languages get lexical+metadata retrieval without symbols.
2. **Mock answers are templates** — grounded, deterministic, honest about confidence, but not prose. Connect an OpenAI-compatible endpoint for fluent answers.
3. **Import→file resolution is heuristic** (dotted-path + suffix matching); dynamic imports invisible; no call-graph extraction (imports + containment only).
4. **Benchmark scope**: 8 cases / one repo — a regression net, not a quality claim.
5. **No API auth** — single-user local tool by design; don't expose it.
6. **Graph layout is deterministic-layered**, not force-directed — chosen for correctness over visual complexity.
7. **Semantic (embedding) retrieval deliberately deferred** until it can run locally or degrade cleanly (ADR-003) — the measured lexical+symbol stack hits 8/8 without it.
8. Windows-first development; stdio MCP framing is platform-agnostic and CI (Linux) exercises the same paths via pytest.

---

## 15. How to experience it in 90 seconds

```bash
# 1. backend
cd backend
python -m venv .venv
.venv\Scripts\pip install fastapi "uvicorn[standard]" pydantic pydantic-settings httpx tree-sitter tree-sitter-language-pack pytest pytest-asyncio
.venv\Scripts\python -m uvicorn app.main:app --port 8000

# 2. frontend
cd frontend && npm install && npm run dev      # → http://localhost:5173

# 3. in the UI: Repositories → import <project>\examples\sample_repo
#    AI Workspace → "Where is complete_task defined?" (locate) → click evidence
#    Tests → Run → watch the intentional failure
#    Diff → apply the one-line fix → tests auto-run → 7 passed
#    Agent Trace → every tool call, every duration
#    Evaluation → 8/8 with real recall numbers

# 4. or scripted, against the live backend:
python scripts/e2e_demo.py          # 16-step workflow, ALL PASS
python scripts/verify_mcp.py        # MCP round-trip
python scripts/adversarial_api.py   # 36 edge-case checks
python scripts/adversarial_wave2.py # concurrency + abuse checks
```

No API key. No network. That's the point.

---

*Generated from repository state: 119 tracked files · 71 passing tests ·
9 commits · every number measured, not estimated.*

