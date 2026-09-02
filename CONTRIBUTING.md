# Contributing to CodeForge

Thanks for considering a contribution!

## Development setup

```bash
# backend
cd backend
python -m venv .venv
.venv\Scripts\pip install fastapi "uvicorn[standard]" pydantic pydantic-settings httpx tree-sitter tree-sitter-language-pack pytest pytest-asyncio
.venv\Scripts\python -m pytest tests -q

# frontend
cd frontend
npm install
npx tsc -b --noEmit && npm run build
```

## Ground rules

1. **Every change ships with tests.** New tool → tool test; new retrieval
   behavior → benchmark still 8/8; security-relevant change → security test.
2. **No fake features.** A button must do something or not exist. Metrics
   come from measurements (see docs/EVALUATION.md conventions).
3. **Security first.** Anything touching file access, subprocesses, or
   indexed content must respect the existing guards (path containment,
   allow-listed commands, secret redaction) — see docs/SECURITY.md.
4. **Modular monolith.** Add code within the existing package boundaries;
   don't introduce services, queues, or frameworks without an ADR.

## Adding a tool

1. Implement `async def my_tool(ctx: ToolContext, args: dict) -> dict` in
   `app/tools/registry.py`.
2. Register it with a description + parameter schema.
3. Decide: read-only or `modifies_files=True` (the latter is stripped in
   non-execution modes automatically).
4. Add mode allow-lists in `app/agent/engine.py::MODE_TOOLS` if the agent
   should use it.
5. Test it (happy path + a security rejection path).

## Adding an evaluation case

Append to `get_benchmark()` with real `expected_files` (verify them against
the sample repo). Never tune expectations to current retrieval behavior.

## Commit style

Conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`,
`security:`. Keep commits runnable (tests green at each commit).
