"""E2 of the solidification plan: counterfactual replay at the steps where a certified policy rule would have fired.

For every failed logged episode in which a certified rule fires (``reports/determinism/clause_audit.json``), cut the
conversation right before the first offending assistant message, and let τ²-bench continue from that prefix
(``Task.initial_state.message_history``: the environment re-executes the logged tool calls, the user simulator
resumes) with two agents: the plain ``llm_agent`` (control) and ``RuleGuardedLLMAgent`` (rules enforced).  Compare
the success rates of the continuations.  Jev is not used: the rules check write calls only.

    python examples/tau2_rule_replay.py --rule-trials 4 --control-trials 4 --out reports/rules/airline-replay

τ²-bench on PYTHONPATH, DEEPSEEK_API_KEY for the LLM.
"""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tau2_replay import openrouter_prices, patch_tau2_usage, recost, register_price  # noqa: E402

ROLE_CLS = {}


def to_messages(raw: list[dict]):
    from tau2.data_model.message import AssistantMessage, ToolMessage, UserMessage  # type: ignore[import-not-found]
    cls = {"assistant": AssistantMessage, "user": UserMessage, "tool": ToolMessage}
    out = []
    for m in raw:
        m = deepcopy(m)
        m.pop("raw_data", None)
        out.append(cls[m["role"]].model_validate(m))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", default="reports/determinism/clause_audit.json")
    ap.add_argument("--anchor-dir", default="reports/anchor")
    ap.add_argument("--llm", default="deepseek/deepseek-chat")
    ap.add_argument("--rule-trials", type=int, default=4)
    ap.add_argument("--control-trials", type=int, default=4)
    ap.add_argument("--limit", type=int, default=None, help="only the first N flagged episodes (pilot)")
    ap.add_argument("--max-concurrency", type=int, default=6)
    ap.add_argument("--seed", type=int, default=400)
    ap.add_argument("--arms", default="rules,control")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    from tau2.data_model.semantic_communication import CommunicateScorer, CommunicateScoring  # type: ignore[import-not-found]
    from tau2.data_model.simulation import TextRunConfig  # type: ignore[import-not-found]
    from tau2.data_model.tasks import InitialState  # type: ignore[import-not-found]
    from tau2.registry import registry  # type: ignore[import-not-found]
    from tau2.runner.batch import run_tasks  # type: ignore[import-not-found]

    from gdopt.adapters.tau2_rules import CERTIFIED, register_rule_agent

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    prices = openrouter_prices(args.llm)
    register_price(args.llm, prices)
    patch_tau2_usage()

    audit = json.loads(Path(args.audit).read_text())
    flagged = [x for x in audit["flagged"] if not x["success"] and set(x["rules"]) & CERTIFIED]
    if args.limit:
        flagged = flagged[: args.limit]
    base_tasks = {str(t.id): t for t in registry.get_tasks_loader("airline")()}
    sims = {}
    for run in {x["run"] for x in flagged}:
        for s in json.load(open(Path(args.anchor_dir) / f"airline-{run}" / "results.json"))["simulations"]:
            sims[(run, str(s["task_id"]), s["trial"])] = s
    tasks, meta = [], {}
    for x in flagged:
        s = sims[(x["run"], x["task"], x["trial"])]
        prefix = s["messages"][: x["first_msg_index"]]
        t = base_tasks[x["task"]].model_copy(deep=True)
        t.id = f"{x['task']}__{x['run']}_{x['trial']}"
        t.initial_state = InitialState(initialization_data=None, initialization_actions=None, message_history=to_messages(prefix))
        tasks.append(t)
        meta[t.id] = {**x, "prefix_len": len(prefix)}
    (out / "replay_tasks.json").write_text(json.dumps(meta, indent=1))
    print(f"{len(tasks)} replay tasks from {len({x['task'] for x in flagged})} base tasks")

    agents = register_rule_agent("gdopt_rules")
    summary = {"tasks": len(tasks), "arms": {}}
    for arm in args.arms.split(","):
        agent = "gdopt_rules" if arm == "rules" else "llm_agent"
        trials = args.rule_trials if arm == "rules" else args.control_trials
        cfg = TextRunConfig(agent=agent, domain="airline", user="user_simulator", llm_agent=args.llm,
                            llm_args_agent={"temperature": 0.0}, llm_user=args.llm, llm_args_user={"temperature": 0.0},
                            num_trials=trials, max_concurrency=args.max_concurrency, seed=args.seed, log_level="ERROR",
                            auto_resume=True, communicate_scoring=CommunicateScoring(scorer=CommunicateScorer.SUBSTRING))
        path = out / f"{arm}.json"
        res = run_tasks(cfg, tasks, save_path=path, console_display=False)
        recost(path, {args.llm: prices}, prices)
        per = {}
        for sim in res.simulations:
            r = (sim.reward_info.reward if sim.reward_info else 0.0) or 0.0
            per.setdefault(sim.task_id, []).append(r >= 0.999)
        n = sum(len(v) for v in per.values())
        k = sum(sum(v) for v in per.values())
        summary["arms"][arm] = {"trials": trials, "runs": n, "successes": k, "success_rate": round(k / n, 3) if n else None,
                                "per_task": {t: sum(v) / len(v) for t, v in per.items()}}
        if arm == "rules":
            agg = {}
            for a in agents:
                for kk, vv in a.stats.items():
                    agg[kk] = agg.get(kk, 0) + vv
            summary["arms"][arm]["agent_stats"] = agg
        print(arm, summary["arms"][arm]["success_rate"], f"{k}/{n}")
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps({a: {k: v for k, v in s.items() if k != "per_task"} for a, s in summary["arms"].items()}, indent=1))


if __name__ == "__main__":
    main()
