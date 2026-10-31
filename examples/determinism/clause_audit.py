"""E1 of the solidification plan: audit hand-written airline policy-clause predicates on logged τ² episodes.

Each rule is a predicate over facts the agent has already seen in tool outputs (reservations, user profile, flight
statuses, search results) plus, for the confirmation rule, the last user message. It is evaluated at every write-tool
call; a "fire" means the rule says the call violates the policy (verdict forbid) or lacks an explicit user yes
(verdict confirm). Harm = fires inside successful episodes (the rule would have blocked something that succeeded);
benefit = fires inside failed episodes. Clopper-Pearson upper bounds on the harm rate are reported per rule.

Zero API cost: reads reports/anchor/airline-*/results.json. Run from repo root. Env: ANCHOR_DIR, OUT_DIR.
"""
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from solidify_estimate import ucb  # noqa: E402

from gdopt.adapters.tau2_rules import CLAUSES, PolicyFacts  # noqa: E402

ANCHOR = Path(os.environ.get("ANCHOR_DIR", "reports/anchor"))
OUT = Path(os.environ.get("OUT_DIR", "reports/determinism"))
RUNS = ["none", "veto", "hint", "checklist", "deliberate", "reasoner", "deliberate_all", "deliberate_reasoner"]
RULES = list(CLAUSES)


def audit_episode(s):
    """(rule, tool name, message index) for every rule fire on a tool call of this episode, facts as of that call."""
    fires, facts = [], PolicyFacts()
    for i, m in enumerate(s["messages"]):
        if m.get("role") == "assistant":
            for tc in m.get("tool_calls") or []:
                fires += [(h, tc["name"], i) for h, _ in facts.check(tc["name"], tc.get("arguments") or {})]
        facts.observe(m)
    return fires


def main():
    calls = defaultdict(Counter)   # rule -> {success, fail} call counts
    eps = defaultdict(Counter)     # rule -> {success, fail} episode counts
    flagged = []
    n_eps = Counter()
    for run in RUNS:
        p = ANCHOR / f"airline-{run}" / "results.json"
        if not p.exists():
            continue
        for s in json.load(open(p))["simulations"]:
            ok = ((s.get("reward_info") or {}).get("reward") or 0.0) >= 0.999
            n_eps["success" if ok else "fail"] += 1
            f = audit_episode(s)
            for rule in {h for h, _, _ in f}:
                eps[rule]["success" if ok else "fail"] += 1
            for h, _, _ in f:
                calls[h]["success" if ok else "fail"] += 1
            forb = [(h, i) for h, _, i in f if h != "confirm_before_write"]
            if forb:
                flagged.append({"run": run, "task": str(s["task_id"]), "trial": s["trial"], "success": ok, "rules": [h for h, _ in forb],
                                "first_msg_index": min(i for _, i in forb)})
    out = {"episodes": dict(n_eps), "rules": {}}
    for rule in RULES:
        c, e = calls[rule], eps[rule]
        out["rules"][rule] = {"clause": CLAUSES[rule], "calls_success": c["success"], "calls_fail": c["fail"],
                              "eps_success": e["success"], "eps_fail": e["fail"],
                              "harm_ucb95": round(ucb(c["success"], c["success"] + c["fail"]), 3) if c else None}
        print(f"{rule:22s} calls S/F {c['success']:3d}/{c['fail']:3d}  eps S/F {e['success']:3d}/{e['fail']:3d}  "
              f"UCB {out['rules'][rule]['harm_ucb95']}")
    forb_rules = [r for r in RULES if r != "confirm_before_write"]
    clean = [r for r in forb_rules if calls[r]["success"] == 0 and calls[r]["fail"] > 0]
    tot = Counter()
    for r in clean:
        tot["fail"] += calls[r]["fail"]
    out["zero_harm_forbid_rules"] = clean
    out["zero_harm_forbid_calls_fail"] = tot["fail"]
    out["zero_harm_forbid_ucb95"] = round(ucb(0, tot["fail"]), 3) if tot["fail"] else None
    out["flagged_failed_episodes"] = len({(x["run"], x["task"], x["trial"]) for x in flagged if not x["success"]})
    out["flagged"] = flagged
    print("episodes", dict(n_eps), "zero-harm forbid rules", clean, "calls", tot["fail"], "UCB", out["zero_harm_forbid_ucb95"],
          "failed eps flagged by forbid rules", out["flagged_failed_episodes"])
    (OUT / "clause_audit.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
