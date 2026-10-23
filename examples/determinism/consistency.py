"""Zero-cost determinism analysis: task-level and step-level consistency across trials.

Zero API cost: reads τ²-bench result files only.
Env: TAU2_BENCH_ROOT (clone of sierra-research/tau2-bench), OUT_DIR (where JSON goes).
Run with PYTHONPATH=src.
"""
import json, math, sys
from collections import Counter, defaultdict
from itertools import combinations
import os
from pathlib import Path

from gdopt.adapters.tau2 import load_results, results_info
from gdopt.profile import fit_situations, split_by_trial
from gdopt.situation import entropy
from gdopt.trace import all_steps

RES = Path(os.environ.get("TAU2_BENCH_ROOT", "../tau2-bench")) / Path("data/tau2/results/final")
OUT = Path(os.environ.get("OUT_DIR", "reports/determinism"))

def pass_hat_k(succ_by_task, k, n):
    vals = []
    for c in succ_by_task.values():
        vals.append(math.comb(c, k) / math.comb(n, k) if c >= k else 0.0)
    return sum(vals) / len(vals)

def tool_seq(traj):
    return tuple(tc.name for m in traj.messages if m.role == "assistant" for tc in m.tool_calls)

def first_action(traj):
    for m in traj.messages:
        if m.role == "assistant":
            return m.action
    return None

def analyze(path, train_trials=(0, 1)):
    trajs = load_results(path)
    info = results_info(path)
    by_task = defaultdict(list)
    for t in trajs:
        by_task[t.task_id].append(t)
    n_trials = max(len(v) for v in by_task.values())
    succ = {k: sum(1 for t in v if t.success) for k, v in by_task.items()}
    hist = Counter(succ.values())
    out = {
        "file": Path(path).name, "agent": info.get("agent_llm"), "user": info.get("user_llm"),
        "n_tasks": len(by_task), "n_trials": n_trials,
        "pass_hat": {k: round(pass_hat_k(succ, k, n_trials), 3) for k in range(1, n_trials + 1)},
        "success_hist": {c: hist.get(c, 0) for c in range(n_trials + 1)},
        "flaky_tasks": sum(1 for c in succ.values() if 0 < c < n_trials),
    }
    # step-level: first action and tool sequence agreement across trials of the same task
    fa_same = seq_same = 0
    jacc = []
    for k, v in by_task.items():
        fas = {first_action(t) for t in v}
        fa_same += (len(fas) == 1)
        seqs = {tool_seq(t) for t in v}
        seq_same += (len(seqs) == 1)
        sets = [set(tool_seq(t)) for t in v]
        for a, b in combinations(sets, 2):
            jacc.append(len(a & b) / len(a | b) if (a | b) else 1.0)
    out["first_action_unanimous"] = round(fa_same / len(by_task), 3)
    out["tool_sequence_unanimous"] = round(seq_same / len(by_task), 3)
    out["tool_set_jaccard_mean"] = round(sum(jacc) / len(jacc), 3) if jacc else None
    # situation-level: pooled entropy vs within-task entropy
    train, test = split_by_trial(trajs, train_trials)
    model = fit_situations(train)
    steps = all_steps(trajs)
    cell = defaultdict(Counter)   # (task, leaf) -> actions
    pooled = defaultdict(Counter)  # leaf -> actions
    for s in steps:
        task = s.trajectory_id.split(":")[0] if ":" in s.trajectory_id else next(t.task_id for t in trajs if t.id == s.trajectory_id)
        leaf = model.situation(s.history).id
        cell[(task, leaf)][s.action] += 1
        pooled[leaf][s.action] += 1
    N = sum(sum(c.values()) for c in pooled.values())
    H_pooled = sum(sum(c.values()) / N * entropy(c) for c in pooled.values())
    H_within = sum(sum(c.values()) / N * entropy(c) for c in cell.values())
    # unanimity of (task, situation) cells that have >=2 trials
    multi = [(k, c) for k, c in cell.items() if sum(c.values()) >= 2]
    unan = sum(1 for k, c in multi if len(c) == 1)
    # same but tool-call-only cells (what matters for DB state)
    out["H_action_given_situation_bits"] = round(H_pooled, 3)
    out["H_action_given_situation_and_task_bits"] = round(H_within, 3)
    out["flakiness_share_of_entropy"] = round(H_within / H_pooled, 3) if H_pooled else None
    out["cells_unanimous"] = round(unan / len(multi), 3) if multi else None
    out["n_cells"] = len(multi)
    out["n_situations"] = len(pooled)
    out["n_steps"] = N
    return out

def our_two_runs():
    a = load_results("/home/user/GDOpt/reports/replay/airline/baseline.json")
    b = load_results("/home/user/GDOpt/reports/replay/airline-baseline-rep2/baseline.json")
    A = {t.task_id: t for t in a}; B = {t.task_id: t for t in b}
    both = sum(1 for k in A if A[k].success and B[k].success)
    only_a = sum(1 for k in A if A[k].success and not B[k].success)
    only_b = sum(1 for k in A if not A[k].success and B[k].success)
    neither = len(A) - both - only_a - only_b
    fa = sum(1 for k in A if first_action(A[k]) == first_action(B[k]))
    seq = sum(1 for k in A if tool_seq(A[k]) == tool_seq(B[k]))
    jac = []
    for k in A:
        s1, s2 = set(tool_seq(A[k])), set(tool_seq(B[k]))
        jac.append(len(s1 & s2) / len(s1 | s2) if (s1 | s2) else 1.0)
    seeds = {(A[k].trial, A[k].meta.get("seed")) == (B[k].trial, B[k].meta.get("seed")) for k in A}
    return {"n": len(A), "both": both, "only_run1": only_a, "only_run2": only_b, "neither": neither,
            "pass1_run1": round((both + only_a) / len(A), 3), "pass1_run2": round((both + only_b) / len(A), 3),
            "pass_hat2_est": round(both / len(A), 3), "pass_at2_est": round((both + only_a + only_b) / len(A), 3),
            "first_action_same": round(fa / len(A), 3), "tool_sequence_same": round(seq / len(A), 3),
            "tool_set_jaccard_mean": round(sum(jac) / len(jac), 3), "same_seed": sorted(seeds)}

if __name__ == "__main__":
    res = {"our_two_runs_airline_deepseek": our_two_runs(), "shipped": []}
    print(json.dumps(res["our_two_runs_airline_deepseek"], indent=1))
    for f in sorted(RES.glob("*_default_gpt-4.1-2025-04-14_4trials.json")):
        if "telecom-workflow" in f.name:
            continue
        r = analyze(f)
        res["shipped"].append(r)
        print(json.dumps(r))
    (OUT / "determinism.json").write_text(json.dumps(res, indent=1))
