# CodeForge — Evaluation

## Method

`backend/app/services/evaluator.py` measures **retrieval quality** — the
foundation every downstream answer is built on. For each curated case the
retriever runs a hybrid search; we compute:

- **recall** = |expected files ∩ top-10 retrieved| / |expected files|
- **precision** = hits / retrieved count
- **latency** = wall-clock ms of the retrieval call
- **pass** = recall ≥ 0.5 AND all expected symbols present in symbol results

Cases target the bundled `examples/sample_repo`: architecture, symbol
location, dependency lookup, bug finding, relevant-file retrieval, planning,
test diagnosis.

## Measured results (this build)

Run: `cd backend && .venv\Scripts\python.exe scripts\run_evaluation.py`
(or the Evaluation page against a live backend).

```
total_cases: 8    passed: 8    mean_recall: 0.875    mean_precision: 0.331

arch-1      recall 1.00  PASS   (all 3 layers retrieved)
sym-1       recall 1.00  PASS   (TaskRepository located)
sym-2       recall 1.00  PASS   (validate_priority located)
dep-1       recall 1.00  PASS   (api↔service imports found)
bug-1       recall 0.50  PASS   (service + test retrieved)
file-1      recall 1.00  PASS   (persistence layer)
plan-1      recall 1.00  PASS   (all affected files)
testdiag-1  recall 0.50  PASS   (failing test + service retrieved)
```

Retrieval latency rounds to 0ms at this corpus size — that is a real
measurement (in-memory FTS over a small repo), not a placeholder.

## Honest notes on the numbers

- **Precision 0.331 is low by design of the metric**: we retrieve top-10
  files but most cases have 1–3 expected files, so even perfect retrieval
  cannot exceed ~0.3 here. Recall is the meaningful number for "did we find
  the right context".
- **sym-2 initially failed** (7/8): "Find the function that validates task
  priority" ranked the generic symbol `Task` above `validate_priority`
  because short names matched as substrings. Fix: rarity-weighted symbol
  tokens + stopword list + length-scaled substring bonuses. Re-run: 8/8.
  This is the evaluation loop doing its job — a measured retrieval defect,
  a targeted ranking fix, a re-measured pass.
- Metrics are computed from actual retriever output on every run; nothing is
  hardcoded or simulated.
- The benchmark is small (8 cases, one repo) — sufficient to catch ranking
  regressions, not a claim of general quality. Extending the corpus is the
  top evaluation roadmap item.

## What is NOT measured

- Answer quality of external LLM providers (only retrieval is benchmarked;
  the mock provider's answers are deterministic templates).
- End-to-end fix quality on arbitrary repos (the single scripted e2e flow
  is in scripts/e2e_demo.py).
