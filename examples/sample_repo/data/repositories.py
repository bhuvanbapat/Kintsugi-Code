"""Campus Task Management — data layer (in-memory repositories).

A small realistic sample application used to demonstrate Kintsugi-Code. It
intentionally contains one defect in the service layer
(`TaskService.complete_task`) that causes `tests/test_task_service.py::test_complete_todo_task_fails`
to fail — the demo shows Kintsugi-Code finding and fixing it.
"""
from __future__ import annotations

from typing import Optional


class Task:
    def __init__(self, task_id: int, title: str, priority: int = 1,
                 status: str = "todo") -> None:
        if priority not in (1, 2, 3):
            raise ValueError("priority must be 1, 2, or 3")
        self.id = task_id
        self.title = title
        self.priority = priority
        self.status = status

    def __repr__(self) -> str:  # pragma: no cover
        return f"Task(id={self.id}, title={self.title!r}, status={self.status})"


class TaskRepository:
    """In-memory persistence for Task entities."""

    def __init__(self) -> None:
        self._tasks: dict[int, Task] = {}
        self._next_id = 1

    def add(self, title: str, priority: int = 1) -> Task:
        task = Task(self._next_id, title, priority)
        self._tasks[task.id] = task
        self._next_id += 1
        return task

    def get(self, task_id: int) -> Optional[Task]:
        return self._tasks.get(task_id)

    def all(self) -> list[Task]:
        return list(self._tasks.values())

    def save(self, task: Task) -> None:
        self._tasks[task.id] = task

    def delete(self, task_id: int) -> bool:
        return self._tasks.pop(task_id, None) is not None

