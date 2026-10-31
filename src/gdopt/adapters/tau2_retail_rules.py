"""Consistency checks for the τ²-bench retail domain (2026-10-25).

Same interface as ``tau2_rules.ConsistencyChecker``: build from the conversation so far, ``check(assistant_message)``
returns ``[(rule, "hard"|"soft", note)]`` for the proposed tool calls.  Found by reading the failed episodes of the
retail baseline and deliberate+reasoner runs (``examples/determinism/retail_rule_audit.py``):

hard (the call contradicts a fact the agent has already seen; regenerate with a corrective note)
  status_precondition   cancel/modify on an order that is not 'pending', return/exchange on one not 'delivered'
  cancel_reason         the reason argument contradicts the user's words ('ordered by mistake' vs 'no longer needed')
  refund_method         return refund to a method that is neither the order's original payment nor a gift card
  new_item_unavailable  a new item id that a product lookup showed as unavailable, or of a different product
  option_count          the agent states "N options/variants" where N is the total variant count but fewer are available
  arithmetic            the agent writes "a − b = c" or "a + b = c" with dollar amounts and the arithmetic is wrong
soft (a second, more careful look by the reasoner)
  transfer_in_scope     transfer to a human while the user's request is an in-scope action that was not attempted
audited but NOT active (fire mostly in successful episodes: users refer to orders by category, to addresses on file,
to "the original payment"; see reports/determinism/retail_rule_audit.json)
  order_unmentioned     the user has several orders and never named this one nor any product in it
  address_unseen        an address line or zip that the user never typed
  payment_unconfirmed   a payment method whose kind (card / PayPal / gift card) the user never mentioned
  items_partial         return/exchange leaves out items of the order whose product the user mentioned
"""

from __future__ import annotations

import re
from typing import Any, Iterable

from .tau2_rules import _as_dict, _json

WRITES = {"cancel_pending_order", "modify_pending_order_address", "modify_pending_order_items",
          "modify_pending_order_payment", "modify_user_address", "return_delivered_order_items",
          "exchange_delivered_order_items"}
NEEDS = {"cancel_pending_order": "pending", "modify_pending_order_address": "pending",
         "modify_pending_order_items": "pending", "modify_pending_order_payment": "pending",
         "return_delivered_order_items": "delivered", "exchange_delivered_order_items": "delivered"}
MISTAKE_RX = re.compile(r"mistake|by accident|accidental|wrong(ly)? order|didn'?t mean to", re.I)
NOT_NEEDED_RX = re.compile(r"no longer need|don'?t need|do not need|not need(ed)? anymore|changed my mind|no use", re.I)
ACTIVE = frozenset({"status_precondition", "cancel_reason", "refund_method", "new_item_unavailable", "option_count",
                    "arithmetic", "transfer_in_scope"})
COUNT_RX = re.compile(r"\b(\d{1,3})\s+(?:[\w-]+\s+){0,2}(?:options|variants|versions|choices)\b", re.I)
AMT = r"\$\s?(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)"
AMT_NC = r"\$\s?(?:\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)"
ARITH_RX = re.compile(r"(?<![\w.,])" + AMT + r"((?:\s*[-−–+]\s*" + AMT_NC + r")+)\s*=\s*" + AMT)
TERM_RX = re.compile(r"([-−–+])\s*" + AMT)
IN_SCOPE_RX = re.compile(r"\b(cancel|return|exchange|refund|swap|modify|change (the |my )?(address|item|size|color|payment))", re.I)
HUMAN_RX = re.compile(r"\b(human|real person|supervisor|manager|representative)\b", re.I)
KIND_RX = {"credit_card": re.compile(r"credit|card|visa|mastercard|amex|discover|\d{4}", re.I),
           "paypal": re.compile(r"paypal", re.I),
           "gift_card": re.compile(r"gift", re.I)}

