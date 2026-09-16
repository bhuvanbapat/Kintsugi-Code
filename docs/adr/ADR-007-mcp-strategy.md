# ADR-007: MCP as the integration layer (tools-first, stdio)

Date: 2026-09-02 · Status: accepted

## Context
Kintsugi-Code should both expose its capabilities to external AI clients and
consume external tools — without locking to one assistant vendor. The MCP
specification standardizes this, but its surface keeps evolving
(resources, prompts, sampling, …).

## Decision
Implement the stable **core** of MCP (2024-11-05): JSON-RPC 2.0 over stdio,
initialize / tools/list / tools/call. Expose only read-only repository tools
plus `set_repository`. Consume external servers through a small stdio
`MCPClient`. Treat richer MCP features as additive, isolated in
`app/mcp/` so evolution requires no core changes.

## Consequences
+ Works with any current MCP client; verified by a live subprocess
  round-trip (scripts/verify_mcp.py).
+ Security posture stays auditable: MCP calls flow through the same tool
  registry (containment, redaction, output caps); no mutation surface over
  MCP.
− Base-protocol only for now — resources/prompts omitted deliberately and
  documented in docs/MCP.md rather than half-implemented.

