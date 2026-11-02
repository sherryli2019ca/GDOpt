"""Zero-cost estimate for "solidifying" sensitive situations into fixed rules.

A sensitive step is an agent step where the logged Jev p_max < TAU (default 0.8). For every such step we build a
situation key from information available online at that step (no future leakage), at three granularities:
  coarse : (previous agent action, Jev top-1)
  policy_lite[_nojev] : (previous action, [Jev top-1,] last reservation facts[, intents])
  policy : coarse + user intents mentioned so far + attributes of the last reservation read
           (cabin, insurance, booked <24h ago, any segment already flown, flight cancelled by airline) + membership
  task   : (task id, previous action, number of writes so far)  -- within-task memorisation, upper bound only
Rules are learned from SUCCESSFUL episodes only (majority action per key) and evaluated leave-task-out: for each task,
the rule table is rebuilt without any episode of that task (any run), then applied to that task's sensitive steps.
Reports recurrence (key support in distinct tasks), purity of successful actions, held-out agreement on successful
vs failed episodes, and the success/failure fork test: at the first divergence between a successful and a failed
trial of the same task, does the rule pick the successful or the failed branch?
Also simulates Learn-then-Test activation (binomial upper bound on held-out rule error) over support thresholds.

Reads reports/anchor/airline-{veto,hint,deliberate,reasoner,deliberate_reasoner}/results.json. Run from repo root.
Env: ANCHOR_DIR, OUT_DIR, TAU.
"""
import json
import math
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ANCHOR = Path(os.environ.get("ANCHOR_DIR", "reports/anchor"))
OUT = Path(os.environ.get("OUT_DIR", "reports/determinism"))
TAU = float(os.environ.get("TAU", "0.8"))
RUNS = ["veto", "hint", "deliberate", "reasoner", "deliberate_reasoner"]
NOW = datetime(2024, 5, 15, 15, 0, 0)  # τ² airline policy "current time"
WRITES = {"cancel_reservation", "update_reservation_flights", "update_reservation_baggages",
          "update_reservation_passengers", "book_reservation", "send_certificate"}
INTENTS = [("cancel", r"cancel|refund"), ("change", r"chang|modif|reschedul|switch|move my|different flight"),
           ("baggage", r"bag"), ("compens", r"compensat|certificate|voucher|reimburs"),
           ("book", r"\bbook|new reservation|new flight"), ("cabin", r"upgrade|downgrade|cabin|business|economy"),
           ("passenger", r"passenger|name on"), ("insurance", r"insurance")]


def action(m):
    tc = m.get("tool_calls")
    return "tool:" + tc[0]["name"] if tc else "message"


def parse_json(s):
    try:
        return json.loads(s)
    except Exception:
        return None


def load(run):
    d = json.load(open(ANCHOR / f"airline-{run}" / "results.json"))
    eps = []
    for s in d["simulations"]:
        steps, intents, res, member, prev, writes = [], set(), None, None, "start", 0
        for m in s["messages"]:
            role = m.get("role")
            if role == "user":
                txt = (m.get("content") or "").lower()
                intents |= {k for k, rx in INTENTS if re.search(rx, txt)}
                continue
            if role == "tool":
                j = parse_json(m.get("content") or "")
                if isinstance(j, dict):
                    if "membership" in j:
                        member = j["membership"]
                    if "reservation_id" in j and "cabin" in j:
                        res = j
                continue
            if role != "assistant":
                continue
            g = (m.get("raw_data") or {}).get("gdopt")
            act = action(m)
            if g:
                a = g.get("anchor", {})
                steps.append({"p": a.get("jev_p"), "top": a.get("jev_top"), "act": act, "prev": prev,
                              "intents": tuple(sorted(intents)), "res": res_feats(res), "member": member,
                              "writes": writes})
            prev = act
            writes += act.replace("tool:", "") in WRITES
        r = (s.get("reward_info") or {}).get("reward") or 0.0
        eps.append({"run": run, "task": str(s["task_id"]), "trial": s["trial"], "success": r >= 0.999,
                    "steps": steps})
    return eps


def res_feats(r):
    if not r:
        return None
    try:
        age_h = (NOW - datetime.fromisoformat(r["created_at"])).total_seconds() / 3600
    except Exception:
        age_h = None
    flown = any(f.get("date", "9999") < "2024-05-15" for f in r.get("flights", []))
    return (r.get("cabin"), r.get("insurance"), None if age_h is None else age_h < 24, flown, r.get("status"))


def key(st, ep, level):
    if level == "coarse":
        return (st["prev"], st["top"])
    if level == "policy":
        return (st["prev"], st["top"], st["intents"], st["res"], st["member"])
    if level == "policy_lite":  # drop intents and membership, keep reservation facts
        return (st["prev"], st["top"], st["res"])
    if level == "policy_lite_nojev":  # no Jev top-1: identical for both trials when their visible facts match
        return (st["prev"], st["res"], st["intents"])
    if level == "task":
        return (ep["task"], st["prev"], st["writes"])
    raise ValueError(level)


