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


def test_deliberate_fires_only_when_unsure(monkeypatch):
    agent, state, calls = make_agent(monkeypatch, {"deliberate"}, lambda o, s: {"message": 0.55, "tool:cancel_reservation": 0.45}, [text_msg()])
    out = agent._generate_next_message(UserMessage(role="user", content="cancel"), state)
    note = [m for m in calls[0] if isinstance(m, SystemMessage) and "ambiguous" in (m.content or "")]
    assert note and "cancel_reservation" in note[0].content
    assert out.raw_data["gdopt"]["anchor"]["deliberate"]["a"] == "message"

    agent, state, calls = make_agent(monkeypatch, {"deliberate"}, lambda o, s: {"message": 0.95}, [text_msg()])
    agent._generate_next_message(UserMessage(role="user", content="hi"), state)
    assert not any("ambiguous" in (m.content or "") for m in calls[0] if isinstance(m, SystemMessage))


def test_reasoner_switches_model_only_when_unsure(monkeypatch):
    seen = []

    def fake_generate(model, tools, messages, call_name, **kw):
        seen.append(model)
        out = text_msg(); out.usage = {"prompt_tokens": 1, "completion_tokens": 1}; out.cost = 0.0
        return out

    monkeypatch.setattr(tau2_anchor, "generate", fake_generate)
    tools = [FakeTool("get_user_details", "Look up a user.")]
    dm = FunctionDecisionModel(lambda o, s: {"message": 0.6, "tool:get_user_details": 0.4})
    agent = tau2_anchor.AnchoredLLMAgent(tools, "policy", "fast", {}, dm, {"reasoner"}, reasoner_llm="slow", reasoner_llm_args={"x": 1})
    state = LLMAgentState(system_messages=[SystemMessage(role="system", content="sys")], messages=[])
    out = agent._generate_next_message(UserMessage(role="user", content="hi"), state)
    assert seen == ["slow"] and out.raw_data["gdopt"]["generator"] == "reasoner"
    dm.fn = lambda o, s: {"message": 0.95}
    agent._generate_next_message(UserMessage(role="user", content="more"), state)
    assert seen == ["slow", "fast"]
    with pytest.raises(ValueError):
        tau2_anchor.AnchoredLLMAgent(tools, "policy", "fast", {}, dm, {"reasoner"})


def test_vote_takes_majority_action_and_sums_usage(monkeypatch):
    temps = []

    def fake_generate(model, tools, messages, call_name, **kw):
        temps.append(kw.get("temperature"))
        out = outputs.pop(0); out.usage = {"prompt_tokens": 100, "completion_tokens": 10, "model": "deepseek-flash"}; out.cost = 0.001
        return out

    outputs = [text_msg("cold"), tool_msg("cancel_reservation"), tool_msg("cancel_reservation")]
    monkeypatch.setattr(tau2_anchor, "generate", fake_generate)
    tools = [FakeTool("get_user_details", "Look up a user."), FakeTool("cancel_reservation", "Cancel.")]
    dm = FunctionDecisionModel(lambda o, s: {"message": 0.55, "tool:cancel_reservation": 0.45})
    agent = tau2_anchor.AnchoredLLMAgent(tools, "policy", "stub", {"temperature": 0.0}, dm, {"vote"}, vote_k=3, vote_temperature=0.7)
    state = LLMAgentState(system_messages=[SystemMessage(role="system", content="sys")], messages=[])
    out = agent._generate_next_message(UserMessage(role="user", content="cancel"), state)
    assert temps == [0.0, 0.7, 0.7]
    assert out.tool_calls and out.tool_calls[0].name == "cancel_reservation"
    assert out.usage["prompt_tokens"] == 300 and out.usage["model"] == "deepseek-flash" and out.cost == pytest.approx(0.003)
    g = out.raw_data["gdopt"]
    assert g["llm_calls"] == 3 and g["anchor"]["vote"] == {"actions": ["message", "tool:cancel_reservation", "tool:cancel_reservation"],
                                                           "chosen": "tool:cancel_reservation", "changed": True}
    assert agent.stats["votes"] == 1 and agent.stats["vote_changed"] == 1 and agent.stats["vote_split"] == 1
    # confident step: a single call, no vote
    dm.fn = lambda o, s: {"message": 0.95}
    outputs[:] = [text_msg("sure")]
    agent._generate_next_message(UserMessage(role="user", content="thanks"), state)
    assert len(temps) == 4 and agent.stats["votes"] == 1


def test_vote_tie_goes_to_cold_sample(monkeypatch):
    outputs = [text_msg("cold"), tool_msg("cancel_reservation"), tool_msg("get_user_details")]

    def fake_generate(model, tools, messages, call_name, **kw):
        out = outputs.pop(0); out.usage = {}; out.cost = 0.0
        return out

    monkeypatch.setattr(tau2_anchor, "generate", fake_generate)
    tools = [FakeTool("get_user_details", "Look up a user."), FakeTool("cancel_reservation", "Cancel.")]
    dm = FunctionDecisionModel(lambda o, s: {"message": 0.5, "tool:cancel_reservation": 0.5})
    agent = tau2_anchor.AnchoredLLMAgent(tools, "policy", "stub", {}, dm, {"vote"}, vote_k=3)
    state = LLMAgentState(system_messages=[SystemMessage(role="system", content="sys")], messages=[])
    out = agent._generate_next_message(UserMessage(role="user", content="cancel"), state)
    assert out.content == "cold" and out.raw_data["gdopt"]["anchor"]["vote"]["changed"] is False


POLICY = """# Test Policy

Always confirm before any update.

## Book flight

The agent must ask for passengers and payment before booking.

## Cancel flight

The booking can be cancelled if it was made within 24 hours or the airline cancelled the flight.

### Refund

Refunds go to the original payment method.

## Baggage

Checked bags can be added but not removed.
"""


def test_split_policy_keeps_heading_path():
    chunks = tau2_anchor.split_policy(POLICY)
    assert [c.heading for c in chunks] == ["General rules", "Book flight", "Cancel flight", "Cancel flight / Refund", "Baggage"]
    assert "24 hours" in chunks[2].text


def test_policy_note_retrieves_relevant_sections(monkeypatch):
    agent, state, calls = make_agent(monkeypatch, {"policy"}, lambda o, s: {"message": 0.55, "tool:cancel_reservation": 0.45}, [text_msg()])
    agent.retriever = tau2_anchor.PolicyRetriever(POLICY, top_k=2)
    out = agent._generate_next_message(UserMessage(role="user", content="I want to cancel my flight and get a refund"), state)
    note = [m for m in calls[0] if isinstance(m, SystemMessage) and "policy sections below" in (m.content or "")]
    assert note and "Cancel flight" in note[0].content and "Baggage" not in note[0].content
    secs = out.raw_data["gdopt"]["anchor"]["policy"]["sections"]
    assert secs[0].startswith("Cancel flight") and len(secs) == 2

    agent, state, calls = make_agent(monkeypatch, {"policy"}, lambda o, s: {"message": 0.95}, [text_msg()])
    agent.retriever = tau2_anchor.PolicyRetriever(POLICY, top_k=2)
    agent._generate_next_message(UserMessage(role="user", content="cancel"), state)
    assert not any("policy sections below" in (m.content or "") for m in calls[0] if isinstance(m, SystemMessage))
