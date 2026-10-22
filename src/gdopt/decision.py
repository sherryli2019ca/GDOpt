"""Decision-model backends (Jev-style Choice / Noul / Score).

A decision model returns calibrated probabilities over a fixed option set.  The
only backend that talks to a real model is :class:`OpenRouterJev`, which calls
TypeSafe's Jev through OpenRouter's ``/api/alpha/decisions`` endpoint.  The
others are for tests and simulations.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from .trace import Message


@dataclass
class ChoiceResult:
    probabilities: dict[str, float]
    cost: float = 0.0
    latency_s: float = 0.0
    raw: Any = None

    @property
    def top(self) -> str:
        return max(self.probabilities, key=self.probabilities.get)

    @property
    def p_max(self) -> float:
        return self.probabilities[self.top]


class DecisionModel(Protocol):
    def choice(self, instructions: str, options: dict[str, str], state: Any) -> ChoiceResult: ...

    def noul(self, instructions: str, criteria: dict[str, str], state: Any) -> ChoiceResult: ...


def conversation_state(history: list[Message], policy: str | None = None, max_messages: int | None = None) -> dict[str, Any]:
    """Serialize a history into the ``state`` object sent to the decision model."""
    msgs = history if max_messages is None else history[-max_messages:]
    conv: list[dict[str, Any]] = []
    for m in msgs:
        if m.role == "assistant" and m.tool_calls:
            conv.append({"role": "assistant", "tool_call": {"name": m.tool_calls[0].name, "arguments": m.tool_calls[0].arguments}})
        elif m.role == "tool":
            conv.append({"role": "tool", "tool": m.tool_name, "error": m.error, "result": m.content})
        else:
            conv.append({"role": m.role, "content": m.content})
    state: dict[str, Any] = {"conversation": conv}
    if policy:
        state["policy"] = policy
    return state


def action_menu(tools: dict[str, str], extra: dict[str, str] | None = None) -> dict[str, str]:
    """The Choice option set for 'what does the agent do next'."""
    menu = {"message": "Send a message to the user (ask, inform, confirm, or close the conversation)."}
    for name, desc in tools.items():
        menu[f"tool:{name}"] = desc or f"Call the tool {name}."
    if extra:
        menu.update(extra)
    return menu


NEXT_ACTION_INSTRUCTIONS = (
    "You are the customer-service agent in this conversation. Given the policy and the "
    "conversation so far, what is the agent's correct next action?"
)


class OpenRouterJev:
    """Jev via OpenRouter's Decisions API.

    ``POST https://openrouter.ai/api/alpha/decisions`` with
    ``{model, questions: {name: {type, instructions, criteria}}, state}``.
    ``choice`` criteria is ``{label: description}``, ``noul`` criteria is
    ``{"true": ..., "false": ...}``.
    """

    URL = "https://openrouter.ai/api/alpha/decisions"

    def __init__(self, api_key: str | None = None, model: str = "typesafe/jev-1.14", timeout: float = 60.0):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not set")
        self.model = model
        self.timeout = timeout
        self.total_cost = 0.0
        self.n_calls = 0

    def _post(self, questions: dict[str, Any], state: Any) -> dict[str, Any]:
        body = json.dumps({"model": self.model, "questions": questions, "state": state}).encode()
        req = urllib.request.Request(
            self.URL,
            data=body,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:  # pragma: no cover - network
            raise RuntimeError(f"OpenRouter decisions HTTP {e.code}: {e.read()[:500]!r}") from e
        data["_latency_s"] = time.time() - t0
        self.n_calls += 1
        self.total_cost += float((data.get("usage") or {}).get("cost") or 0.0)
        return data

    @staticmethod
    def _answer(data: dict[str, Any], name: str) -> dict[str, Any]:
        answers = data.get("answers") or data.get("results") or {}
        ans = answers.get(name) if isinstance(answers, dict) else None
        if ans is None:
            raise RuntimeError(f"no answer for question {name!r} in {json.dumps(data)[:500]}")
        return ans

    def choice(self, instructions: str, options: dict[str, str], state: Any) -> ChoiceResult:
        data = self._post({"q": {"type": "choice", "instructions": instructions, "criteria": options}}, state)
        ans = self._answer(data, "q")
        probs = ans.get("probabilities") or {}
        probs = {k: float(probs.get(k, 0.0)) for k in options}
        return ChoiceResult(probs, cost=float((data.get("usage") or {}).get("cost") or 0.0), latency_s=data["_latency_s"], raw=data)

    def noul(self, instructions: str, criteria: dict[str, str], state: Any) -> ChoiceResult:
        data = self._post({"q": {"type": "noul", "instructions": instructions, "criteria": criteria}}, state)
        ans = self._answer(data, "q")
        p = float(ans.get("probability", ans.get("prob", 0.5)))
        return ChoiceResult({"true": p, "false": 1 - p}, cost=float((data.get("usage") or {}).get("cost") or 0.0), latency_s=data["_latency_s"], raw=data)


@dataclass
class FunctionDecisionModel:
    """Decision model backed by a Python function; for tests and simulations.

    ``fn(options, state) -> dict[label, prob]``.  Missing labels get 0 and the
    result is renormalized.
    """

    fn: Callable[[dict[str, str], Any], dict[str, float]]
    cost_per_call: float = 0.0
    n_calls: int = 0

    def _norm(self, options: dict[str, str], probs: dict[str, float]) -> dict[str, float]:
        p = {k: max(0.0, float(probs.get(k, 0.0))) for k in options}
        z = sum(p.values()) or 1.0
        return {k: v / z for k, v in p.items()}

    def choice(self, instructions: str, options: dict[str, str], state: Any) -> ChoiceResult:
        self.n_calls += 1
        return ChoiceResult(self._norm(options, self.fn(options, state)), cost=self.cost_per_call)

    def noul(self, instructions: str, criteria: dict[str, str], state: Any) -> ChoiceResult:
        self.n_calls += 1
        return ChoiceResult(self._norm(criteria, self.fn(criteria, state)), cost=self.cost_per_call)


@dataclass
class CachedDecisionModel:
    """Memoizes calls by (instructions, options, state) so shadow runs are replayable."""

    inner: DecisionModel
    cache: dict[str, ChoiceResult] = field(default_factory=dict)

    @staticmethod
    def _key(kind: str, instructions: str, options: dict[str, str], state: Any) -> str:
        return json.dumps([kind, instructions, options, state], sort_keys=True, default=str)

    def choice(self, instructions: str, options: dict[str, str], state: Any) -> ChoiceResult:
        k = self._key("choice", instructions, options, state)
        if k not in self.cache:
            self.cache[k] = self.inner.choice(instructions, options, state)
        return self.cache[k]

    def noul(self, instructions: str, criteria: dict[str, str], state: Any) -> ChoiceResult:
        k = self._key("noul", instructions, criteria, state)
        if k not in self.cache:
            self.cache[k] = self.inner.noul(instructions, criteria, state)
        return self.cache[k]
