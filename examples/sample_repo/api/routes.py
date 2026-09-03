"""Campus Task Management — HTTP API routes (framework-free simulation)."""
from __future__ import annotations

import json
from typing import Any

from data.repositories import TaskRepository
from services.task_service import InvalidTaskError, TaskNotFoundError, TaskService


def make_app(repository: TaskRepository) -> dict[str, Any]:
    service = TaskService(repository)
    routes: dict[str, Any] = {}

    def list_tasks(include_done: str = "true") -> dict[str, Any]:
        tasks = service.list_tasks(include_done != "false")
        return {"ok": True, "tasks": [vars(t) | {"id": t.id} for t in tasks]}

    def create_task(body: str) -> dict[str, Any]:
        payload = json.loads(body)
        try:
            task = service.create_task(payload["title"], payload.get("priority", 1))
        except InvalidTaskError as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "task": vars(task)}

    def complete_task(task_id: int) -> dict[str, Any]:
        try:
            task = service.complete_task(task_id)
        except (TaskNotFoundError, InvalidTaskError) as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "task": vars(task)}

    routes["GET /tasks"] = list_tasks
    routes["POST /tasks"] = create_task
    routes["POST /tasks/%d/complete"] = complete_task
    return routes
