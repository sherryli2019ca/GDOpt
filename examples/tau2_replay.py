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


# $/token (prompt, completion, cached prompt), OpenRouter 2026-10-22. deepseek-chat reports cached tokens but
# is not discounted for them on OpenRouter (verified), so its cache price equals its prompt price.
DEFAULT_PRICES = {
    "openrouter/deepseek/deepseek-chat": (0.2574e-6, 1.0287e-6, 0.2574e-6),
    # Direct DeepSeek API (needs DEEPSEEK_API_KEY and api.deepseek.com reachable): cache-miss / output / cache-hit.
    # List prices as of 2025-09 ($0.27 / $1.10 / $0.07 per M); verify at api-docs.deepseek.com before quoting.
    "deepseek/deepseek-chat": (0.27e-6, 1.10e-6, 0.07e-6),
    "deepseek/deepseek-reasoner": (0.55e-6, 2.19e-6, 0.14e-6),
}
_MODEL_LIST: list[dict] | None = None


def openrouter_prices(llm: str) -> tuple[float, float, float]:
    """(prompt, completion, cached-prompt) $/token for an ``openrouter/<id>`` model, from the OpenRouter model list.
    Non-OpenRouter models fall back to ``DEFAULT_PRICES``."""
    global _MODEL_LIST
    if not llm.startswith("openrouter/"):
        return DEFAULT_PRICES.get(llm, (0.0, 0.0, 0.0))
    try:
        if _MODEL_LIST is None:
            import urllib.request

            with urllib.request.urlopen("https://openrouter.ai/api/v1/models", timeout=20) as r:
                _MODEL_LIST = json.load(r)["data"]
        mid = llm.split("openrouter/", 1)[1]
        for m in _MODEL_LIST:
            if m["id"] == mid:
                p = m["pricing"]
                prompt = float(p["prompt"])
                cached = float(p["input_cache_read"]) if p.get("input_cache_read") else prompt
                if mid == "deepseek/deepseek-chat":
                    cached = prompt
                return prompt, float(p["completion"]), cached
    except Exception as e:  # pragma: no cover - network
        print("price lookup failed:", e)
    return DEFAULT_PRICES.get(llm, (0.0, 0.0, 0.0))


def patch_tau2_usage() -> None:
    """Make τ²-bench keep cached-token counts and the model name in every message's ``usage``."""
    from tau2.utils import llm_utils  # type: ignore[import-not-found]

    def get_response_usage(response):
        usage = response.get("usage")
        if usage is None:
            return None
        details = getattr(usage, "prompt_tokens_details", None)
        return {
            "completion_tokens": usage.completion_tokens,
            "prompt_tokens": usage.prompt_tokens,
            "cached_tokens": int(getattr(details, "cached_tokens", 0) or 0) if details else 0,
            "model": getattr(response, "model", None),
        }

    llm_utils.get_response_usage = get_response_usage


def usage_cost(usage: dict, prices_by_model: dict[str, tuple[float, float, float]], default: tuple[float, float, float]) -> float:
    """Cost of one generative call from its token usage, honouring the cache-read price."""
    pr = default
    model = (usage.get("model") or "")
    for k, v in prices_by_model.items():
        if model and (k.split("openrouter/", 1)[-1] in model or k.split("/")[-1] in model):
            pr = v
    pt, ct, cached = int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0), int(usage.get("cached_tokens") or 0)
    return (pt - cached) * pr[0] + cached * pr[2] + ct * pr[1]


def recost(path: Path, prices_by_model: dict[str, tuple[float, float, float]], default: tuple[float, float, float]) -> None:
    """Rewrite every assistant message's ``cost`` in a saved τ² results file from usage + OpenRouter prices
    (cache-aware), plus the recorded decision-model cost."""
    d = json.loads(path.read_text())
    for s in d["simulations"]:
        for m in s["messages"]:
            if m.get("role") != "assistant":
                continue
            g = (m.get("raw_data") or {}).get("gdopt") or {}
            if m.get("usage") and m["usage"].get("prompt_tokens"):
                m["cost"] = usage_cost(m["usage"], prices_by_model, default) + float(g.get("decision_cost") or 0.0)
            elif g:
                m["cost"] = float(g.get("decision_cost") or 0.0)
        s["agent_cost"] = sum(float(m.get("cost") or 0.0) for m in s["messages"] if m.get("role") == "assistant")
    path.write_text(json.dumps(d, indent=2))


def register_price(llm: str, prices: tuple[float, ...]) -> None:
    """Teach litellm the price so τ²-bench's per-message ``cost`` is filled in."""
    import litellm  # type: ignore[import-not-found]

    provider = llm.split("/", 1)[0] if "/" in llm else "openrouter"
    litellm.register_model({llm: {"input_cost_per_token": prices[0], "output_cost_per_token": prices[1],
                                  "litellm_provider": provider, "mode": "chat"}})


def action_of(m) -> str:
    calls = m.tool_calls or []
    return f"tool:{calls[0].name}" if calls else MESSAGE_ACTION


