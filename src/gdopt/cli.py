"""Command line: ``gdopt profile <tau2 results.json> ...``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .adapters.tau2 import load_results, results_info
from .profile import fit_situations, profile, split_by_trial
from .report import profile_markdown


def cmd_profile(args: argparse.Namespace) -> int:
    train_trials = [int(x) for x in args.train_trials.split(",")]
    for path in args.results:
        trajs = load_results(path)
        info = results_info(path)
        train, test = split_by_trial(trajs, train_trials)
        if not train or not test:
            print(f"{path}: need both train and test trials (have trials {sorted({t.trial for t in trajs})})", file=sys.stderr)
            continue
        model = fit_situations(train, max_depth=args.max_depth, min_leaf=args.min_leaf)
        rep = profile(model, train, test)
        title = f"GDOpt profile: {Path(path).stem} (agent {info['agent_llm']}, user {info['user_llm']})"
        md = profile_markdown(rep, title=title, top=args.top)
        if args.out_dir:
            out = Path(args.out_dir)
            out.mkdir(parents=True, exist_ok=True)
            (out / f"{Path(path).stem}.md").write_text(md)
            (out / f"{Path(path).stem}.json").write_text(json.dumps(rep.to_dict(), indent=1))
            print(f"wrote {out / (Path(path).stem + '.md')}")
        else:
            print(md)
    return 0


def cmd_shadow(args: argparse.Namespace) -> int:
    import random

    from .decision import CachedDecisionModel, ChoiceResult, OpenRouterJev, action_menu
    from .local_eval import local_eval_markdown, local_evaluate
    from .profile import candidate_tiers
    from .shadow import ShadowResult, shadow_evaluate
    from .adapters.tau2 import load_gold_actions
    from .trace import all_steps, tool_names

    path = args.results
    trajs = load_results(path)
    train, test = split_by_trial(trajs, [int(x) for x in args.train_trials.split(",")])
    model = fit_situations(train, max_depth=args.max_depth, min_leaf=args.min_leaf)
    rep = profile(model, train, test)
    cands = candidate_tiers(rep)
    keep = {lid for lid, t in cands.items() if t in set(args.tiers.split(","))}
    policy = Path(args.policy).read_text() if args.policy else None
    tools = {t: "" for t in tool_names(train)}
    if args.tool_descriptions:
        tools.update(json.loads(Path(args.tool_descriptions).read_text()))
    menu = action_menu(tools)

    steps = [s for s in all_steps(test) if model.situation(s.history).id in keep]
    rng = random.Random(args.seed)
    if args.max_steps and len(steps) > args.max_steps:
        steps = rng.sample(steps, args.max_steps)
    steps.sort(key=lambda s: (s.trajectory_id, s.index))

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cache_path = out / f"{Path(path).stem}.shadow-cache.json"
    jev = CachedDecisionModel(OpenRouterJev(model=args.model))
    if cache_path.exists():
        raw = json.loads(cache_path.read_text())
        jev.cache = {k: ChoiceResult(**v) for k, v in raw.items()}
    done = 0

    def save() -> None:
        cache_path.write_text(json.dumps({k: {"probabilities": v.probabilities, "cost": v.cost, "latency_s": v.latency_s} for k, v in jev.cache.items()}))

    def on_record(rec) -> None:
        nonlocal done
        done += 1
        if done % 25 == 0:
            save()
            print(f"  {done}/{len(steps)} shadow calls, ${jev.inner.total_cost:.4f}", file=sys.stderr)

    print(f"{len(steps)} steps in {len(keep)} candidate situations; calling {args.model} ...", file=sys.stderr)
    shadow: ShadowResult = shadow_evaluate(steps, model, jev, menu, policy=policy, on_record=on_record)
    save()
    gold = load_gold_actions(path)
    local = local_evaluate(shadow, test, model, gold)
    rules = {s.leaf_id: s.rule for s in rep.situations}
    md = local_eval_markdown(local, rules, title=f"GDOpt local verification: {Path(path).stem} with {args.model}")
    (out / f"{Path(path).stem}.shadow.md").write_text(md)
    (out / f"{Path(path).stem}.shadow.json").write_text(json.dumps(
        [{"trajectory_id": s.record.trajectory_id, "step_index": s.record.step_index, "leaf_id": s.record.leaf_id,
          "llm_action": s.record.llm_action, "probabilities": s.record.probabilities, "success": s.trajectory_success,
          "llm_gold": s.llm_gold, "jev_gold": s.jev_gold, "jev_args": s.jev_args, "verdict": s.verdict} for s in local.steps], indent=1))
    print(md)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="gdopt", description="GDOpt: find LLM steps replaceable by decision models")
    sub = p.add_subparsers(dest="cmd", required=True)
    pp = sub.add_parser("profile", help="stage 1+2: situations and per-situation statistics from τ²-bench results")
    pp.add_argument("results", nargs="+", help="τ²-bench results JSON file(s)")
    pp.add_argument("--train-trials", default="0,1", help="trials used to fit situations (others are held out)")
    pp.add_argument("--max-depth", type=int, default=6)
    pp.add_argument("--min-leaf", type=int, default=25)
    pp.add_argument("--top", type=int, default=None, help="only list the top-N situations")
    pp.add_argument("--out-dir", default=None, help="write <stem>.md and <stem>.json here instead of stdout")
    pp.set_defaults(func=cmd_profile)
    ps = sub.add_parser("shadow", help="stage 3a: shadow Jev calls on held-out steps + local verification (needs OPENROUTER_API_KEY)")
    ps.add_argument("results", help="τ²-bench results JSON file")
    ps.add_argument("--policy", default=None, help="domain policy markdown to include in the decision state")
    ps.add_argument("--tool-descriptions", default=None, help="JSON {tool name: description} for the action menu")
    ps.add_argument("--model", default="typesafe/jev-1.14")
    ps.add_argument("--tiers", default="code,jev", help="candidate tiers to shadow")
    ps.add_argument("--max-steps", type=int, default=400, help="sample at most this many held-out steps (cost control)")
    ps.add_argument("--seed", type=int, default=0)
    ps.add_argument("--train-trials", default="0,1")
    ps.add_argument("--max-depth", type=int, default=6)
    ps.add_argument("--min-leaf", type=int, default=25)
    ps.add_argument("--out-dir", default="reports/shadow")
    ps.set_defaults(func=cmd_shadow)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
