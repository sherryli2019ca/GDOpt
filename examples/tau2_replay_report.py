"""Turn a `tau2_replay.py` output directory into a Markdown report (paired per-task comparison)."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def load(path: Path) -> list[dict]:
    d = json.loads(path.read_text())
    return d["simulations"]


def per_task(sims: list[dict]) -> dict[tuple, dict]:
    out = {}
    for s in sims:
        steps = [m for m in s["messages"] if m["role"] == "assistant" and (m.get("usage") or (m.get("raw_data") or {}).get("gdopt"))]
        g = [(m.get("raw_data") or {}).get("gdopt") for m in steps]
        out[(s["task_id"], s.get("trial", 0))] = {
            "reward": float((s.get("reward_info") or {}).get("reward") or 0.0),
            "cost": sum(float(m.get("cost") or 0.0) for m in steps),
            "steps": len(steps),
            "llm_steps": sum(1 for x in g if x is None or x["llm_called"]),
            "decision_cost": sum(float(x["decision_cost"]) for x in g if x),
        }
    return out


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--title", default="τ²-bench replay")
    args = ap.parse_args()
    out = Path(args.out_dir)
    summ = {s["agent"]: s for s in json.loads((out / "summary.json").read_text())}
    base, tier = per_task(load(out / "baseline.json")), per_task(load(out / "tiered.json"))
    keys = sorted(set(base) & set(tier))
    b, t = summ["llm_agent"], summ["gdopt_tiered"]
    n = len(keys)
    both = sum(1 for k in keys if base[k]["reward"] >= 1 and tier[k]["reward"] >= 1)
    only_b = sum(1 for k in keys if base[k]["reward"] >= 1 and tier[k]["reward"] < 1)
    only_t = sum(1 for k in keys if base[k]["reward"] < 1 and tier[k]["reward"] >= 1)
    neither = n - both - only_b - only_t
    bc, tc = sum(base[k]["cost"] for k in keys), sum(tier[k]["cost"] + tier[k]["decision_cost"] for k in keys)
    lines = [f"# {args.title}", ""]
    lines += [f"{n} paired episodes (same tasks, same seed, same user simulator). Costs are OpenRouter prices for the agent LLM "
              f"plus Jev decision calls; the user simulator is not counted.", ""]
    lines += ["| agent | success | mean reward | agent cost / task | of which decision model | assistant steps | steps with LLM call | LLM-step share |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for name, s, pt in (("original (LLM every step)", b, base), ("tiered (code / Jev / LLM)", t, tier)):
        cost = sum(pt[k]["cost"] + pt[k]["decision_cost"] for k in keys)
        dc = sum(pt[k]["decision_cost"] for k in keys)
        lines.append(f"| {name} | {pct(s['success_rate'])} | {s['mean_reward']:.3f} | ${cost / n:.4f} | ${dc / n:.5f} | {s['steps']} | {s['llm_steps']} | {pct(s['llm_step_share'])} |")
    lines += ["", f"Cost change: **{pct(tc / bc - 1)}** ({'saving' if tc < bc else 'increase'}); success change: "
              f"**{100 * (t['success_rate'] - b['success_rate']):+.1f} points**.", ""]
    lines += ["## Paired outcome", "", "| both succeed | only original | only tiered | neither |", "| ---: | ---: | ---: | ---: |",
              f"| {both} | {only_b} | {only_t} | {neither} |", ""]
    lines += ["## Tiered agent: where each step was decided", "", "| tier that produced the step | steps |", "| --- | ---: |"]
    for k, v in sorted(t["tiers"].items()):
        lines.append(f"| {k} | {v} |")
    lines += ["", "| fallback reason (step still went to the LLM) | steps |", "| --- | ---: |"]
    for k, v in sorted(t["fallback_reasons"].items(), key=lambda kv: -kv[1]):
        lines.append(f"| {k} | {v} |")
    agree = t.get("in_loop_agreement", {})
    if agree:
        same, diff = agree.get("same", 0), agree.get("different", 0)
        lines += ["", f"In-loop shadow check on fallback steps (cheap tier proposed an action, LLM then decided): "
                  f"same action {same} / {same + diff} ({pct(same / max(1, same + diff))}).", "", "| disagreement (proposed -> LLM did) | steps |", "| --- | ---: |"]
        for k, v in sorted(((k, v) for k, v in agree.items() if k not in ("same", "different")), key=lambda kv: -kv[1]):
            lines.append(f"| {k} | {v} |")
    # per-situation usage
    leaf_stats: dict[int, Counter] = defaultdict(Counter)
    for s in load(out / "tiered.json"):
        for m in s["messages"]:
            g = (m.get("raw_data") or {}).get("gdopt")
            if g:
                leaf_stats[g["leaf_id"]]["steps"] += 1
                leaf_stats[g["leaf_id"]]["no_llm" if not g["llm_called"] else "llm"] += 1
                if g.get("fallback_reason", "") and "below threshold" in g["fallback_reason"]:
                    leaf_stats[g["leaf_id"]]["below"] += 1
    rules = {r["leaf_id"]: r for r in json.loads((out / "tier_table.json").read_text())}
    lines += ["", "## Per situation", "", "| leaf | tier | τ | rule | steps | skipped LLM | below threshold |", "| --- | --- | ---: | --- | ---: | ---: | ---: |"]
    for leaf, c in sorted(leaf_stats.items(), key=lambda kv: -kv[1]["steps"]):
        r = rules.get(leaf, {})
        lines.append(f"| {leaf} | {r.get('tier', '?')} | {r.get('tau', 0) or 0:.2f} | `{r.get('rule', '')}` | {c['steps']} | {c['no_llm']} | {c['below']} |")
    lines += ["", "## Per task", "", "| task | trial | original reward | tiered reward | original cost | tiered cost (incl. Jev) | tiered LLM steps / steps |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for k in keys:
        lines.append(f"| {k[0]} | {k[1]} | {base[k]['reward']:.1f} | {tier[k]['reward']:.1f} | ${base[k]['cost']:.4f} | ${tier[k]['cost'] + tier[k]['decision_cost']:.4f} | {tier[k]['llm_steps']} / {tier[k]['steps']} |")
    (out / "REPORT.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:14]))


if __name__ == "__main__":
    main()
