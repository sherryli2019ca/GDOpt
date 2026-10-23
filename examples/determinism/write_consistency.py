import json, re
from collections import defaultdict
import os
from pathlib import Path
from gdopt.adapters.tau2 import load_results, load_gold_actions
SRC = Path(os.environ.get("TAU2_BENCH_ROOT", "../tau2-bench")) / Path("src/tau2/domains")
RES = Path(os.environ.get("TAU2_BENCH_ROOT", "../tau2-bench")) / Path("data/tau2/results/final")
OUT = Path(os.environ.get("OUT_DIR", "reports/determinism"))
def write_tools(domain):
    src = (SRC / domain / "tools.py").read_text()
    return set(re.findall(r"@is_tool\(ToolType\.WRITE\)\s*\n\s*def\s+(\w+)", src))
def norm(v): return json.dumps(v, sort_keys=True, default=str)
rows = []
for f in sorted(RES.glob("*_default_gpt-4.1-2025-04-14_4trials.json")):
    if "telecom-workflow" in f.name: continue
    agent, domain = f.name.split("_")[0], f.name.split("_")[1]
    wt = write_tools(domain) | {"transfer_to_human_agents"}
    trajs = load_results(f); gold = load_gold_actions(f)
    by = defaultdict(list)
    for t in trajs: by[t.task_id].append(t)
    def names(t): return tuple(tc.name for m in t.messages if m.role == "assistant" for tc in m.tool_calls if tc.name in wt)
    def full(t): return tuple((tc.name, norm(tc.arguments)) for m in t.messages if m.role == "assistant" for tc in m.tool_calls if tc.name in wt)
    un_all = sum(1 for v in by.values() if len({names(t) for t in v}) == 1)
    un_all_args = sum(1 for v in by.values() if len({full(t) for t in v}) == 1)
    s2 = [v for v in by.values() if sum(t.success for t in v) >= 2]
    un_succ = sum(1 for v in s2 if len({names(t) for t in v if t.success}) == 1)
    un_succ_args = sum(1 for v in s2 if len({full(t) for t in v if t.success}) == 1)
    f2 = [v for v in by.values() if sum(not t.success for t in v) >= 2]
    un_fail = sum(1 for v in f2 if len({names(t) for t in v if not t.success}) == 1)
    ok = tot = 0
    for k, v in by.items():
        g = sorted(n for n, _ in gold.get(k, []) if n in wt)
        for t in v:
            if t.success: tot += 1; ok += (sorted(names(t)) == g)
    rows.append({"agent": agent, "domain": domain, "n_tasks": len(by), "write_tools": sorted(wt),
                 "write_names_unanimous_all": round(un_all / len(by), 3),
                 "write_full_unanimous_all": round(un_all_args / len(by), 3),
                 "tasks_2succ": len(s2),
                 "write_names_unanimous_succ": round(un_succ / len(s2), 3),
                 "write_full_unanimous_succ": round(un_succ_args / len(s2), 3),
                 "tasks_2fail": len(f2),
                 "write_names_unanimous_fail": round(un_fail / len(f2), 3) if f2 else None,
                 "succ_write_names_match_gold": round(ok / tot, 3)})
for r in rows: print({k: v for k, v in r.items() if k != "write_tools"})
print({r["domain"]: r["write_tools"] for r in rows[:3]})
(OUT / "writes2.json").write_text(json.dumps(rows, indent=1))