def summarize(results, name: str, prices: tuple[float, ...] = (0.0, 0.0, 0.0), prices_by_model: dict | None = None) -> dict:
    sims = results.simulations
    rewards = [float((s.reward_info.reward if s.reward_info else 0.0) or 0.0) for s in sims]
    # τ²'s ``agent_cost`` is None when any message lacks a cost (the fixed greeting), so sum per message.
    cost = sum(float(m.cost or 0.0) for s in sims for m in (s.messages or []) if getattr(m, "role", "") == "assistant")
    tiers: Counter = Counter()
    fallback: Counter = Counter()
    agree: Counter = Counter()  # in-loop shadow: cheap tier proposal vs what the LLM did on fallback steps
    generators: Counter = Counter()
    prices_by_model = prices_by_model or {}
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
            llm_cost_usage += usage_cost(usage, prices_by_model, tuple(prices)) if usage else 0.0
            if g:
                tiers[g["tier"]] += 1
                if g.get("generator"):
                    generators[g["generator"]] += 1
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
        "fallback_reasons": dict(fallback), "in_loop_agreement": dict(agree), "generators": dict(generators),
        "rewards": rewards,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default="airline")
    ap.add_argument("--fit-results", required=True)
    ap.add_argument("--shadow", required=True)
    ap.add_argument("--llm", default="openrouter/deepseek/deepseek-chat")
    ap.add_argument("--llm-user", default=None, help="user simulator LLM (default: same as --llm)")
    ap.add_argument("--llm-args-agent", default='{"temperature": 0.0}', help="JSON kwargs for the agent LLM (litellm)")
    ap.add_argument("--message-llm", default=None,
                    help="cascade: cheaper generative model that writes the text when a cheap tier is confident the next "
                         "step is a message (tiered agent only)")
    ap.add_argument("--message-llm-args", default='{"temperature": 0.0}', help="JSON kwargs for --message-llm")
    ap.add_argument("--agent-name", default="gdopt_tiered", help="name used in summary.json for the tiered agent")
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
    print("prices $/token (prompt, completion, cached):", prices)
    register_price(args.llm, prices)
    prices_by_model = {args.llm: prices}
    for extra in (args.llm_user, args.message_llm):
        if extra and extra not in prices_by_model:
            prices_by_model[extra] = openrouter_prices(extra)
            register_price(extra, prices_by_model[extra])
    patch_tau2_usage()
    llm_args_agent = json.loads(args.llm_args_agent)
    model, rep, table = build_tier_table(args.fit_results, args.shadow, args.min_agreement, args.max_depth, args.min_leaf, args.min_tool_coverage)
    rules = {s.leaf_id: s.rule for s in rep.situations}
    (out / "tier_table.json").write_text(json.dumps(
        [{"leaf_id": r.leaf_id, "rule": rules.get(r.leaf_id, ""), "tier": r.tier.value, "tau": r.tau, "action": r.action, "rationale": r.rationale} for r in table.rules.values()], indent=1))
    print("tier table:", table.counts())

    jev = CachedDecisionModel(OpenRouterJev())
    agents = register_tiered_agent(model, table, jev, name="gdopt_tiered", lam=args.lam,
                                   message_llm=args.message_llm, message_llm_args=json.loads(args.message_llm_args))

    tasks = registry.get_tasks_loader(args.domain)()[args.task_offset: args.task_offset + args.num_tasks]
    llm_user = args.llm_user or args.llm
    common = dict(domain=args.domain, user="user_simulator", llm_agent=args.llm, llm_args_agent=llm_args_agent,
                  llm_user=llm_user, llm_args_user={"temperature": 0.0}, num_trials=args.num_trials,
                  max_concurrency=args.max_concurrency, seed=args.seed, log_level="ERROR",
                  # τ²-bench's current default scores communicate_info with an OpenAI judge; use the original
                  # substring scorer so the run needs only OpenRouter.
                  communicate_scoring=CommunicateScoring(scorer=CommunicateScorer.SUBSTRING))
    summaries = []
    if not args.skip_baseline:
        res = run_tasks(TextRunConfig(agent="llm_agent", **common), tasks, save_path=out / "baseline.json", console_display=False)
        recost(out / "baseline.json", prices_by_model, prices)
        summaries.append(summarize(res, "llm_agent", prices, prices_by_model))
        print(json.dumps(summaries[-1], indent=1))
    if not args.skip_tiered:
        res = run_tasks(TextRunConfig(agent="gdopt_tiered", **common), tasks, save_path=out / "tiered.json", console_display=False)
        recost(out / "tiered.json", prices_by_model, prices)
        s = summarize(res, args.agent_name, prices, prices_by_model)
        s["jev_cost_total"] = jev.inner.total_cost
        s["jev_calls"] = jev.inner.n_calls
        summaries.append(s)
        print(json.dumps(s, indent=1))
    (out / "summary.json").write_text(json.dumps(summaries, indent=1))


if __name__ == "__main__":
    main()