def table(eps, level, exclude_task=None):
    t = defaultdict(lambda: {"acts": Counter(), "tasks": set()})
    for e in eps:
        if not e["success"] or e["task"] == exclude_task:
            continue
        for st in e["steps"]:
            if st["p"] is None or st["p"] >= TAU:
                continue
            k = key(st, e, level)
            t[k]["acts"][st["act"]] += 1
            t[k]["tasks"].add(e["task"])
    return t


def ucb(err, n, delta=0.05):
    """Exact one-sided Clopper-Pearson upper bound on the error rate (binomial tail by bisection, log space)."""
    if n == 0:
        return 1.0
    lo, hi = err / n, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        cdf = sum(math.exp(math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1)
                           + i * math.log(max(mid, 1e-300)) + (n - i) * math.log(max(1 - mid, 1e-300)))
                  for i in range(err + 1))
        lo, hi = (mid, hi) if cdf > delta else (lo, mid)
    return hi


def cancel_predicate():
    """Policy-clause grounding test: cancellation eligibility as a code predicate over reservation facts.

    τ² airline policy: cancellable if booked within 24 h, or the airline cancelled the flight, or cabin is business,
    or travel insurance covers the stated reason (health/weather). No segment may have been flown. The insurance
    clause depends on the user's reason, which is free text, so it is left undecided (-> LLM). For every
    cancel_reservation call we evaluate the predicate on the reservation it targets, and tabulate episode success.
    """
    out = Counter()
    for run in RUNS:
        d = json.load(open(ANCHOR / f"airline-{run}" / "results.json"))
        for s in d["simulations"]:
            ok = ((s.get("reward_info") or {}).get("reward") or 0.0) >= 0.999
            res, seen_cancel = {}, False
            for m in s["messages"]:
                if m.get("role") == "tool":
                    j = parse_json(m.get("content") or "")
                    if isinstance(j, dict) and "reservation_id" in j and "cabin" in j and "created_at" in j:
                        res.setdefault(j["reservation_id"], j)
                if m.get("role") == "assistant":
                    for tc in m.get("tool_calls") or []:
                        if tc["name"] == "update_reservation_flights":
                            a = tc.get("arguments") or {}
                            r = res.get(a.get("reservation_id"))
                            if r and r.get("cabin") == "basic_economy" and a.get("cabin") == "basic_economy":
                                old = sorted(f["flight_number"] + f["date"] for f in r.get("flights", []))
                                new = sorted(f.get("flight_number", "") + f.get("date", "") for f in a.get("flights", []))
                                out[("modify_basic_economy_flights:" + ("forbidden" if old != new else "same"),
                                     ok)] += 1
                            continue
                        if tc["name"] != "cancel_reservation":
                            continue
                        seen_cancel = True
                        r = res.get((tc.get("arguments") or {}).get("reservation_id"))
                        if r is None:
                            out[("unread", ok)] += 1
                            continue
                        f = res_feats(r)
                        cabin, ins, lt24, flown, status = f
                        if flown:
                            v = "forbidden(flown)"
                        elif lt24 or cabin == "business" or status == "cancelled":
                            v = "allowed"
                        elif ins == "yes":
                            v = "undecided(insurance)"
                        else:
                            v = "forbidden"
                        out[(v, ok)] += 1
            if not seen_cancel:
                out[("no_cancel_call", ok)] += 1
    table_ = defaultdict(dict)
    for (v, ok), c in out.items():
        table_[v]["success" if ok else "fail"] = c
    print("cancel predicate", dict(table_))
    return dict(table_)


