"""A τ²-bench agent that runs the GDOpt tiered policy in front of the LLM.

Requires τ²-bench importable (``pip install -e tau2-bench`` or ``PYTHONPATH``
to its ``src``).  Register with::

    from gdopt.adapters.tau2_agent import register_tiered_agent
    register_tiered_agent(situation_model, tier_table, decision_model, name="gdopt_tiered")

and run it with τ²-bench's runner using ``agent="gdopt_tiered"``.  Every
assistant message carries ``raw_data["gdopt"]`` with the tier used, the
confidence, the fallback reason and the decision-model cost; the decision
cost is also added to the message ``cost`` so the run's ``agent_cost`` is the
true total.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from tau2.agent.llm_agent import LLMAgent, LLMAgentState  # type: ignore[import-not-found]
from tau2.data_model.message import (  # type: ignore[import-not-found]
    AssistantMessage,
    MultiToolMessage,
    ToolCall as T2ToolCall,
    ToolMessage,
    UserMessage,
)
from tau2.registry import registry  # type: ignore[import-not-found]

from ..decision import DecisionModel
from ..situation import SituationModel
from ..tiers import Decision, Tier, TieredPolicy, TierTable
from ..trace import Message, ToolCall


def to_gdopt_history(messages: list[Any]) -> list[Message]:
    """Convert τ²-bench agent-side messages to the GDOpt trace schema."""
    out: list[Message] = []
    tool_name_by_id: dict[str, str] = {}
    for m in messages:
        if isinstance(m, MultiToolMessage):
            items = m.tool_messages
        else:
            items = [m]
        for x in items:
            if isinstance(x, AssistantMessage):
                calls = []
                for tc in x.tool_calls or []:
                    tool_name_by_id[tc.id] = tc.name
                    calls.append(ToolCall(tc.name, dict(tc.arguments or {})))
                usage = x.usage or {}
                out.append(Message("assistant", content=x.content, tool_calls=calls, cost=float(x.cost or 0.0),
                                   prompt_tokens=int(usage.get("prompt_tokens") or 0), completion_tokens=int(usage.get("completion_tokens") or 0)))
            elif isinstance(x, UserMessage):
                out.append(Message("user", content=x.content))
            elif isinstance(x, ToolMessage):
                if x.requestor != "assistant":
                    continue
                out.append(Message("tool", content=x.content, tool_name=tool_name_by_id.get(x.id, "?"), error=bool(x.error)))
    return out


def tool_descriptions(tools: list[Any]) -> dict[str, str]:
    out = {}
    for t in tools:
        try:
            out[t.name] = t.openai_schema["function"].get("description", "") or ""
        except Exception:  # pragma: no cover - defensive
            out[t.name] = ""
    return out


class TieredLLMAgent(LLMAgent):
    """τ²-bench LLMAgent whose next-message generation goes through a TieredPolicy."""

    def __init__(self, tools, domain_policy, llm, llm_args, situation_model: SituationModel, tier_table: TierTable,
                 decision_model: Optional[DecisionModel], lam: float = 0.0, additional_stop_tool_names=frozenset()):
        super().__init__(tools=tools, domain_policy=domain_policy, llm=llm, llm_args=llm_args,
                         additional_stop_tool_names=additional_stop_tool_names)
        self._pending: dict[str, Any] = {}
        self.policy = TieredPolicy(
            situation_model, tier_table, decision_model, self._llm_fallback, tool_descriptions(tools), policy_text=domain_policy, lam=lam,
        )
        self.stats = {"steps": 0, "llm_steps": 0, "decision_cost": 0.0, "tiers": {}}

    # The fallback is wired through instance state so TieredPolicy keeps its plain signature.
    def _llm_fallback(self, history: list[Message]) -> Message:
        message, state = self._pending["message"], self._pending["state"]
        t2 = LLMAgent._generate_next_message(self, message, state)  # appends `message` to state, calls the LLM
        self._pending["llm_message"] = t2
        return to_gdopt_history([t2])[0]

    def _generate_next_message(self, message, state: LLMAgentState) -> AssistantMessage:
        incoming = message.tool_messages if isinstance(message, MultiToolMessage) else [message]
        history = to_gdopt_history(list(state.messages) + list(incoming))
        self._pending = {"message": message, "state": state, "llm_message": None}
        d: Decision = self.policy.decide(history)
        info = {"tier": d.tier_used.value, "leaf_id": d.leaf_id, "confidence": round(d.confidence, 4),
                "fallback_reason": d.fallback_reason, "decision_cost": d.decision_cost, "llm_called": d.llm_called,
                "proposed": d.proposed}
        self.stats["steps"] += 1
        self.stats["decision_cost"] += d.decision_cost
        self.stats["tiers"][d.tier_used.value] = self.stats["tiers"].get(d.tier_used.value, 0) + 1
        if d.llm_called:
            self.stats["llm_steps"] += 1
            t2 = self._pending["llm_message"]
            t2.cost = float(t2.cost or 0.0) + d.decision_cost
            t2.raw_data = dict(t2.raw_data or {}, gdopt=info)
            return t2
        # Cheap tier produced the tool call: mirror what the parent does with the incoming message.
        if isinstance(message, MultiToolMessage):
            state.messages.extend(message.tool_messages)
        else:
            state.messages.append(message)
        tc = d.message.tool_calls[0]
        return AssistantMessage(
            role="assistant",
            content=None,
            tool_calls=[T2ToolCall(id=f"gdopt_{uuid.uuid4().hex[:12]}", name=tc.name, arguments=dict(tc.arguments))],
            cost=d.decision_cost,
            usage={"prompt_tokens": 0, "completion_tokens": 0},
            raw_data={"gdopt": info},
        )


def register_tiered_agent(situation_model: SituationModel, tier_table: TierTable, decision_model: Optional[DecisionModel],
                          name: str = "gdopt_tiered", lam: float = 0.0) -> list[TieredLLMAgent]:
    """Register a τ²-bench agent factory; returns the list of agents created (for stats)."""
    created: list[TieredLLMAgent] = []

    def factory(tools, domain_policy, llm=None, llm_args=None, **_: Any) -> TieredLLMAgent:
        a = TieredLLMAgent(tools, domain_policy, llm, llm_args or {}, situation_model, tier_table, decision_model, lam=lam)
        created.append(a)
        return a

    registry.register_agent_factory(factory, name)
    return created
