# ADR-004: Provider abstraction with a deterministic offline mock

Date: 2026-09-02 · Status: accepted

## Context
The product must be demonstrable with no API key and no network, yet
upgradeable to real models without code changes, and must not be locked to
one vendor.

## Decision
`LLMProvider` interface with two implementations: `OpenAIProvider` (any
OpenAI-compatible `/chat/completions` endpoint — OpenAI, Ollama, vLLM, LM
Studio) and `MockProvider` (default). The mock composes answers **from the
retrieval context passed to it** — files, symbols, citations — and labels its
confidence; it cannot invent repository facts.

## Consequences
+ Demo mode is honest: the "AI" in mock mode is grounded composition over
  real retrieval output, clearly labeled, fully reproducible offline.
+ Switching providers is configuration (`Kintsugi-Code_LLM_PROVIDER`), not code.
+ Usage tracking: provider-reported tokens surface when available; the UI
  shows "unavailable" otherwise — never fabricated.
− Mock answers are template-shaped rather than prose-fluent; that is an
  accepted, documented tradeoff for guaranteed offline operation.

