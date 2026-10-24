"""Trajectory-level stability risk from the decision model's per-step confidence.

For every logged anchor run that queried Jev at each agent step (veto, hint, deliberate, reasoner), turn the sequence
of p_max values of one episode into a scalar risk score, aggregate over the 4 trials of a task, and ask whether the
score predicts (a) failure of that episode, (b) whether the task is flaky (some but not all trials pass),
(c) behavioural instability (the 4 trials take different action sequences), and (d) cross-run: whether a risk score
computed in one run predicts flakiness of the same task in a *different* run (incl. the plain baseline, which has no
Jev log). Steps-per-episode is reported as the length-only control.

Zero API cost: reads reports/anchor/*/results.json only.
Env: ANCHOR_DIR (default reports/anchor), OUT_DIR (default reports/determinism).
"""
import json
import math
import os
import random
from collections import defaultdict
from pathlib import Path

ANCHOR = Path(os.environ.get("ANCHOR_DIR", "reports/anchor"))
OUT = Path(os.environ.get("OUT_DIR", "reports/determinism"))
RUNS_WITH_JEV = ["veto", "hint", "deliberate", "reasoner"]
ALL_RUNS = ["none", "veto", "hint", "checklist", "deliberate", "reasoner", "deliberate_all"]
EPS = 1e-3


def action(m):
    tc = m.get("tool_calls")
    return "tool:" + tc[0]["name"] if tc else "message"


def load(run):
    d = json.load(open(ANCHOR / f"airline-{run}" / "results.json"))
    eps = []
    for s in d["simulations"]:
        steps = []
        for m in s["messages"]:
            if m.get("role") != "assistant":
                continue
            g = (m.get("raw_data") or {}).get("gdopt")
            if not g:
                continue  # greeting
            a = g.get("anchor", {})
            steps.append({"p": a.get("jev_p"), "top": a.get("jev_top"), "act": action(m)})
        r = (s.get("reward_info") or {}).get("reward") or 0.0
        eps.append({"task": str(s["task_id"]), "trial": s["trial"], "success": r >= 0.999, "steps": steps})
    return eps


