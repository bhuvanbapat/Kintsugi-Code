"""Tests for the Campus Task Management sample app.

test_complete_todo_task_fails FAILS by design: TaskService.complete_task
compares status to "open" while new tasks have status "todo".
"""
from __future__ import annotations

import pytest

from data.repositories import Task, TaskRepository
from services.task_service import InvalidTaskError, TaskNotFoundError, TaskService


@pytest.fixture()
def repo() -> TaskRepository:
    return TaskRepository()


@pytest.fixture()
def service(repo: TaskRepository) -> TaskService:
    return TaskService(repo)


def test_create_task(service: TaskService) -> None:
    task = service.create_task("Finish lab report", priority=2)
    assert task.id == 1
    assert task.status == "todo"


def test_create_task_rejects_bad_title(service: TaskService) -> None:
    with pytest.raises(InvalidTaskError):
        service.create_task("")


def test_create_task_rejects_bad_priority(service: TaskService) -> None:
    with pytest.raises(InvalidTaskError):
        service.create_task("x", priority=5)


def test_repository_add_and_get(repo: TaskRepository) -> None:
    t = repo.add("Read chapter 3")
    assert repo.get(t.id) is t


def test_list_excludes_done(service: TaskService) -> None:
    service.create_task("A")
    task = service.create_task("B")
    task.status = "done"
    service.repository.save(task)
    visible = service.list_tasks(include_done=False)
    assert all(t.status != "done" for t in visible)


def test_complete_todo_task_fails(service: TaskService) -> None:
    """INTENTIONAL FAILURE: complete_task checks 'open' instead of 'todo'."""
    task = service.create_task("Submit assignment")
    completed = service.complete_task(task.id)
    assert completed.status == "done"


def test_complete_missing_task(service: TaskService) -> None:
    with pytest.raises(TaskNotFoundError):
        service.complete_task(999)
