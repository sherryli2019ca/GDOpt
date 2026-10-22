"""Stage 4: tier table and the transformed (tiered) policy.

Every situation gets a tier and a confidence threshold.  At run time the
tiered policy computes the situation of the current history and then:

* ``code``  – emits the situation's rule action, arguments filled with the
  latest entity of each type; confidence = the rule's held-out accuracy;
* ``jev``   – asks the decision model for the next action, fills closed
  arguments from the entity table; confidence = p_max;
* ``llm``   – calls the original agent.

A step is taken by the cheap tier only when its confidence is at least the
effective threshold ``tau_eff = tau + lam * (1 - tau)``; otherwise the whole
step falls back to the original agent.  ``lam`` in [0, 1] is the single global
knob calibrated by :mod:`gdopt.calibrate`: ``lam = 1`` is the original agent,
``lam = 0`` uses the base thresholds everywhere.  Risk is monotone in ``lam``,
which is what Learn-then-Test needs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from .decision import NEXT_ACTION_INSTRUCTIONS, DecisionModel, conversation_state
from .entities import build_entity_table
from .profile import ProfileReport, candidate_tiers
from .shadow import SituationShadow
from .situation import SituationModel
from .trace import MESSAGE_ACTION, Message, ToolCall, action_tool_name, is_tool_action


class Tier(str, Enum):
    CODE = "code"
    JEV = "jev"
    LLM = "llm"


@dataclass
class TierRule:
    leaf_id: int
    tier: Tier
    tau: float = 1.0
    action: str | None = None  # code tier: the fixed action
    confidence: float = 0.0  # code tier: held-out accuracy of the rule
    rationale: str = ""


@dataclass
class TierTable:
    rules: dict[int, TierRule] = field(default_factory=dict)

    def get(self, leaf_id: int) -> TierRule:
        return self.rules.get(leaf_id) or TierRule(leaf_id, Tier.LLM)

    def counts(self) -> dict[str, int]:
        out = {t.value: 0 for t in Tier}
        for r in self.rules.values():
            out[r.tier.value] += 1
        return out

    @classmethod
    def from_profile(
        cls,
        report: ProfileReport,
        shadow: dict[int, SituationShadow] | None = None,
        min_agreement: float = 0.9,
        default_tau: float = 0.8,
        **candidate_kw: Any,
    ) -> "TierTable":
        """Build the table from stage-2 candidates and (optionally) stage-3 shadow stats.

        Without shadow stats, ``jev`` candidates stay ``jev`` with
        ``default_tau``; with them, a candidate is kept only when the decision
        model agrees with the LLM often enough, and ``tau`` is the smallest
        threshold on its coverage curve whose agreement reaches
        ``min_agreement``.
        """
        cands = candidate_tiers(report, **candidate_kw)
        table = cls()
        for s in report.situations:
            tier = cands[s.leaf_id]
            if tier == "code":
                table.rules[s.leaf_id] = TierRule(
                    s.leaf_id, Tier.CODE, tau=0.0, action=s.majority, confidence=s.majority_test_acc,
                    rationale=f"majority acc {s.majority_test_acc:.3f}, latest-rule acc {s.latest_rule_acc:.3f}",
                )
            elif tier == "jev":
                tau = default_tau
                rationale = f"entropy {s.norm_entropy_test:.2f}"
                if shadow is not None:
                    sh = shadow.get(s.leaf_id)
                    if sh is None:
                        table.rules[s.leaf_id] = TierRule(s.leaf_id, Tier.LLM, rationale="no shadow data")
                        continue
                    ok = [t for t, (agree, cov) in sorted(sh.coverage_curve.items()) if agree >= min_agreement and cov > 0]
                    if not ok:
                        table.rules[s.leaf_id] = TierRule(s.leaf_id, Tier.LLM, rationale=f"shadow agreement {sh.agreement:.2f} too low")
                        continue
                    tau = ok[0]
                    rationale += f", shadow agreement {sh.agreement:.2f}, tau {tau}"
                table.rules[s.leaf_id] = TierRule(s.leaf_id, Tier.JEV, tau=tau, rationale=rationale)
            else:
                table.rules[s.leaf_id] = TierRule(s.leaf_id, Tier.LLM, rationale=f"entropy {s.norm_entropy_test:.2f}")
        return table


def effective_tau(tau: float, lam: float) -> float:
    return tau + lam * (1.0 - tau)


@dataclass
class Decision:
    message: Message
    tier_used: Tier
    leaf_id: int
    confidence: float
    fallback_reason: str | None = None
    decision_cost: float = 0.0
    llm_called: bool = False


LLMFallback = Callable[[list[Message]], Message]


class TieredPolicy:
    """The transformed agent: situation -> tier -> action, with LLM fallback."""

    def __init__(
        self,
        situation_model: SituationModel,
        tier_table: TierTable,
        decision_model: DecisionModel | None,
        llm: LLMFallback,
        tools: dict[str, str],
        policy_text: str | None = None,
        lam: float = 0.0,
        instructions: str = NEXT_ACTION_INSTRUCTIONS,
    ):
        self.situation_model = situation_model
        self.tier_table = tier_table
        self.decision_model = decision_model
        self.llm = llm
        self.tools = tools
        self.policy_text = policy_text
        self.lam = lam
        self.instructions = instructions
        from .decision import action_menu

        self.menu = action_menu(tools)

    # -- helpers -----------------------------------------------------------
    def _fill_args(self, tool: str, history: list[Message]) -> dict[str, Any] | None:
        """Fill every argument of ``tool`` with the latest known entity of its type."""
        table = build_entity_table(history, self.situation_model.schema)
        args: dict[str, Any] = {}
        for name in sorted(self.situation_model.schema.arg_types.get(tool, ())):
            v = table.latest(name)
            if v is None:
                return None
            args[name] = v
        return args

    def _fallback(self, history: list[Message], leaf_id: int, tier: Tier, conf: float, reason: str, cost: float) -> Decision:
        msg = self.llm(history)
        return Decision(msg, Tier.LLM, leaf_id, conf, fallback_reason=f"{tier.value}: {reason}", decision_cost=cost, llm_called=True)

    # -- main entry --------------------------------------------------------
    def decide(self, history: list[Message]) -> Decision:
        leaf = self.situation_model.situation(history)
        rule = self.tier_table.get(leaf.id)
        if rule.tier == Tier.LLM or self.lam >= 1.0:
            return Decision(self.llm(history), Tier.LLM, leaf.id, 0.0, llm_called=True)

        tau = effective_tau(rule.tau, self.lam)
        if rule.tier == Tier.CODE:
            if rule.confidence < tau:
                return self._fallback(history, leaf.id, Tier.CODE, rule.confidence, "below threshold", 0.0)
            return self._emit(rule.action, history, leaf.id, Tier.CODE, rule.confidence, 0.0)

        # JEV tier
        if self.decision_model is None:
            return self._fallback(history, leaf.id, Tier.JEV, 0.0, "no decision model", 0.0)
        state = conversation_state(history, self.policy_text)
        res = self.decision_model.choice(self.instructions, self.menu, state)
        if res.p_max < tau:
            return self._fallback(history, leaf.id, Tier.JEV, res.p_max, "below threshold", res.cost)
        return self._emit(res.top, history, leaf.id, Tier.JEV, res.p_max, res.cost)

    def _emit(self, action: str | None, history: list[Message], leaf_id: int, tier: Tier, conf: float, cost: float) -> Decision:
        if action is None or action == MESSAGE_ACTION or not is_tool_action(action):
            # Deciding "send a message" still needs the generative model for the text.
            msg = self.llm(history)
            return Decision(msg, tier, leaf_id, conf, fallback_reason="message text needs LLM", decision_cost=cost, llm_called=True)
        tool = action_tool_name(action) or ""
        args = self._fill_args(tool, history)
        if args is None:
            return self._fallback(history, leaf_id, tier, conf, "open argument", cost)
        msg = Message(role="assistant", tool_calls=[ToolCall(tool, args)], cost=0.0)
        return Decision(msg, tier, leaf_id, conf, decision_cost=cost)
