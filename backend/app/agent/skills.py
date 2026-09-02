"""Product-level agent skills (directive §54).

Each TaskMode maps to a SkillSpec: purpose, inputs, permitted tools,
workflow, expected output, failure conditions. The agent engine consumes
these specs directly (tool policy + system prompt), so a skill is never
documentation-only — it is the executable contract for that mode.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.models.domain import TaskMode


@dataclass(frozen=True)
class SkillSpec:
    name: str
    purpose: str
    inputs: tuple[str, ...]
    allowed_tools: frozenset[str]
    workflow: tuple[str, ...]
    expected_output: str
    failure_conditions: tuple[str, ...]


_READ_BASE = frozenset({
    "read_file", "list_files", "search_code", "search_symbols", "get_symbol",
})

SKILLS: dict[TaskMode, SkillSpec] = {
    TaskMode.EXPLAIN: SkillSpec(
        name="repository-analysis",
        purpose="Explain a requested part of the codebase with file:line evidence.",
        inputs=("question", "repository"),
        allowed_tools=_READ_BASE | {
            "get_repository_map", "get_dependencies", "get_git_status", "get_git_history",
        },
        workflow=(
            "survey the repository map",
            "retrieve candidate files and symbols",
            "read the most relevant definitions",
            "synthesize an evidence-cited explanation",
        ),
        expected_output="Explanation grounded in indexed files, with citations as path:line.",
        failure_conditions=(
            "repository not indexed",
            "no retrieval evidence matches the question",
        ),
    ),
    TaskMode.LOCATE: SkillSpec(
        name="symbol-location",
        purpose="Locate where requested functionality is defined.",
        inputs=("query", "repository"),
        allowed_tools=_READ_BASE | {"get_dependencies", "find_path"},
        workflow=(
            "search symbols for the requested name",
            "fall back to lexical search",
            "confirm by reading the definition site",
        ),
        expected_output="Concrete file:line locations of the definition.",
        failure_conditions=("symbol not found in the index",),
    ),
    TaskMode.ANALYZE: SkillSpec(
        name="failure-analysis",
        purpose="Diagnose a reported problem or failure and rank likely causes.",
        inputs=("symptom or question", "repository"),
        allowed_tools=_READ_BASE | {
            "get_repository_map", "get_dependencies", "find_path", "run_tests", "get_git_diff",
        },
        workflow=(
            "reproduce or observe the failure (tests, diff)",
            "retrieve the code involved",
            "trace dependency chains between affected files",
            "inspect the relevant definitions",
            "rank likely causes with evidence",
        ),
        expected_output="Likely cause(s) with supporting code citations.",
        failure_conditions=("failure cannot be reproduced", "relevant code not found"),
    ),
    TaskMode.PLAN: SkillSpec(
        name="implementation-planning",
        purpose="Produce an implementation plan for a requested change.",
        inputs=("goal", "repository"),
        allowed_tools=_READ_BASE | {
            "get_repository_map", "get_dependencies", "find_path", "run_tests",
            "inspect_project_config",
        },
        workflow=(
            "survey affected modules",
            "read current implementations",
            "enumerate ordered steps with files to touch",
            "note risks and test strategy",
        ),
        expected_output="Ordered plan listing affected files and validation steps.",
        failure_conditions=("goal is ambiguous", "affected area cannot be determined"),
    ),
    TaskMode.TEST: SkillSpec(
        name="test-analysis",
        purpose="Run the repository's test suite and summarize results.",
        inputs=("optional scope", "repository"),
        allowed_tools=frozenset({
            "run_tests", "read_file", "search_code", "search_symbols",
            "inspect_project_config",
        }),
        workflow=(
            "detect the project ecosystem",
            "run tests with timeout",
            "parse pass/fail counts and failing test names",
            "summarize with output excerpts",
        ),
        expected_output="Structured pass/fail summary with failing tests listed.",
        failure_conditions=("unknown project type", "tests time out", "runner missing"),
    ),
    TaskMode.FIX: SkillSpec(
        name="bug-fixing",
        purpose="Diagnose failing tests and propose a validated patch.",
        inputs=("failing symptom or test", "repository"),
        allowed_tools=_READ_BASE | {
            "run_tests", "apply_patch", "write_file", "create_file", "get_git_diff",
        },
        workflow=(
            "run tests to reproduce the failure",
            "retrieve and read the failing code",
            "propose a minimal diff",
            "state the expected test outcome after the change",
        ),
        expected_output="A proposed unified diff with rationale; applied only via the controlled endpoint.",
        failure_conditions=(
            "tests still fail after the proposed change",
            "root cause cannot be isolated",
        ),
    ),
    TaskMode.REVIEW: SkillSpec(
        name="code-review",
        purpose="Review the current diff for correctness and risks.",
        inputs=("diff (from git)", "repository"),
        allowed_tools=_READ_BASE | {"get_git_diff", "get_git_status", "run_tests"},
        workflow=(
            "read the working-tree diff",
            "retrieve surrounding code for context",
            "identify correctness, security, and maintainability issues",
            "give a verdict with findings",
        ),
        expected_output="Findings referencing diff hunks, each with severity and suggestion.",
        failure_conditions=("no diff present", "diff too large to review"),
    ),
}


def skill_for(mode: TaskMode) -> SkillSpec:
    return SKILLS[mode]
