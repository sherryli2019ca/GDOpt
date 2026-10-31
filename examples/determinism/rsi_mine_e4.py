"""RSI round 2 (R1'): mine checks from the failures of the current best agent (E4, two runs, 8 trials/task).

Same miner, prompt and sandbox as rsi_mine.py, with three changes aimed at stability (pass^k), not pass^1:
  * cases come from E4's own failed trials; for a flaky task each case also shows what a SUCCESSFUL trial of the same
    task did at the decisive write (first write-level difference, e4_forks.py), so the miner sees the fork;
  * found / transfer are judged on E4 episodes only (mining fold: fail >= 2 and >= 3x success; held-out: fail >= 1 and
    >= 3x success), and harm is also counted on all 3000 logged successful airline episodes (older configs included);
  * for each transferring check, a counterfactual pass^4 on the held-out tasks if every flagged failed trial had
    succeeded (upper bound on the stability gain).
Run from repo root with DEEPSEEK_API_KEY; writes reports/rsi/r1_e4.json and R1_E4.md.
"""
import json
import math
import os
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import rsi_mine as M  # noqa: E402
import e4_forks as F  # noqa: E402

OUT = Path("reports/rsi")
E4 = ["deliberate_reasoner_rules_consistency"] + [f"e4_mined-fold{k}" for k in range(3)]


def load_runs(runs):
    old = M.RUNS
    M.RUNS = runs
    try:
        return M.load()
    finally:
        M.RUNS = old


def fork_cases(e4, tasks, n=24):
    """Failed E4 trials of the mining tasks, with the success branch at the decisive write when the task is flaky."""
    by = defaultdict(list)
    for e in e4:
        by[e["task"]].append(e)
    out = []
    for t in sorted(tasks, key=int):
        succ = [e for e in by[t] if e["ok"]]
        for f in (e for e in by[t] if not e["ok"]):
            c = M.culprit(f)
            if succ:
                best = max(succ, key=lambda s: F.common_prefix(f["msgs"], s["msgs"]))
                x, y = F.decisive(f["msgs"], best["msgs"])
                if x is not None:
                    i = x[0]
                    tc = next(tc for tc in f["msgs"][i]["tool_calls"] if tc["name"] in F.DECISIVE)
                    c = (i, tc, "flaky task: a successful trial of the same task did something else here")
                    alt = (f"SUCCESSFUL TRIAL INSTEAD DID: {y[1]}({y[2]})" if y else
                           "SUCCESSFUL TRIAL INSTEAD: made no further write")
                else:
                    alt = None
            else:
                alt = "this task failed in all 8 trials"
            if not c:
                continue
            i, tc, why = c
            gold = "; ".join(f"{g['name']}({json.dumps(g['arguments'])})" for g in f["gold"]
                             if g["name"] in F.DECISIVE) or "(no writes)"
            out.append(f"## case {len(out) + 1} ({why})\n{M.render(f['msgs'], i)}\nCULPRIT: {tc['name']}({json.dumps(tc['arguments'])})\n"
                       f"{alt or ''}\nGOLD WRITES: {gold}")
    random.Random(0).shuffle(out)
    return out[:n]


def ph(c, n, k):
    return math.comb(c, k) / math.comb(n, k) if c >= k else 0.0


