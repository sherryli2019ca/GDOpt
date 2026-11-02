"""Full airline 50x4 with E4 + mined checks (3 fold-isolated sub-runs) vs E4 and baseline: pass^k, paired bootstrap.

Each fold's tasks ran only with mined checks from the other folds (`--mined-exclude-fold`), so no task is scored with a
check mined from its own failures.  Run from repo root; writes reports/rsi/full_compare.json.
"""
import json
import math
import random
from collections import Counter, defaultdict

A = "reports/anchor/airline-"


def load(runs):
    d = defaultdict(list)
    for r in runs:
        for s in json.load(open(A + r + "/results.json"))["simulations"]:
            d[str(s["task_id"])].append(((s.get("reward_info") or {}).get("reward") or 0) >= 0.999)
    return d


def ph(v, k):
    n, c = len(v), sum(v)
    return math.comb(c, k) / math.comb(n, k) if c >= k else 0


def m(d, ts, k):
    return 100 * sum(ph(d[t], k) for t in ts) / len(ts)


def mined_fires():
    fires, eps = Counter(), Counter()
    for k in range(3):
        for s in json.load(open(f"{A}e4_mined-fold{k}/results.json"))["simulations"]:
            ok = ((s.get("reward_info") or {}).get("reward") or 0) >= 0.999
            hit = False
            for msg in s["messages"]:
                c = (((msg.get("raw_data") or {}).get("gdopt") or {}).get("anchor") or {}).get("consistency") or {}
                names = [f for f in c.get("fired", []) if f.startswith("mined:")]
                for f in names:
                    fires[f] += 1
                hit = hit or bool(names)
            if hit:
                eps["success" if ok else "fail"] += 1
    return dict(fires), dict(eps)


def main():
    R = {"base": load(["none"]), "e4": load(["deliberate_reasoner_rules_consistency"]),
         "new": load([f"e4_mined-fold{k}" for k in range(3)])}
    ts = sorted(R["new"], key=int)
    out = {}
    for k, d in R.items():
        out[k] = {f"pass^{j}": round(m(d, ts, j), 1) for j in (1, 2, 3, 4)}
        out[k]["flaky"] = round(100 * sum(0 < sum(d[t]) < len(d[t]) for t in ts) / len(ts))
        out[k]["always_fail"] = round(100 * sum(sum(d[t]) == 0 for t in ts) / len(ts))
        print(k, out[k])
    random.seed(0)
    for ref in ("base", "e4"):
        for j in (1, 4):
            obs = m(R["new"], ts, j) - m(R[ref], ts, j)
            bs = []
            for _ in range(5000):
                s = [random.choice(ts) for _ in ts]
                bs.append(m(R["new"], s, j) - m(R[ref], s, j))
            bs.sort()
            out[f"new_vs_{ref}_pass^{j}"] = dict(delta=round(obs, 1), ci=[round(bs[125], 1), round(bs[4875], 1)],
                                                 P=round(sum(b > 0 for b in bs) / len(bs), 2))
            print(ref, j, out[f"new_vs_{ref}_pass^{j}"])
        rate = lambda d, t: sum(d[t]) / len(d[t])  # noqa: E731
        out[f"new_vs_{ref}_tasks"] = [sum(rate(R["new"], t) > rate(R[ref], t) for t in ts),
                                      sum(rate(R["new"], t) < rate(R[ref], t) for t in ts)]
        print(ref, "tasks better/worse", out[f"new_vs_{ref}_tasks"])
    out["mined_fires"], out["mined_fire_episodes"] = mined_fires()
    print(out["mined_fires"], out["mined_fire_episodes"])
    json.dump(out, open("reports/rsi/full_compare.json", "w"), indent=1)


if __name__ == "__main__":
    main()
