"""Offline tests for the anchored τ²-bench agent (τ²-bench must be importable; the LLM is stubbed)."""

import pytest

tau2 = pytest.importorskip("tau2")

from tau2.agent.llm_agent import LLMAgentState  # noqa: E402
from tau2.data_model.message import AssistantMessage, SystemMessage, ToolCall, UserMessage  # noqa: E402

from gdopt.adapters import tau2_anchor  # noqa: E402
from gdopt.decision import FunctionDecisionModel  # noqa: E402


class FakeTool:
    def __init__(self, name, desc):
        self.name = name
        self.openai_schema = {"function": {"name": name, "description": desc, "parameters": {}}}


def make_agent(monkeypatch, modes, decide, outputs):
    """``decide(options, state)`` drives the decision model; ``outputs`` is the queue of stubbed LLM answers."""
    calls = []

    def fake_generate(model, tools, messages, call_name, **kw):
        calls.append(messages)
        out = outputs.pop(0)
        out.usage = {"prompt_tokens": 100, "completion_tokens": 10}
        out.cost = 0.001
        return out

    monkeypatch.setattr(tau2_anchor, "generate", fake_generate)
    tools = [FakeTool("get_user_details", "Look up a user."), FakeTool("cancel_reservation", "Cancel.")]
    dm = FunctionDecisionModel(decide, cost_per_call=0.0001)
    agent = tau2_anchor.AnchoredLLMAgent(tools, "policy text", "stub", {}, dm, set(modes))
    state = LLMAgentState(system_messages=[SystemMessage(role="system", content="sys")], messages=[])
    return agent, state, calls


def tool_msg(name):
    return AssistantMessage(role="assistant", content=None, tool_calls=[ToolCall(id="1", name=name, arguments={})])


def text_msg(text="ok"):
    return AssistantMessage(role="assistant", content=text)


def test_hint_is_injected_only_when_confident(monkeypatch):
    agent, state, calls = make_agent(monkeypatch, {"hint"}, lambda o, s: {"tool:get_user_details": 0.95}, [tool_msg("get_user_details")])
    out = agent._generate_next_message(UserMessage(role="user", content="hi"), state)
    assert any(isinstance(m, SystemMessage) and "Planner note" in (m.content or "") for m in calls[0])
    assert out.raw_data["gdopt"]["anchor"]["hint"] == "tool:get_user_details"
    assert out.cost == pytest.approx(0.001 + 0.0001)

    agent, state, calls = make_agent(monkeypatch, {"hint"}, lambda o, s: {"message": 0.6, "tool:get_user_details": 0.4}, [text_msg()])
    agent._generate_next_message(UserMessage(role="user", content="hi"), state)
    assert not any("Planner note" in (m.content or "") for m in calls[0] if isinstance(m, SystemMessage))


def test_veto_asks_once_to_reconsider_and_sums_usage(monkeypatch):
    agent, state, calls = make_agent(monkeypatch, {"veto"}, lambda o, s: {"message": 0.95},
                                     [tool_msg("cancel_reservation"), text_msg("Can you confirm?")])
    out = agent._generate_next_message(UserMessage(role="user", content="cancel it"), state)
    assert len(calls) == 2 and any("Verifier note" in (m.content or "") for m in calls[1] if isinstance(m, SystemMessage))
    assert out.content == "Can you confirm?"
    assert out.usage["prompt_tokens"] == 200
    g = out.raw_data["gdopt"]
    assert g["llm_calls"] == 2 and g["anchor"]["veto"][0]["after"] == "message"
    assert agent.stats["vetoes"] == 1 and agent.stats["veto_changed"] == 1


def test_veto_keeps_llm_answer_when_model_agrees_or_is_unsure(monkeypatch):
    agent, state, calls = make_agent(monkeypatch, {"veto"}, lambda o, s: {"message": 0.7, "tool:cancel_reservation": 0.3},
                                     [tool_msg("cancel_reservation")])
    out = agent._generate_next_message(UserMessage(role="user", content="cancel it"), state)
    assert len(calls) == 1 and out.tool_calls[0].name == "cancel_reservation"


def test_checklist_lines_are_added(monkeypatch):
    agent, state, calls = make_agent(monkeypatch, {"checklist"}, lambda o, s: {"true": 0.9, "false": 0.1}, [text_msg()])
    out = agent._generate_next_message(UserMessage(role="user", content="hi"), state)
    note = [m for m in calls[0] if isinstance(m, SystemMessage) and "State tracker" in (m.content or "")]
    assert note and "identity_verified" in out.raw_data["gdopt"]["anchor"]["checklist"]
    assert note[0].content.count("yes (p=0.90)") == 3