# ---------------------------------------------------------------- per-episode scores
def scores(ep, kappa=1.0):
    ps = [st["p"] for st in ep["steps"] if st["p"] is not None]
    if not ps:
        return None
    u = [1 - p for p in ps]
    surpr = [-math.log(max(p, EPS)) for p in ps]
    ent2 = [-(p * math.log(max(p, EPS)) + (1 - p) * math.log(max(1 - p, EPS))) for p in ps]  # binary-entropy proxy
    return {
        "n_steps": len(ps),
        "sum_surprisal": sum(surpr),                       # -log prod p_t  (path-likelihood under Jev)
        "mean_surprisal": sum(surpr) / len(ps),
        "sum_uncertainty": sum(u),                          # expected # of "non-modal" steps
        "n_low_0.8": sum(p < 0.8 for p in ps),
        "n_low_0.6": sum(p < 0.6 for p in ps),
        "frac_low_0.8": sum(p < 0.8 for p in ps) / len(ps),
        "min_p": -min(ps),                                 # sign so that larger = riskier
        "sum_entropy": sum(ent2),
        "branch_prob": 1 - math.prod(1 - kappa * x for x in u),   # P(at least one fork) under independent forks
        "first_half_low": sum(p < 0.8 for p in ps[: max(1, len(ps) // 2)]),
        "disagree_jev": sum(st["top"] is not None and st["top"] != st["act"] for st in ep["steps"]),
    }


# ---------------------------------------------------------------- metrics
def auc(pos, neg):
    if not pos or not neg:
        return float("nan")
    w = 0.0
    for a in pos:
        for b in neg:
            w += 1.0 if a > b else 0.5 if a == b else 0.0
    return w / (len(pos) * len(neg))


def boot_auc(pairs, n=2000, seed=0):
    """pairs: list of (score, label) at task level; bootstrap over items."""
    rng = random.Random(seed)
    vals = []
    for _ in range(n):
        smp = [pairs[rng.randrange(len(pairs))] for _ in pairs]
        pos = [s for s, y in smp if y]; neg = [s for s, y in smp if not y]
        if pos and neg:
            vals.append(auc(pos, neg))
    vals.sort()
    return round(vals[int(0.025 * len(vals))], 3), round(vals[int(0.975 * len(vals))], 3)


def spearman(x, y):
    def rank(v):
        o = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0] * len(v); i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[o[j + 1]] == v[o[i]]:
                j += 1
            for k in range(i, j + 1):
                r[o[k]] = (i + j) / 2
            i = j + 1
        return r
    rx, ry = rank(x), rank(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    c = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    return c / math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry) or 1)


def seq(ep):
    return tuple(st["act"] for st in ep["steps"] if st["act"] != "message")  # tool sequence


def task_table(eps):
    by = defaultdict(list)
    for e in eps:
        by[e["task"]].append(e)
    T = {}
    for k, v in by.items():
        c = sum(e["success"] for e in v)
        sc = [scores(e) for e in v]
        sc = [s for s in sc if s]
        agg = {f: sum(s[f] for s in sc) / len(sc) for f in sc[0]} if sc else {}
        seqs = [seq(e) for e in v]
        pairs = [(i, j) for i in range(len(seqs)) for j in range(i + 1, len(seqs))]
        diff = sum(seqs[i] != seqs[j] for i, j in pairs) / max(1, len(pairs))
        T[k] = {"c": c, "n": len(v), "flaky": 0 < c < len(v), "always_fail": c == 0, "seq_diff": diff, **agg}
    return T


FEATURES = ["n_steps", "sum_surprisal", "mean_surprisal", "sum_uncertainty", "n_low_0.8", "n_low_0.6",
            "frac_low_0.8", "min_p", "sum_entropy", "branch_prob", "first_half_low", "disagree_jev"]


def evaluate(run, eps):
    out = {"run": run, "episodes": len(eps)}
    # (a) episode failure
    ep_sc = [(scores(e), e["success"]) for e in eps]
    ep_sc = [(s, y) for s, y in ep_sc if s]
    out["episode_failure_auc"] = {f: round(auc([s[f] for s, y in ep_sc if not y], [s[f] for s, y in ep_sc if y]), 3)
                                  for f in FEATURES}
    # within-task: among tasks with mixed outcomes, is the failed trial the riskier one?
    by = defaultdict(list)
    for s, y in ep_sc:
        pass
    by = defaultdict(list)
    for e in eps:
        s = scores(e)
        if s:
            by[e["task"]].append((s, e["success"]))
    wt = {}
    for f in FEATURES:
        w = n = 0.0
        for v in by.values():
            for a, ya in v:
                for b, yb in v:
                    if not ya and yb:
                        n += 1; w += 1 if a[f] > b[f] else 0.5 if a[f] == b[f] else 0
        wt[f] = round(w / n, 3) if n else None
    out["within_task_failure_auc"] = wt
    out["within_task_pairs"] = int(sum(1 for v in by.values() for a, ya in v for b, yb in v if not ya and yb))
    # (b) task flaky, (c) seq instability
    T = task_table(eps)
    rows = [t for t in T.values() if "n_steps" in t]
    out["tasks"] = len(rows); out["flaky_tasks"] = sum(t["flaky"] for t in rows)
    out["flaky_auc"] = {}
    out["unstable_auc"] = {}  # not-always-pass vs always-pass (pass^4 failure)
    out["seq_diff_spearman"] = {}
    for f in FEATURES:
        pairs = [(t[f], t["flaky"]) for t in rows]
        out["flaky_auc"][f] = (round(auc([s for s, y in pairs if y], [s for s, y in pairs if not y]), 3),) + boot_auc(pairs)
        pairs4 = [(t[f], t["c"] < t["n"]) for t in rows]
        out["unstable_auc"][f] = round(auc([s for s, y in pairs4 if y], [s for s, y in pairs4 if not y]), 3)
        out["seq_diff_spearman"][f] = round(spearman([t[f] for t in rows], [t["seq_diff"] for t in rows]), 3)
    return out, T


def risk_bins(T, f="sum_surprisal", k=3):
    rows = sorted([t for t in T.values() if f in t], key=lambda t: t[f])
    n = len(rows); res = []
    for i in range(k):
        b = rows[i * n // k:(i + 1) * n // k]
        # pass^k from per-task counts: C(c,k)/C(n,k)
        def passk(kk):
            return sum(math.comb(t["c"], kk) / math.comb(t["n"], kk) for t in b) / len(b)
        res.append({"bin": i + 1, "tasks": len(b), "score_range": [round(b[0][f], 2), round(b[-1][f], 2)],
                    "pass^1": round(100 * passk(1), 1), "pass^4": round(100 * passk(4), 1),
                    "gap": round(100 * (passk(1) - passk(4)), 1),
                    "flaky": round(100 * sum(t["flaky"] for t in b) / len(b), 1)})
    return res


def prefix_scores(ep, k):
    return scores({**ep, "steps": ep["steps"][:k]})


def length_controlled(data, tables):
    """Analyses where episode length cannot carry the signal."""
    out = {}
    # (1) ex-ante prefix: only the first k agent steps of every trial (all episodes have >= k steps or are padded short)
    pre = {}
    for k in (2, 3, 4, 6):
        per = {}
        for r in RUNS_WITH_JEV:
            by = defaultdict(list)
            for e in data[r]:
                s = prefix_scores(e, k)
                if s:
                    by[e["task"]].append((s, e["success"]))
            T = {t: {"flaky": 0 < sum(y for _, y in v) < len(v),
                     **{f: sum(s[f] for s, _ in v) / len(v) for f in ("sum_surprisal", "n_low_0.8", "min_p")}}
                 for t, v in by.items()}
            per[r] = {f: round(auc([t[f] for t in T.values() if t["flaky"]], [t[f] for t in T.values() if not t["flaky"]]), 3)
                      for f in ("sum_surprisal", "n_low_0.8", "min_p")}
        pre[k] = per
        pre[k]["mean_over_runs"] = {f: round(sum(per[r][f] for r in RUNS_WITH_JEV) / len(RUNS_WITH_JEV), 3)
                                    for f in ("sum_surprisal", "n_low_0.8", "min_p")}
    out["prefix_flaky_auc"] = pre
    # (2) within-task, pooled over the 4 runs: failed vs succeeded trial of the same task; task-bootstrap CI
    groups = []
    for r in RUNS_WITH_JEV:
        by = defaultdict(list)
        for e in data[r]:
            s = scores(e)
            if s:
                by[e["task"]].append((s, e["success"]))
        groups += [v for v in by.values() if 0 < sum(y for _, y in v) < len(v)]
    feats = ["n_steps", "sum_surprisal", "mean_surprisal", "n_low_0.8", "frac_low_0.8", "min_p", "sum_uncertainty"]

    def wauc(gs, f):
        w = n = 0.0
        for v in gs:
            for a, ya in v:
                for b, yb in v:
                    if not ya and yb:
                        n += 1; w += 1 if a[f] > b[f] else 0.5 if a[f] == b[f] else 0
        return w / n if n else float("nan")
    rng = random.Random(1)
    wt = {}
    for f in feats:
        bs = sorted(wauc([groups[rng.randrange(len(groups))] for _ in groups], f) for _ in range(2000))
        wt[f] = [round(wauc(groups, f), 3), round(bs[50], 3), round(bs[1949], 3)]
    out["within_task_pooled"] = {"groups": len(groups), "auc_ci": wt}
    # (3) online hazard: at step t, among trials still running, cumulative surprisal of the prefix vs final failure
    hz = {}
    for t in (3, 5, 8, 12):
        pos, neg = [], []
        for r in RUNS_WITH_JEV:
            for e in data[r]:
                ps = [st["p"] for st in e["steps"][:t] if st["p"] is not None]
                if len(e["steps"]) <= t:
                    continue
                v = sum(-math.log(max(p, EPS)) for p in ps)
                (neg if e["success"] else pos).append(v)
        hz[t] = {"alive": len(pos) + len(neg), "failed": len(pos), "auc_cum_surprisal": round(auc(pos, neg), 3)}
    out["online_hazard"] = hz
    # (4) task level: leave-one-out logistic, length only vs length + Jev
    import numpy as np

    def loo(X, y):
        X = np.c_[np.ones(len(X)), X]; pr = []
        for i in range(len(y)):
            m = np.ones(len(y), bool); m[i] = False
            w = np.zeros(X.shape[1])
            for _ in range(400):
                z = 1 / (1 + np.exp(-X[m] @ w)); w -= 0.5 * (X[m].T @ (z - y[m]) / m.sum() + 0.01 * w)
            pr.append(float(1 / (1 + np.exp(-X[i] @ w))))
        return auc([p for p, l in zip(pr, y) if l], [p for p, l in zip(pr, y) if not l])
    lg = {}
    for r in RUNS_WITH_JEV:
        T = [t for t in tables[r].values() if "n_steps" in t]
        y = np.array([float(t["flaky"]) for t in T])
        z = lambda f: (lambda a: (a - a.mean()) / (a.std() or 1))(np.array([t[f] for t in T], float))
        L = z("n_steps"); S = z("mean_surprisal"); N = z("frac_low_0.8"); M = z("min_p")
        lg[r] = {"length": round(loo(L[:, None], y), 3), "length+mean_surprisal": round(loo(np.c_[L, S], y), 3),
                 "length+frac_low+min_p": round(loo(np.c_[L, N, M], y), 3), "jev_only(mean,frac,min)": round(loo(np.c_[S, N, M], y), 3)}
    out["loo_logistic_flaky_auc"] = lg
    return out


HAZARD_BINS = [0, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.01]


def step_hazard(data):
    """Per-step fork rate as a function of Jev confidence. For every pair of trials of the same task, walk the aligned
    steps while both took the same actions; at each step record min(p_i, p_j) and whether the two actions differ there.
    Split by whether the pair ends with different outcomes (one success, one failure)."""
    def b(p):
        return next(i for i in range(len(HAZARD_BINS) - 1) if HAZARD_BINS[i] <= p < HAZARD_BINS[i + 1])
    H = defaultdict(lambda: {"all": [0, 0], "mixed": [0, 0], "same": [0, 0]})
    pair_rows = []
    for r in RUNS_WITH_JEV:
        by = defaultdict(list)
        for e in data[r]:
            by[e["task"]].append(e)
        for v in by.values():
            for i in range(len(v)):
                for j in range(i + 1, len(v)):
                    a, c = v[i]["steps"], v[j]["steps"]
                    mixed = v[i]["success"] != v[j]["success"]
                    div = False
                    for t in range(min(len(a), len(c))):
                        if a[t]["p"] is None or c[t]["p"] is None:
                            continue
                        k = b(min(a[t]["p"], c[t]["p"])); d = a[t]["act"] != c[t]["act"]
                        for key in ("all", "mixed" if mixed else "same"):
                            H[k][key][0] += 1; H[k][key][1] += d
                        if d:
                            div = True; break
                    pair_rows.append((a, div, mixed))
    table = []
    h = {}
    for k in range(len(HAZARD_BINS) - 1):
        row = {"p_range": [HAZARD_BINS[k], min(1.0, HAZARD_BINS[k + 1])]}
        for key in ("all", "mixed", "same"):
            n, d = H[k][key]
            row[key] = {"steps": n, "forks": d, "hazard": round(d / n, 3) if n else None}
        h[k] = H[k]["all"][1] / max(1, H[k]["all"][0])
        table.append(row)
    # trajectory-level use of the calibrated hazard: R = sum_t -log(1 - h(p_t)) on ONE trial's sequence
    def R(steps):
        return sum(-math.log(1 - h[b(st["p"])] + 1e-9) for st in steps if st["p"] is not None)
    pos = [R(a) for a, d, _ in pair_rows if d]; neg = [R(a) for a, d, _ in pair_rows if not d]
    lp = [len(a) for a, d, _ in pair_rows if d]; ln = [len(a) for a, d, _ in pair_rows if not d]
    p4 = [R(a[:4]) for a, d, _ in pair_rows if d]; n4 = [R(a[:4]) for a, d, _ in pair_rows if not d]
    return {"table": table, "pairs": len(pair_rows), "pairs_diverged": len(pos),
            "pair_divergence_auc": {"hazard_risk_full": round(auc(pos, neg), 3), "length_only": round(auc(lp, ln), 3),
                                    "hazard_risk_first4": round(auc(p4, n4), 3)}}


def poisson_fork(tables):
    """P(task flaky) = 1 - exp(-kappa * sum_t (1 - p_t)): each low-confidence step is an independent fork point."""
    res = {}
    for r, T in tables.items():
        rows = [t for t in T.values() if "sum_uncertainty" in t]
        best = None
        for i in range(1, 400):
            k = i / 200
            ll = 0.0
            for t in rows:
                q = min(1 - 1e-6, max(1e-6, 1 - math.exp(-k * t["sum_uncertainty"])))
                ll += math.log(q) if t["flaky"] else math.log(1 - q)
            if best is None or ll > best[1]:
                best = (k, ll)
        k = best[0]
        rows.sort(key=lambda t: t["sum_uncertainty"])
        cal = []
        for b in range(3):
            g = rows[b * len(rows) // 3:(b + 1) * len(rows) // 3]
            cal.append({"pred_flaky": round(100 * sum(1 - math.exp(-k * t["sum_uncertainty"]) for t in g) / len(g), 1),
                        "obs_flaky": round(100 * sum(t["flaky"] for t in g) / len(g), 1)})
        res[r] = {"kappa": k, "calibration_terciles": cal}
    return res


def main():
    data = {r: load(r) for r in ALL_RUNS if (ANCHOR / f"airline-{r}" / "results.json").exists()}
    report = {"per_run": [], "cross_run": {}, "risk_bins": {}, "pooled": {}}
    tables = {}
    for r in RUNS_WITH_JEV:
        if r not in data:
            continue
        o, T = evaluate(r, data[r]); tables[r] = T
        report["per_run"].append(o)
        report["risk_bins"][r] = risk_bins(T)
        print(r, "flaky AUC", {f: o["flaky_auc"][f][0] for f in FEATURES})
    # pooled across the four Jev-logged runs: task-level score = mean over all 16 episodes, label = flaky in each run
    # (d) cross-run: score from run A (task means) predicts outcome counts in run B
    outcome = {r: task_table(eps) for r, eps in data.items()}
    for f in ["n_steps", "sum_surprisal", "mean_surprisal", "n_low_0.8", "frac_low_0.8", "sum_uncertainty", "min_p"]:
        cr = {}
        for a in tables:
            for b in outcome:
                if a == b:
                    continue
                ks = [k for k in tables[a] if k in outcome[b] and f in tables[a][k]]
                pairs = [(tables[a][k][f], outcome[b][k]["flaky"]) for k in ks]
                cr[f"{a}->{b}"] = round(auc([s for s, y in pairs if y], [s for s, y in pairs if not y]), 3)
        vals = [v for v in cr.values() if not math.isnan(v)]
        report["cross_run"][f] = {"mean_auc": round(sum(vals) / len(vals), 3), "pairs": cr}
        print("cross", f, report["cross_run"][f]["mean_auc"])
    # pooled task score: mean over the 4 Jev runs; label: flaky count across all 7 runs (0..7)
    pooled = {}
    for f in ["n_steps", "sum_surprisal", "mean_surprisal", "n_low_0.8", "frac_low_0.8", "sum_uncertainty", "min_p"]:
        ks = [k for k in tables["veto"] if all(k in tables[r] and f in tables[r][k] for r in tables)]
        x = [sum(tables[r][k][f] for r in tables) / len(tables) for k in ks]
        y = [sum(outcome[r][k]["flaky"] for r in outcome if k in outcome[r]) for k in ks]
        z = [sum(outcome[r][k]["c"] for r in outcome if k in outcome[r]) for k in ks]
        pooled[f] = {"spearman_vs_times_flaky": round(spearman(x, y), 3),
                     "spearman_vs_total_successes": round(spearman(x, z), 3)}
    report["pooled"] = pooled
    print(json.dumps(pooled, indent=1))
    report["length_controlled"] = length_controlled(data, tables)
    report["poisson_fork_model"] = poisson_fork(tables)
    report["step_hazard"] = step_hazard(data)
    for row in report["step_hazard"]["table"]:
        print("hazard", row["p_range"], row["all"], "mixed", row["mixed"]["hazard"], "same", row["same"]["hazard"])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "trajectory_risk.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
