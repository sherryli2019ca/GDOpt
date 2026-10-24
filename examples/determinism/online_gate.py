"""Online trigger rules from Jev confidence: per-step p < tau vs cumulative / leaky / reset / rate entropy gates.

Simulated on logged runs (zero API cost). For every rule, at a matched trigger rate, measure coverage of
(a) success/failure forks: first step where a successful and a failed trial of the same task take different actions,
    gate evaluated on the failed trial at that step;
(b) all trial-pair forks (any first action divergence).
Env: ANCHOR_DIR (default reports/anchor), OUT_DIR (default reports/determinism). Run from repo root.
"""
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import trajectory_risk as tr  # noqa: E402

OUT = Path(os.environ.get("OUT_DIR", "reports/determinism"))
EPS = 1e-3


def H(p):
    p = min(max(p, EPS), 1 - EPS)
    return -(p * math.log(p) + (1 - p) * math.log(1 - p)) / math.log(2)  # bits, binary proxy from p_max


def signals(steps):
    """Per-step signal values for each rule family (larger = more alarming)."""
    ps = [st["p"] if st["p"] is not None else 1.0 for st in steps]
    out = defaultdict(list)
    cum = leak5 = leak7 = reset = 0.0
    for t, p in enumerate(ps):
        h = H(p)
        cum += h
        leak5 = 0.5 * leak5 + h
        leak7 = 0.7 * leak7 + h
        reset = 0.0 if p >= 0.95 else reset + h
        prev_cum = cum - h
        out["step_1-p"].append(1 - p)
        out["cum_entropy"].append(cum)
        out["leaky_0.5"].append(leak5)
        out["leaky_0.7"].append(leak7)
        out["reset_on_p>=0.95"].append(reset)
        out["entropy_rate"].append(cum / (t + 1))
        # compound rule: only uncertain steps, ranked by how shaky the context already is
        out["p<0.8_and_prior_cum"].append(prev_cum + 10 if p < 0.8 else prev_cum * 0.0 + (1 - p))
    return out


def main():
    data = {r: tr.load(r) for r in tr.RUNS_WITH_JEV}
    rules = None
    all_vals = defaultdict(list)
    sig = {}
    for r, eps in data.items():
        for i, e in enumerate(eps):
            s = signals(e["steps"]); sig[(r, i)] = s
            rules = list(s)
            for k, v in s.items():
                all_vals[k] += v
    # fork events
    sf, anyf = [], []
    for r, eps in data.items():
        by = defaultdict(list)
        for i, e in enumerate(eps):
            by[e["task"]].append(i)
        for idx in by.values():
            for a in range(len(idx)):
                for b in range(a + 1, len(idx)):
                    i, j = idx[a], idx[b]
                    A, B = eps[i]["steps"], eps[j]["steps"]
                    t = next((t for t in range(min(len(A), len(B))) if A[t]["act"] != B[t]["act"]), None)
                    if t is None:
                        continue
                    anyf.append([(r, i, t), (r, j, t)])
                    if eps[i]["success"] != eps[j]["success"]:
                        f = i if not eps[i]["success"] else j
                        sf.append((r, f, t))
    report = {"steps": len(all_vals["step_1-p"]), "succ_fail_forks": len(sf), "all_forks": len(anyf), "rules": {}}
    for k in rules:
        vals = sorted(all_vals[k], reverse=True)
        res = {}
        for rate in (0.2, 0.35, 0.5):
            thr = vals[int(rate * len(vals)) - 1]
            fired = lambda key: sig[(key[0], key[1])][k][key[2]] >= thr
            cov_sf = sum(fired(x) for x in sf) / len(sf)
            cov_any = sum(any(fired(y) for y in x) for x in anyf) / len(anyf)
            # overlap with the per-step p<0.8 gate
            both = tot = 0
            for (r, i), s in sig.items():
                for t, v in enumerate(s[k]):
                    if v >= thr:
                        tot += 1; both += s["step_1-p"][t] > 0.2
            res[f"{int(rate*100)}%"] = {"threshold": round(thr, 3), "succ_fail_fork_coverage": round(cov_sf, 3),
                                        "any_fork_coverage": round(cov_any, 3), "share_of_fired_with_p<0.8": round(both / tot, 3)}
        report["rules"][k] = res
        print(k, {r_: (v["succ_fail_fork_coverage"], v["any_fork_coverage"], v["share_of_fired_with_p<0.8"]) for r_, v in res.items()})
    # natural p<0.8 gate
    rate = sum(v > 0.2 for v in all_vals["step_1-p"]) / len(all_vals["step_1-p"])
    report["p<0.8_trigger_rate"] = round(rate, 3)
    print("p<0.8 rate", round(rate, 3), "sf forks", len(sf), "any forks", len(anyf))
    (OUT / "online_gate.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
