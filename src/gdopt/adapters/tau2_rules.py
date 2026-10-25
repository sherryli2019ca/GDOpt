"""Solidified policy rules for the τ² airline domain: code predicates over facts already seen in tool outputs.

A rule fires on a proposed write-tool call when the facts the agent has observed show that the call violates a policy
clause (verdict ``forbid``).  ``PolicyFacts`` tracks the facts incrementally over a message list (plain dicts in the
τ²-bench results.json shape, or τ² ``Message`` objects via ``model_dump``); ``check`` returns the rules a call breaks.
``RuleGuardedLLMAgent`` is a τ² ``LLMAgent`` that, when its next step is a forbidden call, adds the clause and the
reason as a system note and regenerates once; a second forbidden call is replaced by a refusal message so the write
never reaches the environment.

Rules marked ``certified`` had zero fires in 1230 successful logged airline episodes (E1 audit,
``examples/determinism/clause_audit.py``); only those are enforced by the agent by default.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from typing import Any, Iterable, Optional

NOW = datetime(2024, 5, 15, 15, 0, 0)   # τ² airline policy: "The current time is 2024-05-15 15:00:00 EST."
TODAY = "2024-05-15"
YES = re.compile(r"\b(yes|yeah|yep|confirm|confirmed|go ahead|proceed|please do|do it|sure|correct|that's right|ok|okay)\b", re.I)

CLAUSES = {
    "cancel_flown": "Cancel flight: if any portion of the flight has already been flown, the agent cannot help and transfer is needed.",
    "cancel_ineligible": ("Cancel flight: a reservation can be cancelled only if it was booked within the last 24 hrs, the flight was "
                          "cancelled by the airline, it is a business flight, or the user has travel insurance and the reason is "
                          "covered. The API does not check this."),
    "modify_basic_economy": "Change flights: basic economy flights cannot be modified.",
    "modify_route": "Change flights: reservations can be modified without changing the origin, destination, and trip type.",
    "cabin_after_flown": "Change cabin: cabin cannot be changed if any flight in the reservation has already been flown.",
    "bag_remove": "Change baggage: the user can add but not remove checked bags.",
    "pax_count": "Change passengers: the number of passengers cannot be modified.",
    "comp_ineligible": "Compensation: do not compensate a regular member with no travel insurance flying (basic) economy.",
    "comp_amount": "Compensation: $100 x passengers for cancelled flights, $50 x passengers for delayed flights.",
    "book_payment": ("Book: at most one travel certificate, one credit card and three gift cards; payment methods must be in the "
                     "user profile; at most five passengers."),
    "confirm_before_write": "Before any database update, list the details and obtain explicit user confirmation (yes).",
}
CERTIFIED = frozenset({"cancel_flown", "cancel_ineligible", "modify_basic_economy", "bag_remove", "book_payment"})
WRITE_CONFIRM = {"book_reservation", "update_reservation_flights", "update_reservation_baggages", "update_reservation_passengers"}


def _json(s: Any) -> Any:
    if not isinstance(s, str):
        return None
    try:
        return json.loads(s)
    except Exception:
        return None


def _as_dict(m: Any) -> dict:
    return m if isinstance(m, dict) else m.model_dump()


class PolicyFacts:
    """Facts visible to the agent so far: reservations (latest view), user profile, flight statuses, flight legs."""

    def __init__(self) -> None:
        self.res: dict[str, dict] = {}
        self.status: dict[tuple, str] = {}
        self.legs: dict[str, tuple] = {}
        self.profile: Optional[dict] = None
        self.last_user = ""
        self._pending: dict[str, tuple[str, dict]] = {}

    @classmethod
    def from_messages(cls, messages: Iterable[Any]) -> "PolicyFacts":
        f = cls()
        for m in messages:
            f.observe(m)
        return f

    def observe(self, m: Any) -> None:
        m = _as_dict(m)
        role = m.get("role")
        if role == "user":
            self.last_user = m.get("content") or ""
        elif role == "assistant":
            for tc in m.get("tool_calls") or []:
                self._pending[tc.get("id")] = (tc.get("name"), tc.get("arguments") or {})
        elif role == "tool":
            j = _json(m.get("content"))
            name, args = self._pending.get(m.get("id"), (None, {}))
            if isinstance(j, dict) and "reservation_id" in j and "cabin" in j:
                self.res[j["reservation_id"]] = j
            elif isinstance(j, dict) and "membership" in j:
                self.profile = j
            elif isinstance(j, list):
                for f in j:
                    for leg in (f if isinstance(f, list) else [f]):
                        if isinstance(leg, dict) and "flight_number" in leg:
                            self.legs[leg["flight_number"]] = (leg.get("origin"), leg.get("destination"))
            elif name == "get_flight_status":
                self.status[(args.get("flight_number"), args.get("date"))] = (m.get("content") or "").strip().strip('"')

    def flown(self, r: dict) -> bool:
        return any(f.get("date", "9999") < TODAY or self.status.get((f.get("flight_number"), f.get("date"))) in ("flying", "landed")
                   for f in r.get("flights", []))

    def check(self, name: str, a: dict) -> list[tuple[str, str]]:
        """Rules the proposed call ``name(**a)`` breaks, as (rule, reason)."""
        r = self.res.get(a.get("reservation_id"))
        hit: list[tuple[str, str]] = []
        if name == "cancel_reservation" and r:
            if self.flown(r):
                hit.append(("cancel_flown", f"reservation {r['reservation_id']} has a segment dated before {TODAY} or already flying/landed"))
            else:
                try:
                    lt24 = (NOW - datetime.fromisoformat(r["created_at"])).total_seconds() < 24 * 3600
                except Exception:
                    lt24 = True
                airline = any(self.status.get((f.get("flight_number"), f.get("date"))) == "cancelled" for f in r["flights"])
                if not (lt24 or airline or r.get("cabin") == "business" or r.get("insurance") == "yes"):
                    hit.append(("cancel_ineligible", f"reservation {r['reservation_id']} was booked {r.get('created_at')} (over 24 h ago), "
                                f"cabin {r.get('cabin')}, insurance {r.get('insurance')}, and no flight in it is known to be "
                                "cancelled by the airline"))
        if name == "update_reservation_flights" and r:
            old = sorted((f["flight_number"], f["date"]) for f in r.get("flights", []))
            new = sorted((f.get("flight_number"), f.get("date")) for f in a.get("flights", []))
            if old != new and r.get("cabin") == "basic_economy":
                hit.append(("modify_basic_economy", f"reservation {r['reservation_id']} is basic economy"))
            if a.get("cabin") and a.get("cabin") != r.get("cabin") and self.flown(r):
                hit.append(("cabin_after_flown", f"reservation {r['reservation_id']} has a flown segment"))
            ends = [self.legs.get(f.get("flight_number")) for f in a.get("flights", [])]
            if ends and all(ends):
                start, end = ends[0][0], ends[-1][1]
                want_end = r.get("origin") if r.get("flight_type") == "round_trip" else r.get("destination")
                if start != r.get("origin") or end != want_end:
                    hit.append(("modify_route", f"new itinerary {start}->{end} differs from the reservation's"))
        if name == "update_reservation_baggages" and r and a.get("total_baggages") is not None:
            if a["total_baggages"] < r.get("total_baggages", 0):
                hit.append(("bag_remove", f"reservation {r['reservation_id']} already has {r.get('total_baggages')} bags"))
        if name == "update_reservation_passengers" and r:
            if len(a.get("passengers", [])) != len(r.get("passengers", [])):
                hit.append(("pax_count", f"reservation {r['reservation_id']} has {len(r.get('passengers', []))} passengers"))
        if name == "send_certificate" and self.profile:
            mine = [x for x in self.res.values() if x.get("user_id") == self.profile.get("user_id")] or list(self.res.values())
            if mine and self.profile.get("membership") == "regular" and all(
                    x.get("insurance") != "yes" and x.get("cabin") != "business" for x in mine):
                hit.append(("comp_ineligible", "regular member, no insurance, no business reservation"))
            ok = {k * len(x.get("passengers", [])) for x in mine for k in (50, 100)}
            if mine and a.get("amount") is not None and float(a["amount"]) not in ok:
                hit.append(("comp_amount", f"amount {a['amount']} is not 50 or 100 times a reservation's passenger count"))
        if name == "book_reservation":
            pm = a.get("payment_methods") or []
            kinds = Counter(str(p.get("payment_id", "")).split("_")[0] for p in pm)
            known = set((self.profile or {}).get("payment_methods", {}))
            if (kinds["certificate"] > 1 or kinds["credit"] > 1 or kinds["gift"] > 3 or len(a.get("passengers", [])) > 5
                    or (known and any(p.get("payment_id") not in known for p in pm))):
                hit.append(("book_payment", "payment methods or passenger count outside the limits"))
        if name in WRITE_CONFIRM and not YES.search(self.last_user):
            hit.append(("confirm_before_write", "the last user message contains no explicit yes"))
        return hit


# ---------------------------------------------------------------- τ² agent
try:  # τ²-bench is optional for the offline audit
    from tau2.agent.llm_agent import LLMAgent, LLMAgentState  # type: ignore[import-not-found]
    from tau2.data_model.message import AssistantMessage, MultiToolMessage, SystemMessage  # type: ignore[import-not-found]
    from tau2.registry import registry  # type: ignore[import-not-found]
    from tau2.utils.llm_utils import generate  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    LLMAgent = object  # type: ignore[misc,assignment]

NOTE = ("Policy check (automatic): the call {call} is not allowed. Clause: {clause} Facts: {reason}. Do not make this call; "
        "explain the policy to the user, or transfer to a human agent if the policy says so.")


class RuleGuardedLLMAgent(LLMAgent):  # type: ignore[misc,valid-type]
    """LLMAgent whose forbidden write calls are blocked by certified policy predicates (one regeneration, then refusal)."""

    def __init__(self, tools, domain_policy, llm, llm_args, rules: frozenset = CERTIFIED, **kw: Any):
        super().__init__(tools=tools, domain_policy=domain_policy, llm=llm, llm_args=llm_args, **kw)
        self.rules = rules
        self.stats: dict[str, Any] = {"steps": 0, "fires": 0, "regenerated_ok": 0, "refused": 0}

    def _violations(self, msgs, am) -> list[tuple[str, str, str]]:
        facts = PolicyFacts.from_messages(msgs)
        out = []
        for tc in am.tool_calls or []:
            for rule, reason in facts.check(tc.name, tc.arguments or {}):
                if rule in self.rules:
                    out.append((rule, reason, f"{tc.name}({json.dumps(tc.arguments)})"))
        return out

    def _generate_next_message(self, message, state: "LLMAgentState") -> "AssistantMessage":
        if isinstance(message, MultiToolMessage):
            state.messages.extend(message.tool_messages)
        else:
            state.messages.append(message)
        self.stats["steps"] += 1
        base = state.system_messages + state.messages
        am = generate(model=self.llm, tools=self.tools, messages=base, call_name="agent_response", **self.llm_args)
        info: dict[str, Any] = {}
        v = self._violations(state.messages, am)
        if v:
            self.stats["fires"] += 1
            notes = [SystemMessage(role="system", content=NOTE.format(call=c, clause=CLAUSES[r], reason=why)) for r, why, c in v]
            info["fired"] = [{"rule": r, "reason": why, "call": c} for r, why, c in v]
            am2 = generate(model=self.llm, tools=self.tools, messages=base + notes, call_name="agent_response", **self.llm_args)
            if self._violations(state.messages, am2):
                self.stats["refused"] += 1
                info["refused"] = True
                am2 = AssistantMessage(role="assistant", content=(
                    "I'm sorry, but I can't do that under our policy: " + " ".join(CLAUSES[r] for r, _, _ in v)))
            else:
                self.stats["regenerated_ok"] += 1
            am2.usage = {k: (am.usage or {}).get(k, 0) + (am2.usage or {}).get(k, 0)
                         for k in set(am.usage or {}) | set(am2.usage or {})
                         if isinstance((am.usage or {}).get(k, 0), (int, float)) and isinstance((am2.usage or {}).get(k, 0), (int, float))}
            am2.cost = (am.cost or 0.0) + (am2.cost or 0.0)
            am = am2
        am.raw_data = {**(am.raw_data or {}), "gdopt": {"rules": info}}
        return am


def register_rule_agent(name: str = "gdopt_rules", rules: frozenset = CERTIFIED) -> list[RuleGuardedLLMAgent]:
    made: list[RuleGuardedLLMAgent] = []

    def factory(tools, domain_policy, llm=None, llm_args=None, **_: Any) -> RuleGuardedLLMAgent:
        a = RuleGuardedLLMAgent(tools=tools, domain_policy=domain_policy, llm=llm, llm_args=llm_args or {}, rules=rules)
        made.append(a)
        return a

    registry.register_agent_factory(factory, name)
    return made


def register_rule_anchored_agent(decision_model, modes: set, name: str = "gdopt_anchored", rules: frozenset = CERTIFIED,
                                 **anchor_kw: Any) -> list:
    """``AnchoredLLMAgent`` (any anchor modes) plus the certified rule guard on every step.

    The guard is a hard constraint outside λ: it runs after the anchored step is produced, whatever the Jev confidence;
    the Jev p of the step is logged with each fire so gating by uncertainty can be analysed offline.
    """
    from .tau2_anchor import AnchoredLLMAgent

    class RuleAnchoredLLMAgent(AnchoredLLMAgent):
        def __init__(self, *a: Any, **kw: Any):
            super().__init__(*a, **kw)
            self.rules = rules
            self.stats.update(rule_fires=0, rule_regenerated_ok=0, rule_refused=0)

        _violations = RuleGuardedLLMAgent._violations

        def _generate_next_message(self, message, state):
            am = super()._generate_next_message(message, state)
            v = self._violations(state.messages, am)
            if not v:
                return am
            self.stats["rule_fires"] += 1
            notes = [SystemMessage(role="system", content=NOTE.format(call=c, clause=CLAUSES[r], reason=why)) for r, why, c in v]
            am2 = generate(model=self.llm, tools=self.tools, messages=state.system_messages + state.messages + notes,
                           call_name="agent_response", **self.llm_args)
            refused = bool(self._violations(state.messages, am2))
            if refused:
                self.stats["rule_refused"] += 1
                am2 = AssistantMessage(role="assistant", content=(
                    "I'm sorry, but I can't do that under our policy: " + " ".join(CLAUSES[r] for r, _, _ in v)))
            else:
                self.stats["rule_regenerated_ok"] += 1
            am2.cost = float(am.cost or 0.0) + float(am2.cost or 0.0)
            am2.usage = self._merge_usage(am, am2) if am2.usage else am.usage
            g = dict((am.raw_data or {}).get("gdopt") or {})
            anchor = dict(g.get("anchor") or {})
            anchor["rules"] = {"fired": [{"rule": r, "reason": why, "call": c} for r, why, c in v], "refused": refused}
            g["anchor"] = anchor
            am2.raw_data = dict(am2.raw_data or {}, gdopt=g)
            return am2

    created: list = []
    modes = set(modes) - {"rules"}

    def factory(tools, domain_policy, llm=None, llm_args=None, **_: Any):
        a = RuleAnchoredLLMAgent(tools, domain_policy, llm, llm_args or {}, decision_model, modes, **anchor_kw)
        created.append(a)
        return a

    registry.register_agent_factory(factory, name)
    return created
