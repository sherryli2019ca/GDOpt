"""Compare multi-trial τ²-bench runs: pass^k, pass@k, flaky tasks, cost, anchor statistics.

    python examples/tau2_passk_report.py baseline=reports/anchor/airline-baseline hint=reports/anchor/airline-hint ...

Each argument is ``name=dir`` where ``dir`` holds ``results.json`` (and optionally ``summary.json``).
Writes ``REPORT.md`` next to the first run unless ``--out`` is given.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path


def pass_hat(succ: dict[str, int], k: int, n: int) -> float:
    return sum((math.comb(c, k) / math.comb(n, k)) if c >= k else 0.0 for c in succ.values()) / len(succ)


def pass_at(succ: dict[str, int], k: int, n: int) -> float:
    return sum(1 - (math.comb(n - c, k) / math.comb(n, k) if n - c >= k else 0.0) for c in succ.values()) / len(succ)


def load(path: Path) -> dict:
    d = json.loads((path / "results.json").read_text())
    sims = d["simulations"]
    by_task: dict[str, list] = defaultdict(list)
    for s in sims:
        by_task[str(s["task_id"])].append(s)
    n = max(len(v) for v in by_task.values())
    succ = {t: sum(1 for s in v if (s.get("reward_info") or {}).get("reward", 0) >= 1.0) for t, v in by_task.items()}
    steps = cost = jev = llm_calls = 0
    hints = vetoes = veto_changed = 0
    for s in sims:
        for m in s["messages"]:
            if m.get("role") != "assistant":
                continue
            steps += 1
            cost += float(m.get("cost") or 0.0)
            g = (m.get("raw_data") or {}).get("gdopt") or {}
            jev += float(g.get("decision_cost") or 0.0)
            llm_calls += int(g.get("llm_calls") or 1)
            a = g.get("anchor") or {}
            hints += 1 if a.get("hint") else 0
            vetoes += len(a.get("veto") or [])
            veto_changed += sum(1 for v in (a.get("veto") or []) if v.get("after") != v.get("proposed"))
    return {
        "n_tasks": len(by_task), "n_trials": n, "succ": succ,
        "pass_hat": {k: pass_hat(succ, k, n) for k in range(1, n + 1)},
        "pass_at": {k: pass_at(succ, k, n) for k in range(1, n + 1)},
        "flaky": sum(1 for c in succ.values() if 0 < c < n) / len(by_task),
        "always_fail": sum(1 for c in succ.values() if c == 0) / len(by_task),
        "steps_per_episode": steps / len(sims), "cost_per_episode": cost / len(sims), "jev_per_episode": jev / len(sims),
        "llm_calls_per_step": llm_calls / max(1, steps), "hints_per_step": hints / max(1, steps),
        "vetoes_per_step": vetoes / max(1, steps), "veto_changed_share": (veto_changed / vetoes) if vetoes else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+", help="name=dir")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    runs = {}
    for r in args.runs:
        name, d = r.split("=", 1)
        runs[name] = load(Path(d))
    first = next(iter(runs.values()))
    n = first["n_trials"]
    lines = ["# pass^k comparison", "", f"{first['n_tasks']} tasks × {n} trials per run.", "",
             "| run | " + " | ".join(f"pass^{k}" for k in range(1, n + 1)) + f" | pass@{n} | flaky | always fail | steps/ep | $/ep | Jev $/ep | LLM calls/step | hints/step | vetoes/step | veto changed |",
             "| --- | " + " | ".join("---" for _ in range(n)) + " | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for name, r in runs.items():
        vc = "–" if r["veto_changed_share"] is None else f"{r['veto_changed_share']:.0%}"
        lines.append(f"| {name} | " + " | ".join(f"{r['pass_hat'][k]:.1%}" for k in range(1, n + 1)) +
                     f" | {r['pass_at'][n]:.1%} | {r['flaky']:.0%} | {r['always_fail']:.0%} | {r['steps_per_episode']:.1f} | {r['cost_per_episode']:.4f} | {r['jev_per_episode']:.4f} | {r['llm_calls_per_step']:.2f} | {r['hints_per_step']:.0%} | {r['vetoes_per_step']:.1%} | {vc} |")
    # paired per-task view against the first run
    base_name, base = next(iter(runs.items()))
    lines += ["", f"## Per-task successes out of {n} (vs {base_name})", ""]
    for name, r in list(runs.items())[1:]:
        up = sum(1 for t in base["succ"] if r["succ"].get(t, 0) > base["succ"][t])
        down = sum(1 for t in base["succ"] if r["succ"].get(t, 0) < base["succ"][t])
        lines.append(f"- {name}: more successes on {up} tasks, fewer on {down}, same on {len(base['succ']) - up - down}")
    md = "\n".join(lines) + "\n"
    out = Path(args.out) if args.out else Path(args.runs[0].split("=", 1)[1]) / "REPORT.md"
    out.write_text(md)
    print(md)


if __name__ == "__main__":
    main()
