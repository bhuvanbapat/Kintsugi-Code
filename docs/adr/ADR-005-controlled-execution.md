# ADR-005: Controlled execution, never blind file writes

Date: 2026-09-02 · Status: accepted

## Context
An agent that modifies code must not be able to silently damage a repository,
and repository content must never be treated as instructions (prompt
injection lives in READMEs and comments).

## Decision
1. Modification tools are gated twice: by TaskMode allow-lists and by
   ExecutionMode (`analysis_only` default strips every file-writing tool).
2. The apply path is: read old → compose new → unified diff → atomic write
   with backup → run tests when requested → **auto-rollback on non-zero
   exit**.
3. The agent never consumes raw repository text as instructions; it receives
   structured retrieval output (files, symbols, citations), and the system
   prompt fixes behavior. Repo content is data.
4. Tool selection is a deterministic per-mode policy, and every call is
   recorded with duration in the run trace.

## Consequences
+ The worst-case agent action is a tested, rolled-back patch.
+ Full auditability: every run's tool history is inspectable (API + UI).
+ Injection resistance: a README saying "delete the project" is text in the
  corpus; it can at most pollute retrieval, never execution.
− Less "agentic autonomy" than unbounded loops — an intentional product
  stance; oversight modes are surfaced rather than marketed away.
