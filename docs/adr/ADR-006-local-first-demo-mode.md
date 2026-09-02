# ADR-006: Local-first demo mode as default

Date: 2026-09-02 · Status: accepted

## Context
Reviewers, recruiters, and CI must be able to run the full product without
keys, accounts, or network — otherwise none of the above ever happens.

## Decision
Default configuration: `CODEFORGE_LLM_PROVIDER=mock`, SQLite in the backend
directory, sample repository bundled, no telemetry, no external calls. Every
feature (search, symbols, graph, tests, diff, trace, evaluation, MCP) is
functional in this mode.

## Consequences
+ `git clone → install → run` works everywhere, offline; CI runs the same
  suite as developers.
+ The evaluation benchmark runs in CI without secrets.
− Semantic retrieval (embeddings) is deferred until it can also run locally
  or degrade cleanly — documented as the main retrieval roadmap item.
