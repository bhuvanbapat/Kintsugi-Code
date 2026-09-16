# Changelog

All notable changes to CodeForge. Format: Keep a Changelog; versioning: semver.

## [0.1.1] - 2026-09-03 — post-audit remediation

Security/correctness fixes from the independent implementation audit.
Architecture unchanged; every fix carries a new regression test.

### Fixed
- **Repository self-containment (P0)**: `examples/sample_repo` was tracked as
  a gitlink (mode 160000) with no `.gitmodules`, and the referenced commit
  was never in the parent object store — fresh clones received an empty
  examples directory, breaking CI evaluation, pytest fixtures, and every
  verification script. The sample repo is now ordinary tracked content
  (nested .git removed). Fresh-clone verified end to end.
- **Secrets stored unredacted (HIGH)**: redaction moved to ingestion, before
  `file_docs` persistence — raw secret values can no longer enter SQLite.
  SHA-256 still hashes original file content so file identity remains
  verifiable. Redaction output is now syntactically valid source (quoted
  secrets redact to a valid string literal), keeping AST extraction correct
  for secret-bearing files. See docs/SECURITY.md for re-index remediation
  of databases created by 0.1.0.
- **Log redaction coverage (HIGH)**: redaction now runs at LogRecord
  creation (global record factory) and covers messages, arguments, and
  exception/traceback text on all logging paths (application, root,
  uvicorn). Previously exception text bypassed redaction entirely.
- **Dangerous-command policy enforcement (MED)**: `assert_safe_command` is
  now enforced inside the subprocess execution boundaries
  (`_run_command`, `TestRunner.run`, `TestRunner.static_check`) instead of
  existing as an unwired helper. shell=False + fixed argv remain the
  primary injection defenses.
- **Rollback completeness (MED)**: `/api/diff/apply` with
  `run_tests_after` now rolls back on test failure OR timeout, restores
  exact pre-apply bytes for existing files, and removes newly created
  files (pre-state = absent).
- **`.env` location (MED)**: Settings load `backend/.env` as documented
  (an off-by-one resolved `backend/app/.env`). Location, load, and
  env-var precedence are regression-tested.
- Portability: `scripts/e2e_demo.py` and `scripts/verify_mcp.py` derive
  paths from `__file__` (no machine-specific absolute paths).
- Git-clone cache dir uses a stable sha256 digest of the URL (was a
  process-salted `hash()`, which broke the documented determinism).
- Scanner ignore list: fixed the `' Pods'` entry (stray leading space and
  wrong casing vs the lowercase comparison) — iOS `Pods/` directories are
  ignored again.
- `search_code` tool honors `mode` (lexical/symbol/hybrid, default hybrid)
  matching its MCP twin and its description.

## [0.1.0] - 2026-09-02

Initial release.

### Added
- Repository engine: secure scanner, ignore rules, language/test/doc/config
  classification, size/count caps.
- Structural code intelligence: tree-sitter AST extraction (Python/JS/TS) with
  stdlib-ast fallback; symbols, containment + import relationships; SQLite
  persistence with module pseudo-symbols.
- Hybrid retrieval: rarity-weighted symbol search + lexical BM25 scoring +
  file-importance priors; deterministic context engine with token budgeting
  and evidence citations. (An initial FTS5 lexical tier was removed during
  development for SQLite thread-affinity safety — see ADR-003 amendment.)
- AI layer: LLMProvider abstraction (OpenAI-compatible + deterministic offline
  mock); evidence-backed answers with confidence labels; token usage surfaced
  when providers report it.
- Controlled agent: validated state machine, bounded loop with repeated-call
  and no-progress detection, per-mode tool policy, 7 task modes
  (explain/locate/analyze/plan/test/fix/review), execution-mode gating.
- Tool system: 17 tools with path containment, dangerous-command policy,
  subprocess timeouts/output caps, secret redaction.
- Test runner: ecosystem detection (pytest/npm/go/cargo/maven/gradle) with
  structured pass/fail parsing.
- Controlled modification workflow: unified diffs, atomic apply with backup,
  test validation, automatic rollback on failure.
- MCP integration: stdio JSON-RPC 2.0 server (8 read-only tools incl.
  set_repository, verified live) and client for external servers.
- Evaluation: 8-case retrieval benchmark with recall/precision/latency
  (8/8 passing, mean recall 0.875).
- Observability: per-tool timings, run traces, conversation history, agent
  trace viewer UI.
- Frontend: 12 screens (home, repositories, workspace, explorer, search,
  symbols, graph, tests, diff, trace, evaluation, settings) in React 18 +
  TypeScript with strict typecheck.
- Sample repository: layered Campus Task Management app with one intentional
  bug and a failing test reproducing it.
- Security: threat model (docs/SECURITY.md), traversal rejection,
  secret detection/redaction, injection-resistant agent design.
- Infra: Dockerfiles + docker-compose, GitHub Actions CI, .env.example,
  MIT license, ADRs 001–007, Graphify knowledge graph of the codebase.

### Fixed during development (regression-protected)
- SQLite column-count mismatches in repository/conversation persistence.
- tree-sitter byte-offset vs string-offset slicing for symbol names.
- Import statement naming (dotted_name nodes) and module-edge persistence.
- Symbol ranking regression: generic names out-ranking specific ones
  (caught by evaluation case sym-2, fixed with rarity weighting).
- Agent state machine blocking TESTING → ANALYZING composition path.
