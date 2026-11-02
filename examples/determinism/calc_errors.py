"""How many E4 failures are calculation / selection errors? (zero cost, 2026-11-02)

For each failed trial of the two E4 airline runs (8 trials per task), compare the agent's write calls with the gold
actions of the task and classify the first mismatching gold write by the argument that differs:
  cheapest_selection  flights differ and the task asks for the cheapest option
  flight_selection    flights differ otherwise
  amount              payment amounts differ (same payment ids)
  payment_choice      payment ids / number of payment methods differ
  bags / insurance / passengers / cabin / other_arg
  missing_write       gold write never attempted with that tool
  extra_write         all gold writes matched but extra writes were made (or a transfer)
  no_write_issue      writes all correct (failure from communication / DB side effects)
Also counts agent self-corrections ("I made an error", "correction") as evidence of computation slips.
"""
import json, re
from collections import Counter
from pathlib import Path

import sys
sys.path.insert(0, "/home/user/tau2-bench/src")
from tau2.registry import registry  # noqa: E402

RUNS = ["deliberate_reasoner_rules_consistency"] + [f"e4_mined-fold{k}" for k in range(3)]
WRITES = {"cancel_reservation", "update_reservation_flights", "update_reservation_baggages",
          "update_reservation_passengers", "book_reservation", "send_certificate"}
SELF_FIX = re.compile(r"(made|I made) an? (arithmetic )?error|correction|I misspoke|I apologi[sz]e.{0,40}(mistake|error)|actually (the )?cheapest", re.I)
T = {str(t.id): t for t in registry.get_tasks_loader("airline")()}


def classify(task, M):
    gold = [a for a in (task.evaluation_criteria.actions or []) if a.name in WRITES]
    agent = [(t["name"], t.get("arguments") or {}) for m in M if m["role"] == "assistant" for t in (m.get("tool_calls") or [])
             if t["name"] in WRITES | {"transfer_to_human_agents"}]
    instr = str(task.user_scenario.instructions).lower()
    used = set()
    for g in gold:
        ga = g.arguments or {}
        exact = [i for i, (n, a) in enumerate(agent) if n == g.name and i not in used
                 and all(a.get(k) == v for k, v in ga.items())]
        if exact:
            used.add(exact[0]); continue
        cands = [(i, a) for i, (n, a) in enumerate(agent) if n == g.name and i not in used]
        if not cands:
            return "missing_write", g.name
        # closest candidate = fewest differing keys
        i, a = min(cands, key=lambda c: sum(c[1].get(k) != v for k, v in ga.items()))
        diff = [k for k, v in ga.items() if a.get(k) != v]
        if "flights" in diff:
            return ("cheapest_selection" if "cheap" in instr else "flight_selection"), g.name
        for k, lab in (("total_baggages", "bags"), ("nonfree_baggages", "bags"), ("insurance", "insurance"),
                       ("passengers", "passengers"), ("cabin", "cabin")):
            if k in diff:
                return lab, g.name
        if "payment_methods" in diff or "payment_id" in diff:
            gp, ap = ga.get("payment_methods") or [], a.get("payment_methods") or []
            if sorted(p.get("payment_id") for p in gp) == sorted(p.get("payment_id") for p in ap):
                return "amount", g.name
            return "payment_choice", g.name
        return "other_arg:" + ",".join(diff), g.name
    if len(agent) > len(used):
        return "extra_write", agent[[i for i in range(len(agent)) if i not in used][0]][0]
    return "no_write_issue", None


def main():
    ok = lambda s: ((s.get("reward_info") or {}).get("reward") or 0) >= 0.999
    sims = [s for r in RUNS for s in json.load(open(f"reports/anchor/airline-{r}/results.json"))["simulations"]]
    succ = Counter(str(s["task_id"]) for s in sims if ok(s))
    out, rows = {"flaky": Counter(), "always": Counter()}, []
    selffix = Counter()
    for s in sims:
        t = str(s["task_id"])
        fixed = any(m["role"] == "assistant" and SELF_FIX.search(m.get("content") or "") for m in s["messages"])
        selffix[("success" if ok(s) else "fail", fixed)] += 1
        if ok(s):
            continue
        kind, tool = classify(T[t], s["messages"])
        grp = "flaky" if succ[t] else "always"
        out[grp][kind] += 1
        rows.append({"task": t, "group": grp, "kind": kind, "tool": tool, "self_correction": fixed})
    res = {"flaky": dict(out["flaky"].most_common()), "always": dict(out["always"].most_common()),
           "self_correction": {f"{k[0]}:{k[1]}": v for k, v in selffix.items()}, "rows": rows,
           "by_task": {}}
    for r in rows:
        res["by_task"].setdefault(r["task"], Counter())[r["kind"]] += 1
    res["by_task"] = {t: dict(c) for t, c in sorted(res["by_task"].items(), key=lambda x: int(x[0]))}
    Path("reports/rsi/calc_errors.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: res[k] for k in ("flaky", "always", "self_correction", "by_task")}, indent=1))


main()
