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
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