NOTES = {
    "status_precondition": "Policy check: order {oid} has status '{status}', but {name} requires status '{need}'. Do not call it; "
                           "explain to the user what is possible for this order.",
    "cancel_reason": "Consistency check: the user's words indicate the cancellation reason is '{want}', not '{got}'. Use the "
                     "reason the user gave (only 'no longer needed' or 'ordered by mistake' are valid), or ask.",
    "refund_method": "Policy check: a return refund must go to the order's original payment method ({orig}) or an existing gift "
                     "card; {pm} is neither. Ask the user to choose one of the allowed methods.",
    "new_item_unavailable": "Consistency check: new item {item} is {why}. Pick an available variant of the same product that matches "
                            "the options the user asked for, or tell the user it is unavailable.",
    "order_unmentioned": "Review before acting: the user has several orders and has not named order {oid} or any product in it. "
                         "Make sure this is the order the user means; if unsure, ask.",
    "address_unseen": "Review before acting: the address in this call ({addr}) does not appear in what the user wrote. Use exactly "
                      "the address the user gave, character by character, or ask the user to confirm it.",
    "payment_unconfirmed": "Review before acting: the user has not said which payment method to use; {pm} was not chosen by the "
                           "user. Ask which payment method to use (policy requires the user to provide it).",
    "items_partial": "Review before acting: the user mentioned {names}, which is also in order {oid} but not in this call. "
                     "Exchange/modify can be called only once per order: collect every item the user wants first.",
    "option_count": "Consistency check: the product lookup shows {total} variants but only {avail} are available. When telling "
                    "the user how many options there are, count available variants ({avail}) unless they asked about all of them.",
    "arithmetic": "Arithmetic check: {expr} is wrong; the correct result is {right}. Correct the amount before telling the user "
                  "(use the calculate tool for any further price arithmetic).",
    "transfer_in_scope": "Review before transferring: the user's request ({req}) is within your scope and has not been attempted. "
                         "Transfer only if the request cannot be handled with your tools; otherwise handle it per policy.",
}


