"""Run one τ²-bench agent configuration (plain LLM or decision-model-anchored LLM) for several trials.

Examples (from the repo root, τ²-bench on PYTHONPATH, OPENROUTER_API_KEY for Jev, DEEPSEEK_API_KEY for the LLM)::

    python examples/tau2_anchor_replay.py --modes none      --out reports/anchor/airline-baseline
    python examples/tau2_anchor_replay.py --modes hint      --out reports/anchor/airline-hint
    python examples/tau2_anchor_replay.py --modes veto      --out reports/anchor/airline-veto
    python examples/tau2_anchor_replay.py --modes checklist --out reports/anchor/airline-checklist

``--modes none`` runs τ²-bench's own ``llm_agent``; anything else runs ``AnchoredLLMAgent`` with those anchors
(comma-separated, e.g. ``hint,checklist``).  Then compare runs with ``examples/tau2_passk_report.py``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tau2_replay import openrouter_prices, patch_tau2_usage, recost, register_price, summarize  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default="airline")
    ap.add_argument("--modes", default="none", help="none | comma list of hint,veto,checklist,deliberate,reasoner,deliberate_all")
    ap.add_argument("--llm", default="deepseek/deepseek-chat")
    ap.add_argument("--llm-user", default=None, help="user simulator LLM (default: same as --llm)")
    ap.add_argument("--llm-args-agent", default='{"temperature": 0.0}')
    ap.add_argument("--num-tasks", type=int, default=50)
    ap.add_argument("--task-offset", type=int, default=0)
    ap.add_argument("--num-trials", type=int, default=4)
    ap.add_argument("--max-concurrency", type=int, default=4)
    ap.add_argument("--seed", type=int, default=300)
    ap.add_argument("--tau-hint", type=float, default=0.9)
    ap.add_argument("--tau-veto", type=float, default=0.9)
    ap.add_argument("--max-reconsider", type=int, default=1)
    ap.add_argument("--tau-uncertain", type=float, default=0.8, help="deliberate/reasoner trigger: Jev p_max below this")
    ap.add_argument("--reasoner-llm", default=None, help="model for 'reasoner' steps, e.g. deepseek/deepseek-reasoner")
    ap.add_argument("--reasoner-llm-args", default='{}')
    ap.add_argument("--checklist", default=None, help="JSON file with a list of {name,label,instructions,true,false}")
    ap.add_argument("--budget-usd", type=float, default=None, help="abort when the Jev spend passes this (LLM spend is not metered live)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    from tau2.data_model.semantic_communication import CommunicateScorer, CommunicateScoring  # type: ignore[import-not-found]
    from tau2.data_model.simulation import TextRunConfig  # type: ignore[import-not-found]
    from tau2.registry import registry  # type: ignore[import-not-found]
    from tau2.runner.batch import run_tasks  # type: ignore[import-not-found]

    from gdopt.decision import CachedDecisionModel, OpenRouterJev

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    prices = openrouter_prices(args.llm)
    register_price(args.llm, prices)
    prices_by_model = {args.llm: prices}
    llm_user = args.llm_user or args.llm
    for extra in (llm_user, args.reasoner_llm):
        if extra and extra not in prices_by_model:
            prices_by_model[extra] = openrouter_prices(extra)
            register_price(extra, prices_by_model[extra])
    print("prices $/token (prompt, completion, cached):", prices_by_model)
    patch_tau2_usage()

    modes = set() if args.modes.strip() in ("", "none") else {m.strip() for m in args.modes.split(",") if m.strip()}
    jev = None
    agents = []
    if modes:
        from gdopt.adapters.tau2_anchor import ChecklistQuestion, register_anchored_agent

        checklist = None
        if args.checklist:
            checklist = [ChecklistQuestion(**q) for q in json.loads(Path(args.checklist).read_text())]
        jev = CachedDecisionModel(OpenRouterJev())
        agents = register_anchored_agent(jev, modes, name="gdopt_anchored", tau_hint=args.tau_hint, tau_veto=args.tau_veto,
                                         checklist=checklist, max_reconsider=args.max_reconsider, tau_uncertain=args.tau_uncertain,
                                         reasoner_llm=args.reasoner_llm, reasoner_llm_args=json.loads(args.reasoner_llm_args))
        agent_name = "gdopt_anchored"
    else:
        agent_name = "llm_agent"

    tasks = registry.get_tasks_loader(args.domain)()[args.task_offset: args.task_offset + args.num_tasks]
    cfg = TextRunConfig(agent=agent_name, domain=args.domain, user="user_simulator", llm_agent=args.llm,
                        llm_args_agent=json.loads(args.llm_args_agent), llm_user=llm_user, llm_args_user={"temperature": 0.0},
                        num_trials=args.num_trials, max_concurrency=args.max_concurrency, seed=args.seed, log_level="ERROR", auto_resume=True,
                        communicate_scoring=CommunicateScoring(scorer=CommunicateScorer.SUBSTRING))
    res = run_tasks(cfg, tasks, save_path=out / "results.json", console_display=False)
    recost(out / "results.json", prices_by_model, prices)
    s = summarize(res, f"{agent_name}:{'+'.join(sorted(modes)) or 'none'}", prices, prices_by_model)
    if jev is not None:
        s["jev_cost_total"] = jev.inner.total_cost
        s["jev_calls"] = jev.inner.n_calls
        agg: dict[str, float] = {}
        for a in agents:
            for k, v in a.stats.items():
                agg[k] = agg.get(k, 0) + v
        s["anchor_stats"] = agg
    s["config"] = {"modes": sorted(modes), "llm": args.llm, "llm_user": llm_user, "num_tasks": args.num_tasks,
                   "num_trials": args.num_trials, "seed": args.seed, "tau_hint": args.tau_hint, "tau_veto": args.tau_veto,
                   "tau_uncertain": args.tau_uncertain, "reasoner_llm": args.reasoner_llm}
    (out / "summary.json").write_text(json.dumps(s, indent=1))
    print(json.dumps(s, indent=1))


if __name__ == "__main__":
    main()
