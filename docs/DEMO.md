# CodeForge — Demo Script

Everything below was executed and verified (see `scripts/e2e_demo.py`, which
automates these exact steps against a live backend — all 16 checks PASS).

## Setup

```bash
# terminal 1 — backend
cd backend
.venv\Scripts\python -m uvicorn app.main:app --port 8000

# terminal 2 — frontend
cd frontend
npm run dev        # http://localhost:5173
```

The sample repository lives at `examples/sample_repo` — a Campus Task
Management app (api/services/data layers, pytest suite) with **one
intentional bug**: `TaskService.complete_task` compares status to `"open"`
instead of `"todo"`, so `test_complete_todo_task_fails` fails.

## The 10 demo workflows

### 1. Explain the architecture
Workspace → mode `explain` → *"Explain the repository layering: services, data, API."*
Answer cites `api/routes.py`, `services/task_service.py`, `data/repositories.py`
with line ranges. Click an evidence chip → Explorer opens at that line.

### 2. Locate authentication-equivalent functionality
mode `locate` → *"Where is complete_task defined?"* → symbol evidence +
`services/task_service.py:32`.

### 3. Find the dependency chain
Graph page → file view: `api/routes.py → services/task_service.py →
data/repositories.py` import edges. Or `get_dependencies` via tools.

### 4. Find the intentional bug
Tests page → Run → **6 passed, 1 failed** → `tests/test_task_service.py::test_complete_todo_task_fails`
with the `InvalidTaskError: task 1 is not completable from status todo` traceback.

### 5. Generate an implementation plan
mode `plan` → *"Plan adding a due-date filter to task listing."* → ranked
affected files: routes, service, repository.

### 6. Produce a diff
Diff page → path `services/task_service.py`, mode `full`, content = the fixed
source (change `!= "open"` to `!= "todo"`), Apply.

### 7. Apply the controlled fix
The apply runs the test suite after writing. Result: **7 passed / 0 failed**
— shown with additions/deletions and the unified diff.
(If a patch breaks tests, the API restores the original file and returns
`rolled_back: true` — try applying `syntax error !!! (` to see it.)

### 8. Run tests
Tests page → Run → all green after the fix.

### 9. Explain the final diff
Diff page → Load git diff → shows exactly the one-line status-check change
with `-`/`+` coloring.

### 10. Show the agent trace
Agent Trace page → any run → every tool call (`get_repository_map — 3ms`,
`search_symbols — 1ms`, `run_tests — 812ms`, …), state transitions,
iterations, token usage.

## API-level reproduction

```bash
python scripts/e2e_demo.py      # 16-step verified workflow, live backend
python scripts/verify_mcp.py    # MCP stdio round-trip
cd backend && .venv\Scripts\python.exe scripts\run_evaluation.py   # 8/8 cases
```

## Mock mode

The default provider is the deterministic mock: it composes answers from
retrieval evidence (files, symbols, citations passed as context) without
any network or key. Every capability above is demonstrable offline.
