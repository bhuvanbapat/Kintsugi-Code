"""Campus Task Management — service layer.

NOTE: `complete_task` below contains an intentional defect: it compares
status against "open" instead of "todo", so completing any freshly created
task raises TaskNotFoundError. See tests/test_task_service.py.
"""
from __future__ import annotations

from data.repositories import Task, TaskRepository
from services.validators import validate_priority, validate_title


class TaskNotFoundError(Exception):
    pass


class InvalidTaskError(Exception):
    pass


class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self.repository = repository

    def create_task(self, title: str, priority: int = 1) -> Task:
        if not validate_title(title):
            raise InvalidTaskError("title must be 1..200 characters")
        if not validate_priority(priority):
            raise InvalidTaskError("priority must be 1, 2, or 3")
        return self.repository.add(title, priority)

    def complete_task(self, task_id: int) -> Task:
        task = self.repository.get(task_id)
        if task is None:
            raise TaskNotFoundError(f"task {task_id} not found")
        if task.status != "open":  # BUG: should be "todo"
            raise InvalidTaskError(f"task {task_id} is not completable from status {task.status}")
        task.status = "done"
        self.repository.save(task)
        return task

    def list_tasks(self, include_done: bool = True) -> list[Task]:
        tasks = self.repository.all()
        if include_done:
            return tasks
        return [t for t in tasks if t.status != "done"]
