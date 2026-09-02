# ADR-003: Hybrid retrieval without a vector database

Date: 2026-09-02 · Status: accepted

## Context
Answers must be grounded in the right files. Candidates: pure lexical, pure
embedding/semantic, or a hybrid stack; hosting an embedding model or vector
DB adds weight to a local-first tool.

## Decision
Three-tier hybrid: SQLite FTS5 lexical (BM25-style fallback when FTS is
unavailable), rarity-weighted structural symbol search, and file-importance
priors — fused into one ranked list. Semantic embeddings are a deliberate
future tier behind the same interface.

## Consequences
+ Zero extra services/models; deterministic, measurable retrieval (8/8
  benchmark cases, mean recall 0.875 — see docs/EVALUATION.md).
+ The rarity-weighted symbol scoring exists because the benchmark caught
  generic names (`Task`) out-ranking specific ones (`validate_priority`);
  the fix was measured before and after.
− Lexical misses paraphrases; intent is inferred from query keywords only.
− Symbol scoring heuristics are tuned on a small benchmark — extending the
  corpus is the evaluation roadmap item.
