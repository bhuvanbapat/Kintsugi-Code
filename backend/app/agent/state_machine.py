"""Agent state machine with validated transitions."""
from __future__ import annotations

from app.models.domain import AgentRun, AgentState

# Valid transitions — invalid ones raise instead of silently corrupting run state.
TRANSITIONS: dict[AgentState, set[AgentState]] = {
    AgentState.IDLE: {AgentState.ANALYZING, AgentState.CANCELLED},
    AgentState.ANALYZING: {AgentState.RETRIEVING, AgentState.PLANNING, AgentState.EXECUTING,
                           AgentState.FAILED, AgentState.CANCELLED, AgentState.COMPLETED},
    AgentState.RETRIEVING: {AgentState.PLANNING, AgentState.ANALYZING, AgentState.FAILED,
                            AgentState.CANCELLED},
    AgentState.PLANNING: {AgentState.EXECUTING, AgentState.ANALYZING, AgentState.FAILED,
                          AgentState.CANCELLED, AgentState.COMPLETED},
    AgentState.EXECUTING: {AgentState.TESTING, AgentState.DIAGNOSING, AgentState.PLANNING,
                           AgentState.ANALYZING, AgentState.COMPLETED, AgentState.FAILED,
                           AgentState.CANCELLED, AgentState.ITERATING},
    AgentState.TESTING: {AgentState.DIAGNOSING, AgentState.ANALYZING, AgentState.COMPLETED,
                         AgentState.FAILED, AgentState.CANCELLED, AgentState.ITERATING},
    AgentState.DIAGNOSING: {AgentState.PLANNING, AgentState.EXECUTING, AgentState.COMPLETED,
                            AgentState.FAILED, AgentState.CANCELLED},
    AgentState.ITERATING: {AgentState.ANALYZING, AgentState.PLANNING, AgentState.EXECUTING,
                           AgentState.FAILED, AgentState.CANCELLED, AgentState.COMPLETED},
    AgentState.COMPLETED: set(),
    AgentState.FAILED: set(),
    AgentState.CANCELLED: set(),
}


class AgentStateMachine:
    def __init__(self, run: AgentRun) -> None:
        self.run = run

    def can(self, to_state: AgentState) -> bool:
        return to_state in TRANSITIONS[self.run.state]

    def transition(self, to_state: AgentState) -> None:
        if self.run.state == to_state:
            return  # idempotent self-transition
        if to_state not in TRANSITIONS[self.run.state]:
            raise ValueError(f"invalid transition {self.run.state.value} -> {to_state.value}")
        self.run.state = to_state
        self.run.status_message = to_state.value
