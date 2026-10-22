"""Framework-neutral trace schema.

A *trajectory* is one episode of an agent: a list of messages exchanged between
the user, the agent and its tools, plus the episode outcome.  A *step* is one
agent decision, i.e. one assistant message; its ``history`` is every message
before it.  Everything downstream (situation keys, profiling, shadow calls,
tier assignment) works on steps, so any agent framework only needs an adapter
that produces trajectories (see :mod:`gdopt.adapters`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator, Literal

Role = Literal["user", "assistant", "tool"]

MESSAGE_ACTION = "message"
TOOL_PREFIX = "tool:"


def tool_action(name: str) -> str:
    return TOOL_PREFIX + name


def is_tool_action(action: str) -> bool:
    return action.startswith(TOOL_PREFIX)


def action_tool_name(action: str) -> str | None:
    return action[len(TOOL_PREFIX):] if is_tool_action(action) else None


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass
class Message:
    role: Role
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    # For role == "tool": which tool produced this result and whether it failed.
    tool_name: str | None = None
    error: bool = False
    # Agent-side cost of producing this message (only meaningful for assistant).
    cost: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def action(self) -> str | None:
        """Action label of an assistant message: ``message`` or ``tool:<name>``."""
        if self.role != "assistant":
            return None
        if self.tool_calls:
            return tool_action(self.tool_calls[0].name)
        return MESSAGE_ACTION


@dataclass
class Step:
    """One agent decision with the context it was taken in."""

    trajectory_id: str
    index: int  # position of the assistant message inside the trajectory
    history: list[Message]  # messages before this step (shared, do not mutate)
    message: Message

    @property
    def action(self) -> str:
        return self.message.action or MESSAGE_ACTION

    @property
    def tool_call(self) -> ToolCall | None:
        return self.message.tool_calls[0] if self.message.tool_calls else None

    @property
    def cost(self) -> float:
        return self.message.cost


@dataclass
class Trajectory:
    id: str
    task_id: str
    messages: list[Message]
    success: bool
    reward: float = 0.0
    trial: int = 0
    agent_cost: float = 0.0
    meta: dict[str, Any] = field(default_factory=dict)

    def steps(self) -> Iterator[Step]:
        for i, m in enumerate(self.messages):
            if m.role == "assistant":
                yield Step(self.id, i, self.messages[:i], m)

    @property
    def n_steps(self) -> int:
        return sum(1 for m in self.messages if m.role == "assistant")


def all_steps(trajectories: list[Trajectory]) -> list[Step]:
    return [s for t in trajectories for s in t.steps()]


def tool_names(trajectories: list[Trajectory]) -> list[str]:
    names: set[str] = set()
    for t in trajectories:
        for m in t.messages:
            for tc in m.tool_calls:
                names.add(tc.name)
    return sorted(names)
