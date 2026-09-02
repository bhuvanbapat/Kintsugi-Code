# ADR-002: Tree-sitter for structural parsing (with stdlib-ast fallback)

Date: 2026-09-02 · Status: accepted

## Context
Evidence-backed answers and symbol navigation need real ASTs, not regex.
Candidates: per-language parsers, tree-sitter, LLM-extracted structure.

## Decision
tree-sitter via `tree-sitter-language-pack` for Python/JS/TS (the languages
with the deepest support), with a stdlib-`ast` fallback for Python so symbol
extraction degrades gracefully if the native wheel is unavailable.

## Consequences
+ One grammar API across languages; incremental adoption for more grammars.
+ Byte-accurate node spans; partial failures are per-file, never fatal.
− tree-sitter offsets are **byte** offsets: all slicing must go through the
  UTF-8-encoded buffer. We hit this exact bug during development (an em-dash
  in a docstring shifted every subsequent symbol name) and fixed it by
  encoding before slicing — regression-covered by the symbol tests.
− Import targets aren't `identifier` nodes; we name imports from statement
  text and synthesize `module:<name>` pseudo-symbols so import edges survive
  persistence and resolve to files heuristically.
