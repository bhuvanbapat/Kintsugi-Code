"""Controlled engineering agent.

State machine (AgentState) with validated transitions, bounded iterations,
tool-use policy per task mode, loop/no-progress detection, and full tracing.
The agent never edits files unless execution_mode allows it; even then every
modification goes through diff generation and optional validation.
"""
from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.agent.state_machine import AgentStateMachine
from app.core.config import get_settings
from app.core.logging import get_logger
from app.llm.providers import LLMProvider, get_provider
from app.models.domain import (
    AgentRun,
    AgentState,
    EvidenceCitation,
    ExecutionMode,
    TaskMode,
    ToolCallRecord,
)
from app.retrieval.context_engine import ContextEngine
from app.services.rag_service import get_retriever
from app.services.store import Store
from app.tools.registry import ToolContext, ToolRegistry, build_default_registry

log = get_logger(__name__)

# Tool policy per task mode — read-only modes never touch modification tools.
MODE_TOOLS: dict[TaskMode, set[str]] = {
    TaskMode.EXPLAIN: {"read_file", "list_files", "search_code", "search_symbols", "get_symbol",
                       "get_repository_map", "get_dependencies", "get_git_status", "get_git_history"},
    TaskMode.LOCATE: {"read_file", "list_files", "search_code", "search_symbols", "get_symbol",
                      "get_dependencies"},
    TaskMode.ANALYZE: {"read_file", "search_code", "search_symbols", "get_symbol", "get_repository_map",
                       "get_dependencies", "run_tests", "get_git_diff"},
    TaskMode.PLAN: {"read_file", "list_files", "search_code", "search_symbols", "get_symbol",
                    "get_repository_map", "get_dependencies", "run_tests", "inspect_project_config"},
    TaskMode.TEST: {"run_tests", "read_file", "search_code", "search_symbols", "inspect_project_config"},
    TaskMode.FIX: {"read_file", "search_code", "search_symbols", "get_symbol", "run_tests",
                   "apply_patch", "write_file", "create_file", "get_git_diff"},
    TaskMode.REVIEW: {"read_file", "list_files", "search_code", "search_symbols", "get_symbol",
                      "get_git_diff", "get_git_status", "run_tests"},
}

EXECUTION_MODES_ALLOW_MODIFICATION = {ExecutionMode.CONTROLLED_EXECUTION}


