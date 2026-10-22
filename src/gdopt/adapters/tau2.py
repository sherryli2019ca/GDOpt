"""Adapter for τ²-bench result files.

τ²-bench (https://github.com/sierra-research/tau2-bench) stores every run as a
JSON file with ``info``, ``tasks`` and ``simulations``; each simulation has a
``messages`` list (user / assistant / tool) and ``reward_info``.  The agent is a
single LLM call per turn that either sends a message or makes one tool call, so
every assistant message is one step.  The repository ships result files under
``data/tau2/results/final/`` which are enough for the offline stages of GDOpt
(static identification and trace profiling).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..trace import Message, ToolCall, Trajectory


def _message(raw: dict[str, Any], tool_name_by_call_id: dict[str, str]) -> Message | None:
    role = raw.get("role")
    usage = raw.get("usage") or {}
    if role == "assistant":
        calls = [ToolCall(tc["name"], dict(tc.get("arguments") or {})) for tc in raw.get("tool_calls") or []]
        for tc_raw in raw.get("tool_calls") or []:
            tool_name_by_call_id[tc_raw.get("id", "")] = tc_raw["name"]
        return Message(
            role="assistant",
            content=raw.get("content"),
            tool_calls=calls,
            cost=float(raw.get("cost") or 0.0),
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
        )
    if role == "user":
        return Message(role="user", content=raw.get("content"))
    if role == "tool":
        if raw.get("requestor", "assistant") != "assistant":
            return None  # user-side tools (telecom) are not agent decisions
        return Message(
            role="tool",
            content=raw.get("content"),
            tool_name=tool_name_by_call_id.get(raw.get("id", ""), "?"),
            error=bool(raw.get("error", False)),
        )
    return None


def load_results(path: str | Path, agent_only: bool = True) -> list[Trajectory]:
    """Load a τ²-bench results JSON into trajectories."""
    data = json.loads(Path(path).read_text())
    out: list[Trajectory] = []
    for sim in data.get("simulations", []):
        by_id: dict[str, str] = {}
        msgs: list[Message] = []
        for raw in sim.get("messages") or []:
            if agent_only and raw.get("role") == "user" and raw.get("tool_calls"):
                continue
            m = _message(raw, by_id)
            if m is not None:
                msgs.append(m)
        reward = float((sim.get("reward_info") or {}).get("reward") or 0.0)
        out.append(
            Trajectory(
                id=str(sim.get("id")),
                task_id=str(sim.get("task_id")),
                messages=msgs,
                success=reward >= 1.0,
                reward=reward,
                trial=int(sim.get("trial") or 0),
                agent_cost=float(sim.get("agent_cost") or 0.0),
                meta={"termination_reason": sim.get("termination_reason"), "seed": sim.get("seed")},
            )
        )
    return out


def load_gold_actions(path: str | Path) -> dict[str, list[tuple[str, dict[str, Any]]]]:
    """Expected agent tool calls per task (``evaluation_criteria.actions``).

    τ²-bench grades a task by database state, but it also lists the tool calls
    the reference solution makes.  They are a free local oracle: an action a
    decision model proposes can be checked against them without running
    anything.
    """
    data = json.loads(Path(path).read_text())
    out: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for task in data.get("tasks", []):
        crit = task.get("evaluation_criteria") or {}
        gold = [
            (a["name"], dict(a.get("arguments") or {}))
            for a in crit.get("actions") or []
            if a.get("requestor", "assistant") == "assistant"
        ]
        out[str(task.get("id"))] = gold
    return out


def results_info(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text())
    info = data.get("info", {})
    return {
        "agent_llm": (info.get("agent_info") or {}).get("llm"),
        "user_llm": (info.get("user_info") or {}).get("llm"),
        "num_trials": info.get("num_trials"),
        "n_tasks": len(data.get("tasks", [])),
        "n_simulations": len(data.get("simulations", [])),
    }
