# CodeForge — Résumé Notes

## One-line description
Built an AI-assisted software engineering workspace that indexes repositories
structurally (tree-sitter AST), answers code questions with file:line
evidence via hybrid retrieval, runs tests, and applies validated,
auto-rolling-back code fixes — with a full agent trace, MCP integration,
and a measured 8/8 retrieval benchmark.

## Actual technology stack
Python 3.11+ · FastAPI · Pydantic · SQLite (FTS5) · tree-sitter ·
httpx · pytest · React 18 · TypeScript · Vite · Docker · GitHub Actions ·
MCP (JSON-RPC 2.0 stdio) · Graphify (dev-time knowledge graph)

## Strongest technical capabilities
1. **Structural code intelligence** — multi-language AST extraction with
   byte-offset-correct symbol/relationship graphs persisted in SQLite.
2. **Hybrid retrieval with measured quality** — lexical (FTS5) + rarity-weighted
   symbol search + importance priors; benchmarked (8/8, recall 0.875), with
   a documented before/after ranking fix.
3. **Safe agent engineering** — validated state machine, bounded iterations,
   loop/no-progress detection, per-mode tool allow-lists, path containment,
   dangerous-command policy, secret redaction, auto-rollback patches.
4. **Provider abstraction with honest offline mode** — deterministic,
   evidence-grounded mock answers; OpenAI-compatible upgrade path.
5. **Real integration surface** — MCP server (verified stdio round-trip) +
   client; not a stub.

## Measured metrics (reproducible)
- Backend test suite: 34 passing (scanner, redaction, AST, retrieval, agent,
  tools, security, API, MCP).
- Retrieval benchmark: 8/8 cases, mean recall 0.875, mean precision 0.331
  (metric-capped; explained in docs/EVALUATION.md).
- E2E workflow: 16/16 live checks (import→index→query→fix→test→trace).
- Frontend: strict TypeScript, 12 screens, clean production build.
- Indexing: 8-file sample repo → 37 symbols / 22 relationships in <1s.

## Three résumé bullet candidates
- Built an AI software-engineering workspace (FastAPI + React/TS) featuring
  tree-sitter AST indexing, hybrid lexical/structural retrieval, and
  evidence-cited codebase Q&A — benchmarked at 0.875 retrieval recall on a
  curated evaluation suite.
- Engineered a controlled coding agent: validated state machine, bounded
  tool loop with loop/no-progress detection, path-containment and
  dangerous-command policies, secret redaction, and diff-validated patches
  that auto-rollback on failing tests.
- Exposed and consumed the Model Context Protocol over stdio JSON-RPC,
  enabling external AI clients to use the product's repository-intelligence
  tools; verified with live subprocess round-trip tests.

## Five interview talking points
1. **The byte-offset bug**: tree-sitter spans are byte offsets; slicing the
   Python `str` shifted every symbol after the first non-ASCII character —
   how the symbol tests caught it and the fix (encode-then-slice).
2. **Ranking fix driven by measurement**: the benchmark exposed generic
   symbols (`Task`) out-ranking specific ones (`validate_priority`); rarity
   weighting + stopwords took sym-2 from FAIL to PASS with data on record.
3. **Why mock mode is honest**: the offline provider composes answers from
   retrieval context only — it cannot hallucinate files, and confidence is
   labeled; contrast with wrapping a chat API and hoping.
4. **Prompt-injection posture**: repository content never becomes
   instructions; the agent consumes structured retrieval output, and the
   worst-case mutation is a tested, rolled-back patch.
5. **When NOT to use a vector DB**: measured lexical+symbol retrieval hit
   8/8 on the benchmark; embeddings are deferred until they earn their
   complexity — an explicit ADR tradeoff.

## Architecture discussion points
- Modular monolith vs. agent frameworks (ADR-001)
- Retrieval tiers & context budgeting (ADR-003, context engine)
- Tool-system security model (containment, allow-lists, rollback) (ADR-005)
- MCP scope decision — core protocol only (ADR-007)
- Evaluation as regression protection for ranking changes

## Weaknesses (know them before the interviewer does)
- Precision metric is low by construction (0.331) — explain, don't hide.
- Benchmark is one small repo / 8 cases — regression net, not a quality claim.
- Mock provider answers are templated, not prose.
- Import→file resolution is heuristic; no call-graph extraction yet.
- No auth on the local API (single-user, local-only tool).
