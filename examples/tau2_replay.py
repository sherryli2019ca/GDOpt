"""Stage 3b/4 on τ²-bench: run the original agent and the tiered agent on the same tasks.

Needs τ²-bench importable (PYTHONPATH to its src), OPENROUTER_API_KEY, and the
stage-2/3 artifacts: a τ²-bench results file to fit situations on, and a
`gdopt shadow` JSON for the tier thresholds.

Example:
  PYTHONPATH=tau2-bench/src:src python examples/tau2_replay.py \
      --domain airline --fit-results tau2-bench/data/tau2/results/final/gpt-4.1-2025-04-14_airline_default_gpt-4.1-2025-04-14_4trials.json \
      --shadow reports/shadow-desc/gpt-4.1-2025-04-14_airline_default_gpt-4.1-2025-04-14_4trials.shadow.json \
      --llm openrouter/deepseek/deepseek-chat --num-tasks 50 --out reports/replay/airline
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from gdopt.adapters.tau2 import load_results
from gdopt.trace import MESSAGE_ACTION
from gdopt.decision import CachedDecisionModel, OpenRouterJev
from gdopt.profile import fit_situations, profile, split_by_trial
from gdopt.shadow import ShadowRecord, ShadowResult
from gdopt.tiers import TierTable


def build_tier_table(fit_results: str, shadow_json: str, min_agreement: float, max_depth: int, min_leaf: int, min_tool_coverage: float = 0.0):
    trajs = load_results(fit_results)
    train, test = split_by_trial(trajs, [0, 1])
    model = fit_situations(train, max_depth=max_depth, min_leaf=min_leaf)
    rep = profile(model, train, test)
    recs = [ShadowRecord(r["trajectory_id"], r["step_index"], r["leaf_id"], r["llm_action"], r["probabilities"], 0.0) for r in json.loads(Path(shadow_json).read_text())]
    shadow = ShadowResult(recs, 0.0).by_situation()
    table = TierTable.from_profile(rep, shadow, min_agreement=min_agreement, min_tool_coverage=min_tool_coverage)
    return model, rep, table


DEFAULT_PRICES = {"openrouter/deepseek/deepseek-chat": (0.2574e-6, 1.0287e-6)}  # $/token (prompt, completion), OpenRouter 2026-10-22


def openrouter_prices(llm: str) -> tuple[float, float]:
    """(prompt, completion) $/token for an ``openrouter/<id>`` model, from the OpenRouter model list."""
    try:
        import urllib.request

        with urllib.request.urlopen("https://openrouter.ai/api/v1/models", timeout=20) as r:
            data = json.load(r)["data"]
        mid = llm.split("openrouter/", 1)[1]
        for m in data:
            if m["id"] == mid:
                return float(m["pricing"]["prompt"]), float(m["pricing"]["completion"])
    except Exception as e:  # pragma: no cover - network
        print("price lookup failed:", e)
    return DEFAULT_PRICES.get(llm, (0.0, 0.0))


def register_price(llm: str, prices: tuple[float, float]) -> None:
    """Teach litellm the price so τ²-bench's per-message ``cost`` is filled in."""
    import litellm  # type: ignore[import-not-found]

    litellm.register_model({llm: {"input_cost_per_token": prices[0], "output_cost_per_token": prices[1],
                                  "litellm_provider": "openrouter", "mode": "chat"}})


def action_of(m) -> str:
    calls = m.tool_calls or []
    return f"tool:{calls[0].name}" if calls else MESSAGE_ACTION


