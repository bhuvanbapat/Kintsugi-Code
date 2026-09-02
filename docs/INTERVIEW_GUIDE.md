# CodeForge — Interview Guide

Technical questions you should be able to answer about this project, with
pointers into the code/docs.

## Repository indexing & parsing
- How does the scanner avoid executing repository code? (`app/indexing/scanner.py` — allow-listed traversal, size caps; SECURITY.md)
- Why tree-sitter over regex or LLM extraction? (ADR-002)
- Tree-sitter byte offsets: name the bug class and the fix. (`ast_parser.py::_name_for_node`, RESUME_NOTES.md)
- What happens when one file fails to parse? (counted, skipped — never fatal)

## Retrieval & context
- What are the three retrieval tiers and how are scores fused? (`retrieval/hybrid.py`, ADR-003)
- Why no vector database (yet)? What would change if you added embeddings? (ADR-003, roadmap)
- How does the context engine bound LLM input? (token budget, line-windowing — `retrieval/context_engine.py`)
- What retrieval defect did the benchmark catch, and how was it fixed? (rarity weighting; EVALUATION.md sym-2 story)
- How do you prevent "just send the whole repo to the LLM"?

## RAG & evidence
- How are citations generated and made clickable? (EvidenceCitation model → UI deep-links)
- How do you distinguish confirmed vs inferred vs uncertain? (`models/domain.py::Confidence`, mock provider labels)

## Agent architecture
- Describe the state machine and why invalid transitions raise. (`agent/state_machine.py`, tests)
- What stops runaway loops? (max iterations, repeat-call detection, no-progress counter, timeouts)
- Why is tool selection deterministic per mode rather than LLM-chosen? (ADR-005 — auditability in mock mode)
- How is each TaskMode's tool allow-list enforced? (`agent/engine.py::MODE_TOOLS`)

## Tool calling & MCP
- How is path traversal prevented in tools and the file API? (`tools/registry.py::resolve_in_repo`; tests)
- What does the dangerous-command policy block? Give examples. (`assert_safe_command`)
- What MCP surface did you implement and verify? How? (docs/MCP.md; scripts/verify_mcp.py)
- Why expose only read-only tools over MCP?

## Security
- Treat this README as attacker-controlled: what does CodeForge do? (content is retrieval data; never instructions — ADR-005)
- Where does secret redaction happen and what patterns? (`indexing/secrets.py`; tested)
- Walk through the rollback-on-failing-tests flow. (`main.py::apply_patch`; integration test)

## Testing & evaluation
- What layers are tested? (34 backend tests: scanner/redaction/AST/retrieval/agent/tools/security/API/MCP)
- How are metrics computed and what do they NOT claim? (EVALUATION.md honesty notes)
- What would you do to scale the benchmark?

## Observability
- What is recorded per run? (tool calls, durations, state transitions, usage)
- How do you show token usage when a provider doesn't report it? ("unavailable" — never invented)

## Scalability & cost
- Where are the single-node ceilings, and does it matter? (ADR-001)
- How is context size kept small (and cheap) per query?
- How would you add streaming responses? Multi-user auth?

## Human oversight
- Explain ExecutionModes and why `analysis_only` is the default. (ADR-005)
- Why is "full autonomy" not marketed here?

## Failure handling
- What degrades gracefully, and how? (AST fallback, FTS fallback, mock provider, per-file parse errors)
- What did you have to fix during development that tests now protect against? (SQL column mismatch, byte offsets, import naming, ranking regression)
