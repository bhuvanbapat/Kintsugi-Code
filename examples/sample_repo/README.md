# Campus Task Management (sample_repo)

A deliberately small-but-realistic Python application used to demonstrate
Kintsugi-Code end to end.

## Architecture

```
api/routes.py         HTTP route simulation (top layer)
  └─ services/task_service.py   business logic (service layer)
       ├─ services/validators.py   input validation
       └─ data/repositories.py     persistence (data layer)
tests/                pytest suite (one test fails by design)
```

## The intentional bug

`TaskService.complete_task` compares `task.status != "open"` but new tasks
are created with status `"todo"`, so completing any fresh task raises
`InvalidTaskError`. `tests/test_task_service.py::test_complete_todo_task_fails`
reproduces it. The Kintsugi-Code FIX demo locates, patches, and fixes it.

## Running tests

```
python -m pytest -q
```

Expected: 6 passed, 1 failed (test_complete_todo_task_fails) until the bug
is fixed.