class Agent:
    def __init__(self, store: Store, provider: LLMProvider | None = None,
                 registry: ToolRegistry | None = None) -> None:
        self.store = store
        self.settings = get_settings()
        self.provider = provider or get_provider()
        self.registry = registry or build_default_registry()

    async def run(self, repository_id: str, task: str, mode: TaskMode,
                  execution_mode: ExecutionMode = ExecutionMode.ANALYSIS_ONLY,
                  max_iterations: int | None = None) -> AgentRun:
        repo = self.store.get_repository(repository_id)
        if repo is None:
            raise ValueError(f"unknown repository: {repository_id}")
        run = AgentRun(
            repository_id=repository_id, task=task, mode=mode,
            execution_mode=execution_mode,
            max_iterations=max_iterations or self.settings.agent_max_iterations,
        )
        sm = AgentStateMachine(run)
        ctx = ToolContext(repository=repo, store=self.store, root=Path(repo.root_path).resolve())

        allowed_tools = MODE_TOOLS[mode].copy()
        if execution_mode not in EXECUTION_MODES_ALLOW_MODIFICATION:
            # Strip every file-mutating tool outside controlled execution.
            allowed_tools = {
                t for t in allowed_tools
                if not self.registry.get(t).modifies_files
            }

        retriever = get_retriever(repository_id)
        if retriever is None:
            run.state = AgentState.FAILED
            run.status_message = "repository not indexed"
            self.store.save_run(run)
            return run
        engine = ContextEngine(retriever)

        seen_calls: list[tuple[str, str]] = []
        no_progress = 0
        total_input_tokens = 0
        total_output_tokens = 0
        all_evidence: list[EvidenceCitation] = []

        try:
            sm.transition(AgentState.ANALYZING)
            sm.transition(AgentState.RETRIEVING)
            context = engine.build_context(task)
            context["task_mode"] = mode.value
            all_evidence.extend(EvidenceCitation(**c) for c in context["citations"])

            sm.transition(AgentState.PLANNING)

            # Iterative tool loop: each iteration picks at most one follow-up tool
            # based on mode heuristics, executes it, expands context, stops on
            # completion/no-progress/max-iterations.
            iterations = 0
            while iterations < run.max_iterations:
                iterations += 1
                run.iterations = iterations
                next_tool = self._select_next_tool(mode, context, seen_calls, iterations)
                if next_tool is None:
                    break
                tool_name, args = next_tool
                call_key = (tool_name, str(sorted(args.items())))
                if call_key in seen_calls:
                    no_progress += 1
                    if no_progress >= 2:
                        break
                    continue
                seen_calls.append(call_key)
                if tool_name not in allowed_tools:
                    log.info("tool %s not allowed in mode %s — skipping", tool_name, mode)
                    continue
                sm.transition(AgentState.EXECUTING)
                start = time.monotonic()
                outcome = await self._execute_tool_safely(tool_name, ctx, args, run)
                duration_ms = int((time.monotonic() - start) * 1000)
                record = ToolCallRecord(
                    run_id=run.id, tool_name=tool_name, arguments=args,
                    result_summary=_summarize(outcome), duration_ms=duration_ms,
                    error=outcome.get("error"),
                )
                run.tool_calls.append(record)
                if not outcome.get("ok"):
                    no_progress += 1
                    if no_progress >= 3:
                        run.status_message = "stopped: repeated tool failures"
                        break
                else:
                    no_progress = 0
                    self._absorb_tool_result(context, tool_name, outcome)
                if mode == TaskMode.TEST and tool_name == "run_tests":
                    sm.transition(AgentState.TESTING)
                    break

            # Compose final answer via provider.
            sm.transition(AgentState.ANALYZING)
            response = await self.provider.complete(
                system=self._system_prompt(mode, allowed_tools),
                prompt=task,
                context=context,
            )
            total_input_tokens += response.input_tokens or 0
            total_output_tokens += response.output_tokens or 0
            if response.usage.get("available"):
                pass
            run.result = response.content
            run.evidence = all_evidence
            run.usage = {
                "provider": response.provider,
                "model": response.model,
                "input_tokens": total_input_tokens or None,
                "output_tokens": total_output_tokens or None,
                "usage_available": response.usage.get("available", False),
                "requests": 1,
            }
            sm.transition(AgentState.COMPLETED)
            run.status_message = "completed"
        except Exception as exc:  # noqa: BLE001
            run.state = AgentState.FAILED
            run.status_message = f"agent error: {exc}"
            log.exception("agent run failed")
        run.finished_at = datetime.now(UTC)
        self.store.save_run(run)
        return run

    # ------------------------------------------------------------------
    def _select_next_tool(self, mode: TaskMode, context: dict, seen: list, iteration: int):
        """Deterministic, explainable tool-selection policy."""
        if iteration == 1:
            if mode in (TaskMode.TEST, TaskMode.FIX):
                return ("run_tests", {})
            if mode == TaskMode.REVIEW:
                return ("get_git_diff", {})
            if mode == TaskMode.LOCATE:
                return ("search_symbols", {"query": context["query"]})
            return ("get_repository_map", {})
        # Later iterations: fill gaps.
        if mode in (TaskMode.TEST, TaskMode.FIX):
            files = context.get("files") or []
            if files:
                return ("read_file", {"path": files[0]["path"],
                                      "start_line": files[0].get("start_line", 1),
                                      "end_line": (files[0].get("start_line", 1) + 40)})
            return None
        if mode in (TaskMode.EXPLAIN, TaskMode.ANALYZE, TaskMode.PLAN):
            ranked = context.get("retrieval_stats", {})
            if iteration == 2 and ranked.get("symbol_hits", 0) > 0:
                return ("get_dependencies", {})
            if iteration == 2:
                return ("get_git_status", {})
        return None

    async def _execute_tool_safely(self, name: str, ctx: ToolContext, args: dict,
                                   run: AgentRun) -> dict[str, Any]:
        try:
            return await asyncio.wait_for(
                self.registry.execute(name, ctx, args),
                self.settings.tool_timeout_seconds,
            )
        except TimeoutError:
            return {"ok": False,
                    "error": f"tool timeout after {self.settings.tool_timeout_seconds}s"}

    def _absorb_tool_result(self, context: dict, tool_name: str, outcome: dict) -> None:
        """Merge useful tool output into LLM context (bounded)."""
        result = outcome.get("result", {})
        if tool_name == "run_tests":
            context["test_results"] = {
                k: result.get(k) for k in ("ok", "exit_code", "passed", "failed",
                                           "errors", "failed_tests", "stdout")
                if k in result
            }
        elif tool_name == "get_repository_map":
            context["repo_map_summary"] = {
                "file_count": result.get("file_count"),
                "symbol_count": result.get("symbol_count"),
                "files": [f["path"] for f in (result.get("files") or [])[:40]],
            }
        elif tool_name == "get_dependencies":
            context["dependencies"] = (result.get("dependencies") or [])[:80]
        elif tool_name == "get_git_diff":
            context["git_diff"] = (result.get("diff") or "")[:4000]
        elif tool_name == "get_git_status":
            context["git_status"] = (result.get("entries") or [])[:50]
        elif tool_name == "read_file":
            context.setdefault("files", []).append({
                "path": result.get("path"), "start_line": result.get("start_line"),
                "end_line": result.get("end_line"), "snippet": (result.get("content") or "")[:3000],
            })
        elif tool_name == "search_symbols":
            context["symbol_results"] = (result.get("symbol_results") or [])[:40]

    def _system_prompt(self, mode: TaskMode, allowed_tools: set[str]) -> str:
        base = (
            "You are CodeForge, a repository-aware software engineering assistant. "
            "Answer grounded ONLY in the provided context. Cite files as path:line. "
            "Mark statements as CONFIRMED FROM CODE, INFERENCE, or UNCERTAINTY. "
            "Never invent files, symbols, or line numbers.\n"
        )
        mode_text = {
            TaskMode.EXPLAIN: "Task: explain the requested part of the codebase with evidence.",
            TaskMode.LOCATE: "Task: locate where the requested functionality is implemented.",
            TaskMode.ANALYZE: "Task: analyze the reported problem and identify likely causes.",
            TaskMode.PLAN: "Task: produce an implementation plan with steps and affected files.",
            TaskMode.TEST: "Task: run tests and summarize results.",
            TaskMode.FIX: "Task: propose a fix with an exact diff after diagnosing failures.",
            TaskMode.REVIEW: "Task: review the current diff for correctness and risks.",
        }
        return base + mode_text[mode] + f"\nAllowed tools: {', '.join(sorted(allowed_tools))}."


def _summarize(outcome: dict) -> str:
    if not outcome.get("ok"):
        return f"error: {outcome.get('error', 'unknown')[:120]}"
    result = outcome.get("result", {})
    if isinstance(result, dict):
        for key in ("total", "symbol_count", "file_count", "modified", "passed", "failed", "bytes"):
            if key in result:
                return f"{key}={result[key]}"
        if "symbols" in result:
            return f"{len(result['symbols'])} symbols"
        if "files" in result:
            return f"{len(result['files'])} files"
        if "diff" in result:
            return f"diff {len(result['diff'])} chars"
    return "ok"
