"""Campus Task Management — validation helpers."""
from __future__ import annotations


def validate_priority(priority: int) -> bool:
    """Return True when priority is within the allowed 1..3 range."""
    return isinstance(priority, int) and priority in (1, 2, 3)


def validate_title(title: str) -> bool:
    """Titles must be non-empty and at most 200 characters."""
    return isinstance(title, str) and 0 < len(title.strip()) <= 200
