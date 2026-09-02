"""Skill specs (§54) and the find_path tool."""
from __future__ import annotations

import pytest

from app.agent.skills import SKILLS, skill_for
from app.models.domain import TaskMode


def test_all_modes_have_skill_specs() -> None:
    assert set(SKILLS) == set(TaskMode)
    for mode, spec in SKILLS.items():
        assert spec.name and spec.purpose and spec.expected_output
        assert spec.allowed_tools, f"{mode} skill has no tools"
        assert spec.workflow, f"{mode} skill has no workflow"
        assert spec.failure_conditions, f"{mode} skill has no failure conditions"


def test_read_only_skills_have_no_modification_tools() -> None:
    modification = {"apply_patch", "write_file", "create_file"}
    for mode in (TaskMode.EXPLAIN, TaskMode.LOCATE, TaskMode.ANALYZE,
                 TaskMode.PLAN, TaskMode.TEST, TaskMode.REVIEW):
        assert not (SKILLS[mode].allowed_tools & modification), mode


def test_fix_skill_is_the_only_modifying_skill() -> None:
    modification = {"apply_patch", "write_file", "create_file"}
    assert SKILLS[TaskMode.FIX].allowed_tools & modification
    assert skill_for(TaskMode.FIX).name == "bug-fixing"


def test_engine_mode_tools_match_skill_specs() -> None:
    from app.agent.engine import MODE_TOOLS

    for mode in TaskMode:
        assert MODE_TOOLS[mode] == set(SKILLS[mode].allowed_tools), mode


@pytest.mark.asyncio
async def test_find_path_tool(indexed_repo, temp_store, sample_repo_copy):
    from app.tools.registry import ToolContext, build_default_registry

    registry = build_default_registry()
    ctx = ToolContext(repository=indexed_repo, store=temp_store,
                      root=sample_repo_copy.resolve())

    result = await registry.execute("find_path", ctx, {
        "from": "api/routes.py", "to": "data/repositories.py"})
    assert result["ok"] is True
    body = result["result"]
    assert body["found"] is True
    # routes.py imports data.repositories directly (TaskRepository) —
    # the shortest chain is one hop, not via the service layer.
    assert body["path"] == ["api/routes.py", "data/repositories.py"]
    assert body["hops"] == 1


@pytest.mark.asyncio
async def test_find_path_unreachable(indexed_repo, temp_store, sample_repo_copy):
    from app.tools.registry import ToolContext, build_default_registry

    registry = build_default_registry()
    ctx = ToolContext(repository=indexed_repo, store=temp_store,
                      root=sample_repo_copy.resolve())
    # repositories.py does not import routes.py — no chain should exist.
    result = await registry.execute("find_path", ctx, {
        "from": "data/repositories.py", "to": "api/routes.py"})
    assert result["ok"] is True
    assert result["result"]["found"] is False


@pytest.mark.asyncio
async def test_find_path_validates_inputs(indexed_repo, temp_store, sample_repo_copy):
    from app.tools.registry import ToolContext, build_default_registry

    registry = build_default_registry()
    ctx = ToolContext(repository=indexed_repo, store=temp_store,
                      root=sample_repo_copy.resolve())
    result = await registry.execute("find_path", ctx, {"from": "nope.py", "to": "api/routes.py"})
    assert result["ok"] is False
    assert "indexed source files" in result["error"]


def test_skill_documentation_endpoint(client, indexed_repo):
    """Skills are exposed via the tools list for transparency."""
    r = client.get("/api/tools")
    assert r.status_code == 200
    names = [t["name"] for t in r.json()["tools"]]
    assert "find_path" in names