class RetailConsistencyChecker:
    def __init__(self, messages: Iterable[Any]):
        self.user_texts: list[str] = []
        self.orders: dict[str, dict] = {}
        self.profile: dict = {}
        self.variants: dict[str, dict] = {}     # item_id -> {"product_id", "available", "options"}
        self.last_product: dict = {}
        self.writes_done = 0
        for m in messages:
            self._observe(_as_dict(m))

    def _observe(self, m: dict) -> None:
        role = m.get("role")
        if role == "user":
            self.user_texts.append(m.get("content") or "")
        elif role == "assistant":
            self.writes_done += sum(tc.get("name") in WRITES for tc in m.get("tool_calls") or [])
        elif role == "tool":
            j = _json(m.get("content"))
            if not isinstance(j, dict):
                return
            if "order_id" in j and "items" in j:
                self.orders[j["order_id"]] = j
            elif "payment_methods" in j and "user_id" in j:
                self.profile = j
            elif "variants" in j and "product_id" in j:
                self.last_product = j
                for iid, v in (j.get("variants") or {}).items():
                    self.variants[iid] = {"product_id": j["product_id"], "available": v.get("available"), "options": v.get("options")}

    def _users(self) -> str:
        return " ".join(self.user_texts)

    def check(self, am: Any, active: frozenset = ACTIVE) -> list[tuple[str, str, str]]:
        return [h for h in self.check_all(am) if h[0] in active]

    def _message_checks(self, txt: str) -> list[tuple[str, str, str]]:
        out: list[tuple[str, str, str]] = []
        v = (self.last_product.get("variants") or {}).values()
        total, avail = len(v), sum(bool(x.get("available")) for x in v)
        if total and avail < total:
            for m in COUNT_RX.finditer(txt):
                if int(m.group(1)) == total:
                    out.append(("option_count", "hard", NOTES["option_count"].format(total=total, avail=avail)))
                    break
        num = lambda x: float(x.replace(",", ""))
        for m in ARITH_RX.finditer(txt):
            right = num(m.group(1)) + sum(num(v) if op == "+" else -num(v) for op, v in TERM_RX.findall(m.group(2)))
            c = num(m.group(m.lastindex))
            if abs(right - c) > 0.005 and abs(abs(right) - c) > 0.005:
                out.append(("arithmetic", "hard", NOTES["arithmetic"].format(expr=m.group(0), right=f"{right:.2f}")))
        return out

    def check_all(self, am: Any) -> list[tuple[str, str, str]]:
        am = _as_dict(am)
        out: list[tuple[str, str, str]] = []
        if not am.get("tool_calls") and am.get("content"):
            return self._message_checks(am["content"])
        users = self._users()
        low = users.lower()
        for tc in am.get("tool_calls") or []:
            name, a = tc.get("name"), tc.get("arguments") or {}
            o = self.orders.get(a.get("order_id"))
            # -- hard
            if name in NEEDS and o and o.get("status") != NEEDS[name]:
                out.append(("status_precondition", "hard", NOTES["status_precondition"].format(
                    oid=o["order_id"], status=o.get("status"), name=name, need=NEEDS[name])))
            if name == "cancel_pending_order":
                want = ("ordered by mistake" if MISTAKE_RX.search(users) and not NOT_NEEDED_RX.search(users) else
                        "no longer needed" if NOT_NEEDED_RX.search(users) and not MISTAKE_RX.search(users) else None)
                if want and a.get("reason") != want:
                    out.append(("cancel_reason", "hard", NOTES["cancel_reason"].format(want=want, got=a.get("reason"))))
            if name == "return_delivered_order_items" and o and a.get("payment_method_id"):
                pm = a["payment_method_id"]
                orig = {p.get("payment_method_id") for p in o.get("payment_history") or []}
                if orig and pm not in orig and not pm.startswith("gift_card"):
                    out.append(("refund_method", "hard", NOTES["refund_method"].format(orig=", ".join(sorted(orig)), pm=pm)))
            if name in ("modify_pending_order_items", "exchange_delivered_order_items") and o:
                old = {it["item_id"]: it for it in o.get("items") or []}
                for i, new in enumerate(a.get("new_item_ids") or []):
                    v = self.variants.get(new)
                    olditem = old.get((a.get("item_ids") or [None] * (i + 1))[i]) if i < len(a.get("item_ids") or []) else None
                    why = None
                    if v and v.get("available") is False:
                        why = "shown as unavailable in the product lookup"
                    elif v and olditem and v["product_id"] != olditem.get("product_id"):
                        why = "a different product from the item it replaces (only option changes are allowed)"
                    if why:
                        out.append(("new_item_unavailable", "hard", NOTES["new_item_unavailable"].format(item=new, why=why)))
            # -- soft
            if name in WRITES and name != "modify_user_address" and o and len(self.profile.get("orders") or []) > 1:
                named = o["order_id"].lstrip("#") in users or any(
                    (it.get("name") or "").lower() in low for it in o.get("items") or [])
                if not named:
                    out.append(("order_unmentioned", "soft", NOTES["order_unmentioned"].format(oid=o["order_id"])))
            if name in ("modify_pending_order_address", "modify_user_address"):
                a1, z = str(a.get("address1") or ""), str(a.get("zip") or "")
                num = re.match(r"\d+", a1)
                if (z and z not in users) or (num and num.group() not in users):
                    out.append(("address_unseen", "soft", NOTES["address_unseen"].format(addr=f"{a1}, {z}")))
            pm = a.get("payment_method_id")
            if pm and name in ("modify_pending_order_items", "exchange_delivered_order_items", "modify_pending_order_payment",
                               "return_delivered_order_items"):
                kind = next((k for k in KIND_RX if pm.startswith(k)), None)
                if kind and not KIND_RX[kind].search(users) and pm not in users:
                    out.append(("payment_unconfirmed", "soft", NOTES["payment_unconfirmed"].format(pm=pm)))
            if name in ("return_delivered_order_items", "exchange_delivered_order_items", "modify_pending_order_items") and o:
                chosen = set(a.get("item_ids") or [])
                chosen_names = {(it.get("name") or "").lower() for it in o.get("items") or [] if it["item_id"] in chosen}
                left = sorted({(it.get("name") or "") for it in o.get("items") or []
                               if it["item_id"] not in chosen and (it.get("name") or "").lower() in low
                               and (it.get("name") or "").lower() not in chosen_names})
                if left:
                    out.append(("items_partial", "soft", NOTES["items_partial"].format(names=", ".join(left), oid=o["order_id"])))
            if name == "transfer_to_human_agents" and self.writes_done == 0:
                m = IN_SCOPE_RX.search(users)
                if m and not HUMAN_RX.search(users):
                    out.append(("transfer_in_scope", "soft", NOTES["transfer_in_scope"].format(req=m.group(0))))
        return out
