# ADR-003: Hybrid retrieval without a vector database

Date: 2026-09-02 · Status: accepted (amended)

## Context
Answers must be grounded in the right files. Candidates: pure lexical, pure
embedding/semantic, or a hybrid stack; hosting an embedding model or vector
DB adds weight to a local-first tool. The original implementation used
SQLite FTS5 for the lexical tier.

## Decision
Three-tier hybrid: **pure-Python BM25** lexical scoring over an in-memory
token index, rarity-weighted structural symbol search, and file-importance
priors — fused into one ranked list. Semantic embeddings remain a deliberate
future tier behind the same interface.

## Amendment (FTS5 removed)
The first implementation kept an in-memory FTS5 connection as the primary
lexical path with BM25 as fallback. That connection is created in one thread
and the retriever cache is shared across worker threads — SQLite objects are
thread-affine, so `/api/evaluation/run` crashed intermittently (500) when
execution landed on a different thread. Rather than per-thread connections
or locks, the FTS layer was removed entirely: the BM25 path — already
benchmark-equivalent — became the single lexical implementation. Quality was
re-verified after the change: 8/8 benchmark cases, recall 0.875, unchanged.

## Consequences
+ Zero extra services/models and no thread-affinity hazards; deterministic,
  measurable retrieval (8/8 benchmark cases, mean recall 0.875 — see
  docs/EVALUATION.md).
+ The rarity-weighted symbol scoring exists because the benchmark caught
  generic names (`Task`) out-ranking specific ones (`validate_priority`);
  the fix was measured before and after.
− Lexical misses paraphrases; intent is inferred from query keywords only.
− Symbol scoring heuristics are tuned on a small benchmark — extending the
  corpus is the evaluation roadmap item.
− BM25 over Python dicts is O(corpus) per query — fine for the intended
  local-repo scale (thousands of files), not a hosted-multi-tenant design.
