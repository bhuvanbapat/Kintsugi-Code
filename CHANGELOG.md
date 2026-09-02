# Changelog

All notable changes to CodeForge. Format: Keep a Changelog; versioning: semver.

## [0.1.0] — 2026-09-02

Initial release.

### Added
- Repository engine: secure scanner, ignore rules, language/test/doc/config
  classification, size/count caps.
- Structural code intelligence: tree-sitter AST extraction (Python/JS/TS) with
  stdlib-ast fallback; symbols, containment + import relationships; SQLite
  persistence with module pseudo-symbols.
- Hybrid retrieval: FTS5 lexical + rarity-weighted symbol search +
  file-importance priors; deterministic context engine with token budgeting
  and evidence citations.
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
- MCP integration: stdio JSON-RPC 2.0 server (7 tools, verified live) and
  client for external servers.
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
