"""A toy τ²-style customer-service environment for tests and demos.

Three task kinds: cancel a reservation (allowed, needs confirmation), refund
insurance (not allowed -> transfer), flight status (read-only).  A scripted
user simulator and a scripted, slightly noisy "LLM" policy produce traces with
the same shape as τ²-bench: one agent decision per turn, either a message or a
tool call.  ``simulated_decision_model`` plays the role of Jev with a chosen
accuracy, so the whole pipeline (profile -> tiers -> calibrate -> evaluate)
can run offline.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Any

from .decision import FunctionDecisionModel
from .replay import EpisodeResult, Policy
from .trace import MESSAGE_ACTION, Message, ToolCall, Trajectory, tool_action

TOOLS = {
    "get_user_details": "Look up a user profile by user_id.",
    "get_reservation_details": "Look up a reservation by reservation_id.",
    "cancel_reservation": "Cancel a reservation by reservation_id. Requires explicit user confirmation first.",
    "get_flight_status": "Get the status of flight_number on date.",
    "transfer_to_human_agents": "Transfer the user to a human agent with a summary.",
}
POLICY_TEXT = (
    "Cancel reservations only after listing the details and getting an explicit yes. "
    "Travel insurance cannot be refunded; transfer such requests to a human agent. "
    "Flight status can be given directly."
)
STOP = "###STOP###"
KINDS = ("cancel", "refund", "status")


@dataclass
class ToyTask:
    id: str
    kind: str
    user_id: str
    reservation_id: str
    flight_number: str
    date: str


def make_tasks(n: int, seed: int = 0) -> list[ToyTask]:
    rng = random.Random(seed)
    tasks = []
    for i in range(n):
        kind = KINDS[i % len(KINDS)]
        res = "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ0123456789") for _ in range(6))
        tasks.append(ToyTask(str(i), kind, f"user_{rng.randint(1000, 9999)}", res, f"HAT{rng.randint(100, 999)}", f"2024-05-{rng.randint(10, 28):02d}"))
    return tasks


# ---------------------------------------------------------------- environment


@dataclass
class ToyEnv:
    task: ToyTask
    cancelled: bool = False
    confirmed: bool = False
    transferred: bool = False
    log: list[str] = field(default_factory=list)

    def call(self, tc: ToolCall) -> Message:
        a = tc.arguments
        t = self.task
        if tc.name == "get_user_details":
            if a.get("user_id") != t.user_id:
                return Message("tool", content='{"error": "user not found"}', tool_name=tc.name, error=True)
            return Message("tool", content=f'{{"user_id": "{t.user_id}", "membership": "silver", "reservations": ["{t.reservation_id}"]}}', tool_name=tc.name)
        if tc.name == "get_reservation_details":
            if a.get("reservation_id") != t.reservation_id:
                return Message("tool", content='{"error": "reservation not found"}', tool_name=tc.name, error=True)
            status = "cancelled" if self.cancelled else "active"
            return Message("tool", content=f'{{"reservation_id": "{t.reservation_id}", "user_id": "{t.user_id}", "flight_number": "{t.flight_number}", "date": "{t.date}", "insurance": "yes", "status": "{status}"}}', tool_name=tc.name)
        if tc.name == "cancel_reservation":
            if a.get("reservation_id") != t.reservation_id:
                return Message("tool", content='{"error": "reservation not found"}', tool_name=tc.name, error=True)
            self.cancelled = True
            return Message("tool", content=f'{{"reservation_id": "{t.reservation_id}", "status": "cancelled"}}', tool_name=tc.name)
        if tc.name == "get_flight_status":
            if a.get("flight_number") != t.flight_number:
                return Message("tool", content='{"error": "flight not found"}', tool_name=tc.name, error=True)
            return Message("tool", content=f'{{"flight_number": "{t.flight_number}", "date": "{a.get("date")}", "status": "on time"}}', tool_name=tc.name)
        if tc.name == "transfer_to_human_agents":
            self.transferred = True
            return Message("tool", content="Transfer successful", tool_name=tc.name)
        return Message("tool", content='{"error": "unknown tool"}', tool_name=tc.name, error=True)

    def success(self, messages: list[Message]) -> bool:
        k = self.task.kind
        if k == "cancel":
            return self.cancelled and self.confirmed
        if k == "refund":
            return self.transferred and not self.cancelled
        last = [m for m in messages if m.role == "assistant" and m.content]
        return (not self.cancelled) and any("on time" in m.content for m in last)


def user_reply(task: ToyTask, agent_text: str, turn: int) -> str:
    t = agent_text.lower()
    if turn == 0:
        return {
            "cancel": "Hi, I need to cancel my reservation.",
            "refund": "Hi, I want a refund for the travel insurance on my reservation.",
            "status": "Hi, can you tell me the status of my flight?",
        }[task.kind]
    if "transferred" in t or "cancelled" in t or "on time" in t or "cannot" in t:
        return f"Thanks, that's all. {STOP}"
    if "confirm" in t:
        return "Yes, please go ahead."
    if "user id" in t or "reservation" in t or "flight" in t:
        if task.kind == "status":
            return f"It's flight {task.flight_number} on {task.date}."
        return f"My user id is {task.user_id} and the reservation is {task.reservation_id}."
    return "Okay."


# ---------------------------------------------------------------- agent policies


def _known(history: list[Message], pattern: str) -> str | None:
    for m in reversed(history):
        if m.role == "user" and m.content:
            mm = re.search(pattern, m.content)
            if mm:
                return mm.group(0)
    return None


def _called(history: list[Message], tool: str) -> bool:
    return any(tc.name == tool for m in history for tc in m.tool_calls)


def _last_tool_ok(history: list[Message], tool: str) -> bool:
    return any(m.role == "tool" and m.tool_name == tool and not m.error for m in history)


def ideal_action(history: list[Message]) -> tuple[str, dict[str, Any], str]:
    """The policy-following next action: (action, args, message text)."""
    first = next((m.content or "" for m in history if m.role == "user"), "")
    kind = "refund" if "insurance" in first else "status" if "status" in first else "cancel"
    res = _known(history, r"[A-Z0-9]{6}")
    user = _known(history, r"user_\d{4}")
    flight = _known(history, r"HAT\d{3}")
    date = _known(history, r"\d{4}-\d{2}-\d{2}")
    prev = history[-1] if history else None
    if kind == "status":
        if not (flight and date):
            return MESSAGE_ACTION, {}, "Sure, which flight number and date?"
        if not _last_tool_ok(history, "get_flight_status"):
            return tool_action("get_flight_status"), {"flight_number": flight, "date": date}, ""
        return MESSAGE_ACTION, {}, f"Flight {flight} on {date} is on time."
    if not (res and user):
        return MESSAGE_ACTION, {}, "I can help. Please give me your user id and reservation id."
    if not _last_tool_ok(history, "get_reservation_details"):
        return tool_action("get_reservation_details"), {"reservation_id": res}, ""
    if kind == "refund":
        if not _last_tool_ok(history, "transfer_to_human_agents"):
            return tool_action("transfer_to_human_agents"), {"summary": "insurance refund request"}, ""
        return MESSAGE_ACTION, {}, "Insurance cannot be refunded; you are being transferred to a human agent."
    if _last_tool_ok(history, "cancel_reservation"):
        return MESSAGE_ACTION, {}, f"Your reservation {res} has been cancelled."
    if prev is not None and prev.role == "user" and re.search(r"\byes\b", prev.content or "", re.I):
        return tool_action("cancel_reservation"), {"reservation_id": res}, ""
    return MESSAGE_ACTION, {}, f"Please confirm: cancel reservation {res} for user {user}? Reply yes to confirm."


def _message_from(action: str, args: dict[str, Any], text: str, history: list[Message], usd_per_token: float) -> Message:
    prompt_tokens = 500 + sum(len(m.content or "") for m in history) // 4
    cost = usd_per_token * (prompt_tokens + 40)
    if action == MESSAGE_ACTION:
        return Message("assistant", content=text, cost=cost, prompt_tokens=prompt_tokens, completion_tokens=40)
    return Message("assistant", tool_calls=[ToolCall(action[len("tool:"):], args)], cost=cost, prompt_tokens=prompt_tokens, completion_tokens=40)


def make_llm_policy(seed: int = 0, detour_rate: float = 0.25, skip_confirm_rate: float = 0.05, usd_per_token: float = 2e-6) -> Policy:
    """A noisy version of the ideal policy, standing in for the original LLM agent.

    * detours: sometimes looks up the user profile before the reservation;
    * errors: sometimes skips the confirmation and cancels directly (a policy
      violation that fails the task).
    """
    rng = random.Random(seed)

    def policy(history: list[Message]) -> Message:
        action, args, text = ideal_action(history)
        user = _known(history, r"user_\d{4}")
        if action == tool_action("get_reservation_details") and user and not _called(history, "get_user_details") and rng.random() < detour_rate:
            action, args = tool_action("get_user_details"), {"user_id": user}
        elif action == MESSAGE_ACTION and "confirm" in text and rng.random() < skip_confirm_rate:
            action, args, text = tool_action("cancel_reservation"), {"reservation_id": _known(history, r"[A-Z0-9]{6}")}, ""
        return _message_from(action, args, text, history, usd_per_token)

    return policy


def simulated_decision_model(accuracy: float = 0.95, seed: int = 0, cost_per_call: float = 1e-5) -> FunctionDecisionModel:
    """Stands in for Jev: knows the ideal action with probability ``accuracy``."""
    rng = random.Random(seed)

    def fn(options: dict[str, str], state: Any) -> dict[str, float]:
        conv = state["conversation"]
        history = [
            Message("assistant", tool_calls=[ToolCall(c["tool_call"]["name"], c["tool_call"]["arguments"])]) if "tool_call" in c
            else Message("tool", content=c.get("result"), tool_name=c.get("tool"), error=bool(c.get("error"))) if c["role"] == "tool"
            else Message(c["role"], content=c.get("content"))
            for c in conv
        ]
        ideal, _, _ = ideal_action(history)
        labels = list(options)
        if rng.random() < accuracy:
            top, p = ideal, rng.uniform(0.8, 0.99)
        else:
            top, p = rng.choice([l for l in labels if l != ideal] or labels), rng.uniform(0.5, 0.85)
        rest = (1 - p) / max(1, len(labels) - 1)
        return {l: (p if l == top else rest) for l in labels}

    return FunctionDecisionModel(fn, cost_per_call=cost_per_call)


# ---------------------------------------------------------------- runner


class ToyRunner:
    def __init__(self, tasks: list[ToyTask], max_steps: int = 30):
        self.tasks = {t.id: t for t in tasks}
        self.max_steps = max_steps

    def _episode(self, task_id: str, policy: Policy) -> tuple[ToyEnv, list[Message], EpisodeResult]:
        task = self.tasks[task_id]
        env = ToyEnv(task)
        messages: list[Message] = [Message("user", content=user_reply(task, "", 0))]
        turn, n_steps, n_llm, cost = 1, 0, 0, 0.0
        tiers: dict[str, int] = {}
        while n_steps < self.max_steps:
            m = policy(messages)
            n_steps += 1
            cost += m.cost + getattr(m, "_decision_cost", 0.0)
            n_llm += 1 if getattr(m, "_llm_called", True) else 0
            tier = getattr(m, "_tier", "llm")
            tiers[tier] = tiers.get(tier, 0) + 1
            messages.append(m)
            if m.tool_calls:
                tc = m.tool_calls[0]
                if tc.name == "cancel_reservation":
                    # Confirmation counts only if the agent asked and the user said yes right before.
                    asked = any(mm.role == "assistant" and mm.content and "confirm" in mm.content.lower() for mm in messages[:-1])
                    said_yes = len(messages) >= 2 and messages[-2].role == "user" and re.search(r"\byes\b", messages[-2].content or "", re.I)
                    env.confirmed = bool(asked and said_yes)
                messages.append(env.call(tc))
                continue
            reply = user_reply(task, m.content or "", turn)
            turn += 1
            messages.append(Message("user", content=reply))
            if STOP in reply:
                break
        return env, messages, EpisodeResult(task_id, env.success(messages), cost, n_steps, n_llm, tiers)

    def run(self, task_id: str, policy: Policy, seed: int = 0) -> EpisodeResult:
        return self._episode(task_id, policy)[2]

    def trajectory(self, task_id: str, policy: Policy, seed: int = 0, trial: int = 0) -> Trajectory:
        """Run and return the episode as a trajectory (for profiling)."""
        _, messages, res = self._episode(task_id, policy)
        return Trajectory(f"{task_id}-{trial}", task_id, messages, res.success, 1.0 if res.success else 0.0, trial, res.cost)


def tiered_as_policy(tiered) -> Policy:
    """Adapt a :class:`gdopt.tiers.TieredPolicy` to the runner's plain policy signature."""

    def policy(history: list[Message]) -> Message:
        d = tiered.decide(history)
        m = d.message
        m._tier = d.tier_used.value  # type: ignore[attr-defined]
        m._llm_called = d.llm_called  # type: ignore[attr-defined]
        m._decision_cost = d.decision_cost  # type: ignore[attr-defined]
        return m

    return policy
