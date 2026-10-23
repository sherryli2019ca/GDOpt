"""A τ²-bench agent where a decision model *anchors* the LLM instead of replacing it.

Three anchors, combinable (``modes``):

``hint``
    Before each LLM call, ask the decision model "what is the correct next action?" (Choice over the
    action menu, same question as the shadow evaluation).  If its confidence is at least ``tau_hint``
    the suggestion is appended to the prompt as a planner note; the LLM still writes the step.
``veto``
    After the LLM has produced a step, compare it with the decision model's answer.  If the model is at
    least ``tau_veto`` confident in a *different* action, the LLM is asked once to reconsider with a
    verifier note; the second answer is used whatever it is.
``checklist``
    Before each LLM call, ask a fixed set of yes/no questions about the conversation state (identity
    verified? pending change confirmed by the user? open user question?) in one request and append the
    answers to the prompt as a state tracker.

Every assistant message carries ``raw_data["gdopt"]`` in the same shape the tiered agent uses
(``tier`` is always ``llm``) plus ``anchor`` details; the decision-model cost is in ``decision_cost`` and
added to the message cost, and a reconsidered step carries the summed usage of both LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from tau2.agent.llm_agent import LLMAgent, LLMAgentState  # type: ignore[import-not-found]
from tau2.data_model.message import (  # type: ignore[import-not-found]
    AssistantMessage,
    MultiToolMessage,
    SystemMessage,
)
from tau2.registry import registry  # type: ignore[import-not-found]
from tau2.utils.llm_utils import generate  # type: ignore[import-not-found]

from ..decision import NEXT_ACTION_INSTRUCTIONS, ChoiceResult, DecisionModel, action_menu, conversation_state
from ..trace import MESSAGE_ACTION, action_tool_name, is_tool_action
from .tau2_agent import to_gdopt_history, tool_descriptions


@dataclass
class ChecklistQuestion:
    name: str
    label: str  # how the line reads in the prompt
    instructions: str
    true: str
    false: str


DEFAULT_CHECKLIST: list[ChecklistQuestion] = [
    ChecklistQuestion(
        "identity_verified",
        "User identity verified (user id obtained and looked up successfully)",
        "Has the agent already identified the user, i.e. obtained the user's id and successfully looked up the user's details with a tool in this conversation?",
        "The user's id is known and a successful user-lookup tool result appears in the conversation.",
        "No user id yet, or the lookup has not succeeded.",
    ),
    ChecklistQuestion(
        "change_confirmed",
        "User explicitly confirmed the specific pending state-changing action (after the details were listed)",
        "The policy requires listing the details of any booking, change, cancellation or other state-changing action and getting the user's explicit 'yes' before performing it. Has the user explicitly confirmed the specific action that is currently pending, after the agent listed its details, and have the details not changed since?",
        "The agent listed the details of the pending action and the user then explicitly agreed, and nothing changed since.",
        "No explicit confirmation of the currently pending action yet, or the details changed after the last confirmation.",
    ),
    ChecklistQuestion(
        "open_question",
        "There is a user question or request the agent has not addressed yet",
        "Is there a question or request from the user that the agent has not yet answered or acted on?",
        "The user asked or requested something that the agent has not yet addressed.",
        "Everything the user asked for so far has been answered or acted on.",
    ),
]


HINT_TEMPLATE = (
    "Planner note (a calibrated decision model read the policy and the conversation; confidence {p:.2f}): "
    "the correct next step is most likely to {action}. Follow the policy; deviate only for a specific reason."
)
VETO_TEMPLATE = (
    "Verifier note: you proposed to {proposed}. A calibrated verifier that read the policy and the conversation "
    "is confident (p={p:.2f}) that the correct next step is to {suggested}. Reconsider and give your next step now, "
    "following the policy."
)
CHECKLIST_HEADER = "State tracker (computed by a calibrated decision model from the conversation so far; use it to follow the policy consistently):"


def describe_action(action: str) -> str:
    tool = action_tool_name(action)
    return f"call the tool `{tool}`" if tool else "send a message to the user (ask, inform, confirm or close)"


def action_of_message(m: AssistantMessage) -> str:
    calls = m.tool_calls or []
    return f"tool:{calls[0].name}" if calls else MESSAGE_ACTION


class AnchoredLLMAgent(LLMAgent):
    """τ²-bench LLMAgent with decision-model hint / veto / checklist anchors."""

    def __init__(self, tools, domain_policy, llm, llm_args, decision_model: DecisionModel, modes: set[str],
                 tau_hint: float = 0.9, tau_veto: float = 0.9, checklist: Optional[list[ChecklistQuestion]] = None,
                 max_reconsider: int = 1, additional_stop_tool_names=frozenset()):
        super().__init__(tools=tools, domain_policy=domain_policy, llm=llm, llm_args=llm_args,
                         additional_stop_tool_names=additional_stop_tool_names)
        unknown = modes - {"hint", "veto", "checklist"}
        if unknown:
            raise ValueError(f"unknown anchor modes: {sorted(unknown)}")
        self.decision_model = decision_model
        self.modes = set(modes)
        self.tau_hint, self.tau_veto = tau_hint, tau_veto
        self.checklist = checklist if checklist is not None else DEFAULT_CHECKLIST
        self.max_reconsider = max_reconsider
        self.policy_text = domain_policy
        self.menu = action_menu(tool_descriptions(tools))
        self.stats: dict[str, Any] = {"steps": 0, "hints": 0, "vetoes": 0, "veto_changed": 0, "checklists": 0,
                                      "decision_cost": 0.0, "llm_calls": 0}

    # -- decision-model queries ------------------------------------------
    def _next_action(self, history) -> ChoiceResult:
        return self.decision_model.choice(NEXT_ACTION_INSTRUCTIONS, self.menu, conversation_state(history, self.policy_text))

    def _checklist(self, history) -> tuple[dict[str, float], float]:
        state = conversation_state(history, self.policy_text)
        questions = {q.name: (q.instructions, {"true": q.true, "false": q.false}) for q in self.checklist}
        nouls = getattr(self.decision_model, "nouls", None)
        if nouls is not None:
            res = nouls(questions, state)
        else:
            res = {n: self.decision_model.noul(ins, crit, state) for n, (ins, crit) in questions.items()}
        probs = {n: float(r.probabilities.get("true", 0.0)) for n, r in res.items()}
        return probs, sum(float(r.cost) for r in res.values())

    @staticmethod
    def _merge_usage(a: AssistantMessage, b: AssistantMessage) -> dict[str, Any]:
        ua, ub = a.usage or {}, b.usage or {}
        return {k: int(ua.get(k) or 0) + int(ub.get(k) or 0) for k in set(ua) | set(ub)}

    # -- generation ------------------------------------------------------
    def _generate_next_message(self, message, state: LLMAgentState) -> AssistantMessage:
        if isinstance(message, MultiToolMessage):
            state.messages.extend(message.tool_messages)
        else:
            state.messages.append(message)
        history = to_gdopt_history(list(state.messages))
        notes: list[SystemMessage] = []
        info: dict[str, Any] = {"modes": sorted(self.modes)}
        cost = 0.0
        res: Optional[ChoiceResult] = None
        if self.modes & {"hint", "veto"}:
            res = self._next_action(history)
            cost += float(res.cost)
            info.update(jev_top=res.top, jev_p=round(res.p_max, 3))
        if "hint" in self.modes and res is not None and res.p_max >= self.tau_hint:
            notes.append(SystemMessage(role="system", content=HINT_TEMPLATE.format(p=res.p_max, action=describe_action(res.top))))
            info["hint"] = res.top
            self.stats["hints"] += 1
        if "checklist" in self.modes:
            probs, c = self._checklist(history)
            cost += c
            lines = [CHECKLIST_HEADER]
            for q in self.checklist:
                p = probs.get(q.name, 0.0)
                lines.append(f"- {q.label}: {'yes' if p >= 0.5 else 'no'} (p={p:.2f})")
            notes.append(SystemMessage(role="system", content="\n".join(lines)))
            info["checklist"] = {k: round(v, 3) for k, v in probs.items()}
            self.stats["checklists"] += 1

        messages = state.system_messages + state.messages + notes
        out = generate(model=self.llm, tools=self.tools, messages=messages, call_name="agent_response", **self.llm_args)
        llm_calls = 1
        if "veto" in self.modes and res is not None:
            proposed = action_of_message(out)
            reconsidered = 0
            while res.p_max >= self.tau_veto and res.top != proposed and reconsidered < self.max_reconsider:
                self.stats["vetoes"] += 1
                note = SystemMessage(role="system", content=VETO_TEMPLATE.format(
                    proposed=describe_action(proposed), p=res.p_max, suggested=describe_action(res.top)))
                second = generate(model=self.llm, tools=self.tools, messages=messages + [note], call_name="agent_response",
                                  **self.llm_args)
                llm_calls += 1
                second.usage = self._merge_usage(out, second)
                second.cost = float(out.cost or 0.0) + float(second.cost or 0.0)
                info.setdefault("veto", []).append({"proposed": proposed, "suggested": res.top, "p": round(res.p_max, 3),
                                                    "after": action_of_message(second)})
                if action_of_message(second) != proposed:
                    self.stats["veto_changed"] += 1
                out = second
                proposed = action_of_message(out)
                reconsidered += 1
        self.stats["steps"] += 1
        self.stats["llm_calls"] += llm_calls
        self.stats["decision_cost"] += cost
        out.cost = float(out.cost or 0.0) + cost
        out.raw_data = dict(out.raw_data or {}, gdopt={
            "tier": "llm", "leaf_id": -1, "confidence": round(res.p_max, 4) if res is not None else 0.0,
            "fallback_reason": "+".join(sorted(self.modes)) or "none", "decision_cost": cost, "llm_called": True,
            "proposed": res.top if res is not None else None, "generator": "llm", "llm_calls": llm_calls, "anchor": info,
        })
        return out


def register_anchored_agent(decision_model: DecisionModel, modes: set[str], name: str = "gdopt_anchored",
                            tau_hint: float = 0.9, tau_veto: float = 0.9, checklist: Optional[list[ChecklistQuestion]] = None,
                            max_reconsider: int = 1) -> list[AnchoredLLMAgent]:
    created: list[AnchoredLLMAgent] = []

    def factory(tools, domain_policy, llm=None, llm_args=None, **_: Any) -> AnchoredLLMAgent:
        a = AnchoredLLMAgent(tools, domain_policy, llm, llm_args or {}, decision_model, modes, tau_hint=tau_hint,
                             tau_veto=tau_veto, checklist=checklist, max_reconsider=max_reconsider)
        created.append(a)
        return a

    registry.register_agent_factory(factory, name)
    return created
