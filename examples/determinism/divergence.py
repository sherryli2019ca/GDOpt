"""Where do flips originate? First divergence between a successful and a failed trial of the same task,
attributed to the situation (and its candidate tier) of the failed trial at that step.

Zero API cost: reads τ²-bench result files only.
Env: TAU2_BENCH_ROOT (clone of sierra-research/tau2-bench), OUT_DIR (where JSON goes).
Run with PYTHONPATH=src.
"""
import json
from collections import Counter, defaultdict
import os
from pathlib import Path
from gdopt.adapters.tau2 import load_results
from gdopt.profile import fit_situations, profile, split_by_trial, candidate_tiers
from gdopt.trace import is_tool_action
RES = Path(os.environ.get("TAU2_BENCH_ROOT", "../tau2-bench")) / Path("data/tau2/results/final")
OUT = Path(os.environ.get("OUT_DIR", "reports/determinism"))
rows = []
for f in sorted(RES.glob("*_default_gpt-4.1-2025-04-14_4trials.json")):
    if "telecom-workflow" in f.name: continue
    agent, domain = f.name.split("_")[0], f.name.split("_")[1]
    trajs = load_results(f)
    train, test = split_by_trial(trajs, [0, 1])
    model = fit_situations(train)
    rep = profile(model, train, test)
    tiers = candidate_tiers(rep)
    by = defaultdict(list)
    for t in trajs: by[t.task_id].append(t)
    by_tier = Counter(); by_kind = Counter(); n_pairs = 0; no_div = 0; pos = []
    for k, v in by.items():
        S = [t for t in v if t.success]; F = [t for t in v if not t.success]
        for s in S:
            ss = list(s.steps())
            for fl in F:
                fs = list(fl.steps())
                n_pairs += 1
                idx = next((i for i in range(min(len(ss), len(fs))) if ss[i].action != fs[i].action), None)
                if idx is None:
                    no_div += 1; continue
                st = fs[idx]
                leaf = model.situation(st.history).id
                by_tier[tiers.get(leaf, "llm")] += 1
                a, b = ss[idx].action, fs[idx].action
                kind = ("tool-vs-message" if is_tool_action(a) != is_tool_action(b)
                        else "different-tool" if is_tool_action(a) else "message-vs-message")
                by_kind[kind] += 1
                pos.append(idx / max(1, len(fs)))
    tot = sum(by_tier.values())
    rows.append({"agent": agent, "domain": domain, "pairs": n_pairs, "no_divergence_in_actions": no_div,
                 "first_divergence_by_candidate_tier": {k: round(v / tot, 3) for k, v in by_tier.items()},
                 "first_divergence_kind": {k: round(v / tot, 3) for k, v in by_kind.items()},
                 "median_relative_position": round(sorted(pos)[len(pos) // 2], 2) if pos else None,
                 "tier_counts_over_situations": dict(Counter(tiers.values()))})
    print(json.dumps(rows[-1]))
(OUT / "diverge.json").write_text(json.dumps(rows, indent=1))
