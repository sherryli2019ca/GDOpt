"""Retail validation: baseline vs deliberate+reasoner (Jev p<0.8), 114 tasks x 4, paired bootstrap. Run from repo root."""
import json, math, random
from collections import Counter, defaultdict
A = "reports/anchor/"


def load(r):
    d, sims = defaultdict(list), json.load(open(A + r + "/results.json"))["simulations"]
    assert len({(s["task_id"], s["trial"]) for s in sims}) == len(sims)
    assert not any(s.get("termination_reason") == "infrastructure_error" for s in sims)
    for s in sims:
        d[str(s["task_id"])].append(((s.get("reward_info") or {}).get("reward") or 0) >= 0.999)
    return d, sims


def ph(v, k):
    c = sum(v)
    return math.comb(c, k) / math.comb(len(v), k) if c >= k else 0


def m(d, ts, k):
    return 100 * sum(ph(d[t], k) for t in ts) / len(ts)


R, S = {}, {}
for k, v in dict(base="retail-none", dr="retail-deliberate_reasoner", cons="retail-deliberate_reasoner_consistency").items():
    R[k], S[k] = load(v)
ts = sorted(R["base"], key=int)
out = {}
for k, d in R.items():
    out[k] = {f"pass^{j}": round(m(d, ts, j), 1) for j in (1, 2, 3, 4)}
    out[k]["flaky"] = round(100 * sum(0 < sum(d[t]) < len(d[t]) for t in ts) / len(ts), 1)
    out[k]["always_fail"] = round(100 * sum(sum(d[t]) == 0 for t in ts) / len(ts), 1)
    gens = Counter()
    for s in S[k]:
        for msg in s["messages"]:
            if msg.get("role") == "assistant":
                a = ((msg.get("raw_data") or {}).get("gdopt") or {}).get("anchor") or {}
                gens["steps"] += 1
                gens["reasoner"] += bool(a.get("reasoner") or a.get("generator") == "reasoner")
    out[k]["steps"] = gens["steps"]
    print(k, out[k])
rate = lambda d, t: sum(d[t]) / len(d[t])
for new, ref in (("dr", "base"), ("cons", "base"), ("cons", "dr")):
    random.seed(0)
    tag = "" if (new, ref) == ("dr", "base") else f"{new}_vs_{ref}_"
    for j in (1, 2, 4):
        obs = m(R[new], ts, j) - m(R[ref], ts, j)
        bs = sorted(m(R[new], s, j) - m(R[ref], s, j) for s in ([random.choice(ts) for _ in ts] for _ in range(5000)))
        out[f"{tag}delta_pass^{j}"] = dict(delta=round(obs, 1), ci=[round(bs[125], 1), round(bs[4875], 1)], P=round(sum(b > 0 for b in bs) / len(bs), 2))
        print(new, ref, j, out[f"{tag}delta_pass^{j}"])
    out[f"{tag}tasks_better_worse"] = [sum(rate(R[new], t) > rate(R[ref], t) for t in ts), sum(rate(R[new], t) < rate(R[ref], t) for t in ts)]
    print(new, ref, "tasks better/worse", out[f"{tag}tasks_better_worse"])
json.dump(out, open("reports/anchor/retail_compare.json", "w"), indent=1)
