"""Zero-cost audit of the retail consistency checks (src/gdopt/adapters/tau2_retail_rules.py) on the logged retail runs.

For every assistant step with tool calls, build the checker from the messages before it and count fires in successful
vs failed episodes (per call and per episode), with the Clopper-Pearson upper bound on the share of fires that land in
successful episodes. Run from repo root; writes reports/determinism/retail_rule_audit.json.
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).parent))
from gdopt.adapters.tau2_retail_rules import RetailConsistencyChecker  # noqa: E402
from solidify_estimate import ucb  # noqa: E402

RUNS = sys.argv[1:] or ["retail-none", "retail-deliberate_reasoner"]


def main():
    calls, eps, tasks, n = defaultdict(Counter), defaultdict(Counter), defaultdict(Counter), Counter()
    for run in RUNS:
        for s in json.load(open(f"reports/anchor/{run}/results.json"))["simulations"]:
            ok = ((s.get("reward_info") or {}).get("reward") or 0.0) >= 0.999
            key = "success" if ok else "fail"
            n[key] += 1
            fired = set()
            msgs = s["messages"]
            for i, m in enumerate(msgs):
                if m.get("role") == "assistant":
                    for r, _, _ in RetailConsistencyChecker(msgs[:i]).check_all(m):
                        calls[r][key] += 1
                        fired.add(r)
            for r in fired:
                eps[r][key] += 1
                tasks[r][str(s["task_id"])] += 1
    out = {"runs": RUNS, "episodes": dict(n), "rules": {}}
    for r in sorted(calls):
        c, e = calls[r], eps[r]
        out["rules"][r] = {"eps_success": e["success"], "eps_fail": e["fail"], "calls_success": c["success"],
                           "calls_fail": c["fail"], "harm_ucb95": round(ucb(e["success"], e["success"] + e["fail"]), 3),
                           "tasks": dict(tasks[r].most_common(8))}
        print(f"{r:22s} eps S/F {e['success']:3d}/{e['fail']:3d}  calls S/F {c['success']:3d}/{c['fail']:3d}  tasks {dict(tasks[r].most_common(6))}")
    print(dict(n))
    Path("reports/determinism/retail_rule_audit.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
