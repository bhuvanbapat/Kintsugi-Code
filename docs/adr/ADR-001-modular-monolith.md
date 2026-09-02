# ADR-001: Modular monolith

Date: 2026-09-02 · Status: accepted

## Context
CodeForge needs scanning, AST parsing, retrieval, an agent, tools, MCP, and a
web UI. Options: microservices, an agent framework, or a modular monolith.

## Decision
Single FastAPI application with strictly layered internal packages
(`indexing` → `services` → `retrieval` → `agent`/`tools`/`api`), one SQLite
file, one frontend SPA. No message queues, no service sprawl, no external
agent framework.

## Consequences
+ One process to run/test/debug; the whole system is explainable by one engineer.
+ Deployment is trivial (uvicorn + static build, or one compose file).
+ Module boundaries are still enforced by package structure and tests.
− Single-node scaling ceiling — acceptable for a local-first developer tool.