def main():
    old = load_runs(M.RUNS)
    e4 = load_runs(E4)
    r1 = json.loads((OUT / "r1.json").read_text())
    folds = [set(f) for f in r1["folds"]]
    tasks = set().union(*folds)
    policy = e4[0]["policy"]
    succ_all = [e for e in old + e4 if e["ok"]]
    out = {"model": M.MODEL, "folds": r1["folds"], "e4_episodes": len(e4), "mined": []}
    M.LOG = OUT / "calls_e4.jsonl"
    rng = random.Random(1)
    for k, mine in enumerate(folds):
        held = tasks - mine
        cases = fork_cases(e4, mine)
        contrast = M.contrast_for(e4, mine, rng)
        print(f"fold {k}: {len(cases)} cases", flush=True)
        if not cases:
            continue
        props = M.deepseek(M.PROMPT.format(policy=policy, cases="\n\n".join(cases), contrast="\n\n".join(contrast)))
        for p in props:
            rec = {"fold": k, "name": p.get("name"), "description": p.get("description"), "clause": p.get("clause"), "versions": []}
            code = p.get("code", "")
            for rnd in range(2):
                try:
                    fn = M.compile_check(code)
                    res, fp = M.evaluate(fn, e4, mine, held)
                    by_all, _, _ = M.audit(fn, succ_all)
                    res["all_success_fires"] = sum(v["success"] for v in by_all.values())
                except Exception as e:  # noqa: BLE001
                    res, fp = {"invalid": str(e)[:200], "found": False, "transfers": False}, []
                rec["versions"].append({"code": code, **res})
                if res.get("found") or rnd == 1:
                    break
                rev = M.deepseek(M.REVISE.format(name=rec["name"], f=res.get("mine_fail", 0), s=res.get("mine_success", 0),
                                                 why=res.get("invalid") or "", code=code,
                                                 fp=("A successful episode it flagged:\n" + fp[0]) if fp else ""))
                if not rev:
                    break
                code = rev[0].get("code", "")
            rec.update({x: v for x, v in rec["versions"][-1].items() if x != "code"})
            out["mined"].append(rec)
            print(k, rec["name"], {x: rec.get(x) for x in ("mine_fail", "mine_success", "held_fail", "held_success", "all_success_fires", "found", "transfers")}, flush=True)
        (OUT / "r1_e4.json").write_text(json.dumps(out, indent=1))

    # counterfactual stability on held-out tasks: flagged failed trials of transferring checks counted as successes
    for k, mine in enumerate(folds):
        held = sorted(tasks - mine, key=int)
        fns = [M.compile_check(r["versions"][-1]["code"]) for r in out["mined"] if r["fold"] == k and r.get("transfers")]
        res = defaultdict(lambda: [0, 0, 0])  # task -> [successes, n, rescued]
        for e in e4:
            if e["task"] not in held:
                continue
            r = res[e["task"]]
            r[1] += 1
            if e["ok"]:
                r[0] += 1
            elif any(any(fn({"name": tc["name"], "arguments": tc["arguments"]}, e["msgs"][:i]) for i, tc in M.calls(e)) for fn in fns):
                r[2] += 1
        out.setdefault("counterfactual", {})[k] = {
            "checks": len(fns),
            "pass1": round(100 * sum(c / n for c, n, _ in res.values()) / len(held), 1),
            "pass4": round(100 * sum(ph(c, n, 4) for c, n, _ in res.values()) / len(held), 1),
            "pass1_cf": round(100 * sum((c + x) / n for c, n, x in res.values()) / len(held), 1),
            "pass4_cf": round(100 * sum(ph(c + x, n, 4) for c, n, x in res.values()) / len(held), 1),
            "rescued_trials": sum(x for _, _, x in res.values()), "failed_trials": sum(n - c for c, n, _ in res.values())}
    (OUT / "r1_e4.json").write_text(json.dumps(out, indent=1))
    lines = ["# RSI R1' — checks mined from E4's own failures (airline, 3-fold task split)", "",
             "| fold | check | mine fail/succ (E4) | held fail/succ (E4) | success fires, all 3000 logs | found | transfers |",
             "|---|---|---|---|---|---|---|"]
    for r in out["mined"]:
        lines.append(f"| {r['fold']} | {r['name']} | {r.get('mine_fail')}/{r.get('mine_success')} | {r.get('held_fail')}/{r.get('held_success')} | "
                     f"{r.get('all_success_fires')} | {r.get('found')} | {r.get('transfers')} |")
    lines += ["", "Counterfactual on held-out tasks (every flagged failed trial counted as a success; upper bound):", "",
              "| fold | transferring checks | rescued / failed trials | pass^1 → cf | pass^4 → cf |", "|---|---|---|---|---|"]
    for k, c in out.get("counterfactual", {}).items():
        lines.append(f"| {k} | {c['checks']} | {c['rescued_trials']}/{c['failed_trials']} | {c['pass1']} → {c['pass1_cf']} | {c['pass4']} → {c['pass4_cf']} |")
    (OUT / "R1_E4.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
