"""Jev reproducibility: repeat identical decision calls, compare the returned probability vectors.

Reads 5 states from the shadow caches in reports/shadow-desc/, calls Jev 8 times sequentially and 8 times
concurrently per state, and reports distinct vectors / max abs diff / argmax changes. Budget-capped (default $0.012).
Needs OPENROUTER_API_KEY in the environment (never written to disk). Run from the repo root with PYTHONPATH=src:

    OPENROUTER_API_KEY=... PYTHONPATH=src python examples/determinism/jev_reproducibility.py

Output: $OUT_DIR/jev_reproducibility.json (default reports/determinism/).
"""
import os
import json, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from gdopt.decision import OpenRouterJev

OUT = Path(os.environ.get("OUT_DIR", "reports/determinism"))
BUDGET = float(os.environ.get("JEV_BUDGET_USD", "0.012"))
N_SEQ, N_PAR = 8, 8

def load(dom):
    f = f"reports/shadow-desc/gpt-4.1-2025-04-14_{dom}_default_gpt-4.1-2025-04-14_4trials.shadow-cache.json"
    return json.load(open(f))

def stats(v):
    p = sorted(v["probabilities"].values(), reverse=True)
    return p[0], p[0] - p[1]

def pick(d, cond):
    for k, v in d.items():
        pm, gap = stats(v)
        if cond(pm, gap):
            return k, v
    raise SystemExit("no state matches")

air, tel = load("airline"), load("telecom")
cases = [
    ("airline/p_max=1.0", *pick(air, lambda pm, g: pm >= 0.995)),
    ("airline/p_max~0.9", *pick(air, lambda pm, g: 0.88 <= pm < 0.92)),
    ("airline/top2gap<=0.05", *pick(air, lambda pm, g: g <= 0.05)),
    ("telecom/top2gap<=0.05", *pick(tel, lambda pm, g: g <= 0.05)),
    ("telecom/p_max~0.6", *pick(tel, lambda pm, g: 0.5 <= pm < 0.7)),
]
jev = OpenRouterJev()
spent = 0.0
results = []
for label, key, cached in cases:
    kind, instructions, options, state = json.loads(key)
    assert kind == "choice"
    def call(_):
        t = time.time(); r = jev.choice(instructions, options, state)
        return {"probabilities": dict(r.probabilities), "cost": getattr(r, "cost", None), "latency_s": round(time.time() - t, 3)}
    runs = []
    for i in range(N_SEQ):
        runs.append(call(i)); spent += runs[-1]["cost"] or 0
        if spent > BUDGET: break
    if spent <= BUDGET:
        with ThreadPoolExecutor(max_workers=N_PAR) as ex:
            par = list(ex.map(call, range(N_PAR)))
        runs += par; spent += sum(r["cost"] or 0 for r in par)
    vecs = [tuple(sorted(r["probabilities"].items())) for r in runs]
    distinct = len(set(vecs))
    opts = list(runs[0]["probabilities"].keys())
    maxdiff = max(abs(a["probabilities"][o] - b["probabilities"][o]) for a in runs for b in runs for o in opts)
    argmax = {max(r["probabilities"], key=r["probabilities"].get) for r in runs}
    pmax = [max(r["probabilities"].values()) for r in runs]
    cached_vec = tuple(sorted(cached["probabilities"].items()))
    results.append({"case": label, "n_calls": len(runs), "distinct_vectors": distinct, "max_abs_diff": round(maxdiff, 4),
                    "argmax_set": sorted(argmax), "p_max_min": min(pmax), "p_max_max": max(pmax),
                    "same_as_yesterday_cache": cached_vec == vecs[0], "cached_p_max": cached["probabilities"][max(cached["probabilities"], key=cached["probabilities"].get)],
                    "latency_s_median": sorted(r["latency_s"] for r in runs)[len(runs)//2],
                    "cost_total": round(sum(r["cost"] or 0 for r in runs), 5),
                    "vectors": [dict(v) for v in sorted(set(vecs))]})
    print(json.dumps({k: v for k, v in results[-1].items() if k != "vectors"}, ensure_ascii=False))
    if spent > BUDGET:
        print("budget reached", spent); break
print("TOTAL SPENT", round(spent, 5))
(OUT / "jev_reproducibility.json").write_text(json.dumps({"spent_usd": round(spent, 5), "cases": results}, indent=1, ensure_ascii=False))
