"""Audit candidate consistency rules found by reading the flaky tasks of the pooled deliberate+reasoner runs.

Each candidate is an online predicate on a write/transfer call (only facts visible at that point). For each we count
fires in successful vs failed episodes over all logged airline runs (zero API cost), like clause_audit.py.

  cheapest_not_min   the user asked for the cheapest option, but the chosen itinerary costs more than the cheapest
                     searched itinerary for the same cabin and endpoints (arithmetic / argmin done by code)
  substitute_book    book_reservation although the opening request was to change/cancel an existing trip and the
                     user never asked to book (a write that substitutes for a denied request;
                     also when the agent itself first offered to book a new/separate flight)
  pax_dob_mismatch   a booked passenger has the user's (or a saved passenger's) name but a different date of birth
  duplicate_write    the same write with identical arguments was already executed successfully
  transfer_pending   transfer_to_human_agents while an in-scope write the agent had already summarised for
                     confirmation has not been executed (side request should be declined, main request finished)
  write_after_done   a write after the user said everything is done / goodbye (proxy: user text with "that's all" etc.)

Run from repo root; writes reports/determinism/new_rule_audit.json.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from solidify_estimate import ucb  # noqa: E402

ANCHOR = Path("reports/anchor")
OUT = Path("reports/determinism")
RUNS = ["none", "veto", "hint", "checklist", "deliberate", "reasoner", "deliberate_all", "deliberate_reasoner",
        "deliberate_reasoner_rules"]
WRITES = {"cancel_reservation", "update_reservation_flights", "update_reservation_baggages",
          "update_reservation_passengers", "book_reservation", "send_certificate"}
CHEAP = re.compile(r"cheapest|lowest[- ]price|least expensive|lowest fare|cheaper", re.I)
CHANGE = re.compile(r"chang|modif|reschedul|move my|switch|push back|cancel|upgrade|downgrade", re.I)
BOOK = re.compile(r"\bbook|new (flight|reservation|ticket)|reserve a|buy a", re.I)
ASK_CONFIRM = re.compile(r"confirm|shall i|should i proceed|would you like me to (proceed|book|go ahead|make)|do you want me to", re.I)


def parse(s):
    try:
        return json.loads(s)
    except Exception:
        return None


def itineraries(results):
    """[(cabin_price_dict per itinerary, [flight numbers], origin, destination)] from a search result list."""
    out = []
    for o in results:
        legs = o if isinstance(o, list) else [o]
        if not all(isinstance(x, dict) and "prices" in x for x in legs):
            continue
        out.append(([x["prices"] for x in legs], [x["flight_number"] for x in legs], legs[0]["origin"], legs[-1]["destination"]))
    return out


def audit(s):
    fires = []
    user_texts, searched, res, profile = [], [], {}, None
    done_calls = set()
    pending_summary = False
    first_user = None
    pending = {}
    agent_offered_book = False  # the agent mentioned booking a new/separate flight before the user asked for one
    for m in s["messages"]:
        role = m.get("role")
        if role == "user":
            t = m.get("content") or ""
            user_texts.append(t)
            first_user = first_user if first_user is not None else t
            continue
        if role == "tool":
            j = parse(m.get("content") or "")
            name, args = pending.get(m.get("id"), (None, {}))
            if isinstance(j, list):
                searched += itineraries(j)
            elif isinstance(j, dict) and "reservation_id" in j and "cabin" in j:
                res[j["reservation_id"]] = j
            elif isinstance(j, dict) and "membership" in j:
                profile = j
            if name in WRITES and isinstance(j, dict):
                done_calls.add((name, json.dumps(args, sort_keys=True)))
            continue
        if role != "assistant":
            continue
        tcs = m.get("tool_calls") or []
        if not tcs:
            if not BOOK.search(" ".join(user_texts)) and re.search(r"(book|purchase) (a |an )?(new|separate)", m.get("content") or "", re.I):
                agent_offered_book = True
            if ASK_CONFIRM.search(m.get("content") or "") and searched:
                pending_summary = True
            continue
        all_user = " ".join(user_texts)
        for tc in tcs:
            name, a = tc["name"], tc.get("arguments") or {}
            pending[tc.get("id")] = (name, a)
            if name in WRITES and (name, json.dumps(a, sort_keys=True)) in done_calls:
                fires.append("duplicate_write")
            if name in ("update_reservation_flights", "book_reservation") and CHEAP.search(all_user) and a.get("flights"):
                cabin = a.get("cabin")
                r = res.get(a.get("reservation_id")) or {}
                o = a.get("origin") or r.get("origin")
                dst = a.get("destination") or r.get("destination")
                chosen = [f.get("flight_number") for f in a["flights"]]
                cands = [(sum(p.get(cabin, 1e9) for p in ps), fl) for ps, fl, so, sd in searched if so == o and sd == dst]
                mine = [c for c in cands if c[1] == chosen[: len(c[1])] or c[1] == chosen]
                if cands and mine and min(mine)[0] > min(cands)[0] + 1e-6:
                    fires.append("cheapest_not_min")
            if name == "book_reservation" and first_user and CHANGE.search(first_user) and (agent_offered_book or not BOOK.search(all_user)):
                fires.append("substitute_book")
            if name == "book_reservation" and profile:
                known = {(profile["name"]["first_name"].lower(), profile["name"]["last_name"].lower()): profile.get("dob")}
                for p in profile.get("saved_passengers", []) or []:
                    known[(p["first_name"].lower(), p["last_name"].lower())] = p.get("dob")
                for p in a.get("passengers", []):
                    k = (str(p.get("first_name", "")).lower(), str(p.get("last_name", "")).lower())
                    if k in known and known[k] and p.get("dob") and p["dob"] != known[k]:
                        fires.append("pax_dob_mismatch")
            if name == "transfer_to_human_agents" and pending_summary:
                fires.append("transfer_pending")
            if name in WRITES:
                pending_summary = False
                if user_texts and re.search(r"that'?s all|that is all|all set|nothing else|goodbye|bye", user_texts[-1], re.I):
                    fires.append("write_after_done")
    return fires


def main():
    calls, eps = defaultdict(Counter), defaultdict(Counter)
    n = Counter()
    tasks = defaultdict(Counter)
    for run in RUNS:
        p = ANCHOR / f"airline-{run}" / "results.json"
        if not p.exists():
            continue
        for s in json.load(open(p))["simulations"]:
            ok = ((s.get("reward_info") or {}).get("reward") or 0.0) >= 0.999
            key = "success" if ok else "fail"
            n[key] += 1
            f = audit(s)
            for r in f:
                calls[r][key] += 1
            for r in set(f):
                eps[r][key] += 1
                tasks[r][str(s["task_id"])] += 1
    out = {"episodes": dict(n), "rules": {}}
    for r in sorted(calls):
        c, e = calls[r], eps[r]
        out["rules"][r] = {"calls_success": c["success"], "calls_fail": c["fail"], "eps_success": e["success"],
                           "eps_fail": e["fail"], "harm_ucb95": round(ucb(c["success"], c["success"] + c["fail"]), 3),
                           "tasks": dict(tasks[r].most_common(8))}
        print(f"{r:18s} eps S/F {e['success']:3d}/{e['fail']:3d}  calls S/F {c['success']:3d}/{c['fail']:3d}  "
              f"UCB {out['rules'][r]['harm_ucb95']}  tasks {dict(tasks[r].most_common(6))}")
    print(dict(n))
    (OUT / "new_rule_audit.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