def summarize(results, name: str, prices: tuple[float, float] = (0.0, 0.0)) -> dict:
    sims = results.simulations
    rewards = [float((s.reward_info.reward if s.reward_info else 0.0) or 0.0) for s in sims]
    # τ²'s ``agent_cost`` is None when any message lacks a cost (the fixed greeting), so sum per message.
    cost = sum(float(m.cost or 0.0) for s in sims for m in (s.messages or []) if getattr(m, "role", "") == "assistant")
    tiers: Counter = Counter()
    fallback: Counter = Counter()
    agree: Counter = Counter()  # in-loop shadow: cheap tier proposal vs what the LLM did on fallback steps
    n_steps = n_llm = 0
    llm_cost_usage = decision_cost = 0.0
    prompt_tokens = completion_tokens = 0
    for s in sims:
        for m in s.messages or []:
            if getattr(m, "role", "") != "assistant":
                continue
            g = (m.raw_data or {}).get("gdopt") if m.raw_data else None
            usage = m.usage or {}
            if not g and not usage:
                continue  # fixed opening greeting, no model call
            n_steps += 1
            pt, ct = int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0)
            prompt_tokens += pt
            completion_tokens += ct
            llm_cost_usage += pt * prices[0] + ct * prices[1]
            if g:
                tiers[g["tier"]] += 1
                n_llm += 1 if g["llm_called"] else 0
                decision_cost += float(g.get("decision_cost") or 0.0)
                if g.get("fallback_reason"):
                    fallback[g["fallback_reason"]] += 1
                if g["llm_called"] and g.get("proposed"):
                    agree["same" if g["proposed"] == action_of(m) else "different"] += 1
                    if g["proposed"] != action_of(m):
                        agree[f"{g['proposed']} -> {action_of(m)}"] += 1
            else:
                n_llm += 1
    n = max(1, len(sims))
    return {
        "agent": name, "n_tasks": len(sims), "success_rate": sum(1 for r in rewards if r >= 1.0) / n,
        "mean_reward": sum(rewards) / max(1, len(rewards)),
        "agent_cost_total": cost, "agent_cost_per_task": cost / n,
        "llm_cost_from_usage": llm_cost_usage, "decision_cost": decision_cost, "total_cost_from_usage": llm_cost_usage + decision_cost,
        "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
        "steps": n_steps, "llm_steps": n_llm, "llm_step_share": n_llm / max(1, n_steps), "tiers": dict(tiers),
        "fallback_reasons": dict(fallback), "in_loop_agreement": dict(agree),
        "rewards": rewards,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default="airline")
    ap.add_argument("--fit-results", required=True)
    ap.add_argument("--shadow", required=True)
    ap.add_argument("--llm", default="openrouter/deepseek/deepseek-chat")
    ap.add_argument("--llm-user", default=None, help="user simulator LLM (default: same as --llm)")
    ap.add_argument("--num-tasks", type=int, default=50)
    ap.add_argument("--task-offset", type=int, default=0)
    ap.add_argument("--num-trials", type=int, default=1)
    ap.add_argument("--max-concurrency", type=int, default=4)
    ap.add_argument("--seed", type=int, default=300)
    ap.add_argument("--lam", type=float, default=0.0)
    ap.add_argument("--min-agreement", type=float, default=0.9)
    ap.add_argument("--min-tool-coverage", type=float, default=0.0,
                    help="cost-aware tier table: drop Jev situations whose confident-tool coverage at tau is below this "
                         "(Jev/LLM cost ratio is ~0.08 for DeepSeek; 0.16 = require 2x break-even)")
    ap.add_argument("--max-depth", type=int, default=6)
    ap.add_argument("--min-leaf", type=int, default=25)
    ap.add_argument("--skip-baseline", action="store_true")
    ap.add_argument("--skip-tiered", action="store_true")
    ap.add_argument("--out", default="reports/replay/airline")
    args = ap.parse_args()

    from tau2.data_model.semantic_communication import CommunicateScorer, CommunicateScoring  # type: ignore[import-not-found]
    from tau2.data_model.simulation import TextRunConfig  # type: ignore[import-not-found]
    from tau2.registry import registry  # type: ignore[import-not-found]
    from tau2.runner.batch import run_tasks  # type: ignore[import-not-found]

    from gdopt.adapters.tau2_agent import register_tiered_agent

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    prices = openrouter_prices(args.llm)
    print("prices $/token (prompt, completion):", prices)
    register_price(args.llm, prices)
    if args.llm_user and args.llm_user != args.llm:
        register_price(args.llm_user, openrouter_prices(args.llm_user))
    model, rep, table = build_tier_table(args.fit_results, args.shadow, args.min_agreement, args.max_depth, args.min_leaf, args.min_tool_coverage)
    rules = {s.leaf_id: s.rule for s in rep.situations}
    (out / "tier_table.json").write_text(json.dumps(
        [{"leaf_id": r.leaf_id, "rule": rules.get(r.leaf_id, ""), "tier": r.tier.value, "tau": r.tau, "action": r.action, "rationale": r.rationale} for r in table.rules.values()], indent=1))
    print("tier table:", table.counts())

    jev = CachedDecisionModel(OpenRouterJev())
    agents = register_tiered_agent(model, table, jev, name="gdopt_tiered", lam=args.lam)

    tasks = registry.get_tasks_loader(args.domain)()[args.task_offset: args.task_offset + args.num_tasks]
    llm_user = args.llm_user or args.llm
    common = dict(domain=args.domain, user="user_simulator", llm_agent=args.llm, llm_args_agent={"temperature": 0.0},
                  llm_user=llm_user, llm_args_user={"temperature": 0.0}, num_trials=args.num_trials,
                  max_concurrency=args.max_concurrency, seed=args.seed, log_level="ERROR",
                  # τ²-bench's current default scores communicate_info with an OpenAI judge; use the original
                  # substring scorer so the run needs only OpenRouter.
                  communicate_scoring=CommunicateScoring(scorer=CommunicateScorer.SUBSTRING))
    summaries = []
    if not args.skip_baseline:
        res = run_tasks(TextRunConfig(agent="llm_agent", **common), tasks, save_path=out / "baseline.json", console_display=False)
        summaries.append(summarize(res, "llm_agent", prices))
        print(json.dumps(summaries[-1], indent=1))
    if not args.skip_tiered:
        res = run_tasks(TextRunConfig(agent="gdopt_tiered", **common), tasks, save_path=out / "tiered.json", console_display=False)
        s = summarize(res, "gdopt_tiered", prices)
        s["jev_cost_total"] = jev.inner.total_cost
        s["jev_calls"] = jev.inner.n_calls
        summaries.append(s)
        print(json.dumps(s, indent=1))
    (out / "summary.json").write_text(json.dumps(summaries, indent=1))


if __name__ == "__main__":
    main()