def main():
    eps = [e for r in RUNS for e in load(r)]
    tasks = sorted({e["task"] for e in eps})
    sens = [(e, st) for e in eps for st in e["steps"] if st["p"] is not None and st["p"] < TAU]
    report = {"tau": TAU, "episodes": len(eps), "steps": sum(len(e["steps"]) for e in eps),
              "sensitive_steps": len(sens), "sensitive_steps_in_success": sum(e["success"] for e, _ in sens),
              "levels": {}}
    # success/failure forks per (run, task)
    forks = []
    for r in RUNS:
        by = defaultdict(list)
        for e in eps:
            if e["run"] == r:
                by[e["task"]].append(e)
        for es in by.values():
            for a in es:
                for b in es:
                    if not (a["success"] and not b["success"]):
                        continue
                    A, B = a["steps"], b["steps"]
                    t = next((t for t in range(min(len(A), len(B))) if A[t]["act"] != B[t]["act"]), None)
                    if t is not None:
                        forks.append((a, b, t))
    report["succ_fail_forks"] = len(forks)
    for level in ["coarse", "policy_lite", "policy_lite_nojev", "policy", "task"]:
        full = table(eps, level)
        # recurrence and purity on the full successful table
        sup_tasks = Counter()
        purity_w = purity_n = 0
        for k, v in full.items():
            n = sum(v["acts"].values())
            purity_w += v["acts"].most_common(1)[0][1]
            purity_n += n
        rec = {m: 0 for m in (1, 2, 3, 5)}
        succ_sens = [(e, st) for e, st in sens if e["success"]]
        for e, st in succ_sens:
            k = key(st, e, level)
            for m in rec:
                rec[m] += len(full[k]["tasks"]) >= m if k in full else 0
        # leave-task-out evaluation
        loo = {t: table(eps, level, exclude_task=t) for t in tasks}

        def rule(e, st, min_tasks, min_purity):
            v = loo[e["task"]].get(key(st, e, level))
            if not v or len(v["tasks"]) < min_tasks:
                return None
            a, c = v["acts"].most_common(1)[0]
            return a if c / sum(v["acts"].values()) >= min_purity else None

        grid = {}
        for min_tasks in (2, 3, 5):
            for min_purity in (0.6, 0.8, 0.9):
                fired = {True: [0, 0], False: [0, 0]}  # success flag -> [fired, agreed]
                for e, st in sens:
                    a = rule(e, st, min_tasks, min_purity)
                    if a is None:
                        continue
                    fired[e["success"]][0] += 1
                    fired[e["success"]][1] += a == st["act"]
                fk = Counter()
                for a_ep, b_ep, t in forks:
                    st_s, st_f = a_ep["steps"][t], b_ep["steps"][t]
                    if st_f["p"] is None or st_f["p"] >= TAU:
                        fk["not_sensitive"] += 1
                        continue
                    ra = rule(b_ep, st_f, min_tasks, min_purity)  # rule evaluated on the failing trial's state
                    rs = rule(a_ep, st_s, min_tasks, min_purity)  # same rule on the successful trial's state
                    if rs is not None:
                        fk["succ_state:" + ("success_branch" if rs == st_s["act"] else
                                            "failed_branch" if rs == st_f["act"] else "other")] += 1
                    if ra is None:
                        fk["no_rule"] += 1
                    elif ra == st_s["act"]:
                        fk["rule=success_branch"] += 1
                    elif ra == st_f["act"]:
                        fk["rule=failed_branch"] += 1
                    else:
                        fk["rule=other"] += 1
                ns, nf = fired[True][0], fired[False][0]
                err = ns - fired[True][1]
                grid[f"tasks>={min_tasks},purity>={min_purity}"] = {
                    "coverage_of_sensitive_steps": round((ns + nf) / len(sens), 3),
                    "heldout_agree_success_eps": round(fired[True][1] / ns, 3) if ns else None,
                    "heldout_agree_failed_eps": round(fired[False][1] / nf, 3) if nf else None,
                    "fired_success_eps": ns, "fired_failed_eps": nf,
                    "rule_error_ucb95_on_success_eps": round(ucb(err, ns), 3) if ns else None,
                    "forks": dict(fk)}
        report["levels"][level] = {
            "distinct_keys_in_success": len(full),
            "success_purity_weighted": round(purity_w / purity_n, 3),
            "share_success_sensitive_steps_with_key_in_>=m_tasks": {m: round(c / len(succ_sens), 3)
                                                                   for m, c in rec.items()},
            "loo_grid": grid}
        print(level, json.dumps(report["levels"][level]["share_success_sensitive_steps_with_key_in_>=m_tasks"]),
              "purity", report["levels"][level]["success_purity_weighted"], "keys", len(full))
        for g, v in grid.items():
            print("  ", g, v["coverage_of_sensitive_steps"], v["heldout_agree_success_eps"],
                  v["heldout_agree_failed_eps"], v["rule_error_ucb95_on_success_eps"], v["forks"])
    # most frequent policy-level recurring keys
    full = table(eps, "policy_lite")
    top = sorted(full.items(), key=lambda kv: -len(kv[1]["tasks"]))[:15]
    report["top_policy_lite_keys"] = [{"key": [str(x) for x in k], "tasks": len(v["tasks"]),
                                       "acts": dict(v["acts"].most_common(3))} for k, v in top]
    for x in report["top_policy_lite_keys"]:
        print(x)
    print({k: report[k] for k in ("episodes", "steps", "sensitive_steps", "sensitive_steps_in_success",
                                  "succ_fail_forks")})
    report["cancel_predicate"] = cancel_predicate()
    (OUT / "solidify_estimate.json").write_text(json.dumps(report, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
