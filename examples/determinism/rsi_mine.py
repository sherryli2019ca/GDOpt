"""RSI round R1: can an automatic loop that sees only a third of the tasks mine checks that hold on the other tasks?

For a fixed 3-fold task split of the logged airline runs (13 runs x 50 tasks x 4 trials):
  1. mining fold: collect failed episodes, locate the culprit agent call (first write whose name/arguments match no gold
     action, or a transfer to a human the gold does not contain) and show it with the preceding dialogue, next to the
     gold actions; also show correct calls from successful episodes of the same tools as contrast;
  2. deepseek-reasoner proposes up to 6 checks as Python predicates `check(call, history) -> bool` (True = flag),
     forbidden to name ids, people, flight numbers or dates (static check);
  3. audit every predicate on every logged episode (zero cost); a check is "found" if on the mining fold it fires in
     >= 2 failed episodes and fail >= 3x success; checks that miss get one revision round with their counts and one
     false-positive snippet;
  4. a found check "transfers" if on the two held-out folds it fires in >= 1 failed episode with fail >= 3x success.
The hand-written checks (new_rule_audit.py) are scored on the same split as the reference.

Run from repo root with DEEPSEEK_API_KEY set; writes reports/rsi/r1.json and reports/rsi/R1.md.
"""
import json
import os
import random
import re
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
import new_rule_audit as hand  # noqa: E402

ANCHOR = Path("reports/anchor")
OUT = Path(os.environ.get("OUT_DIR", "reports/rsi"))
RUNS = hand.RUNS + ["deliberate_reasoner_rules_consistency", "policy", "policy_reasoner", "vote"]
WRITES = hand.WRITES
SEED = int(os.environ.get("SEED", "0"))
MODEL = os.environ.get("MINER_MODEL", "deepseek-reasoner")
LOG = OUT / "calls.jsonl"

FORBIDDEN = [re.compile(p) for p in (
    r"['\"][A-Z0-9]{6}['\"]",          # reservation ids
    r"['\"]HAT\d{3}['\"]",              # flight numbers
    r"['\"][a-z]+_[a-z]+_\d{3,5}['\"]",  # user ids
    r"20\d\d-\d\d-\d\d",               # dates
    r"task",
    r"subprocess|open\(|__import__|eval\(|exec\(|getattr|globals|__",
)]
SAFE_BUILTINS = {k: __builtins__[k] if isinstance(__builtins__, dict) else getattr(__builtins__, k) for k in (
    "len", "any", "all", "sum", "min", "max", "sorted", "set", "list", "dict", "tuple", "str", "int", "float", "bool",
    "isinstance", "enumerate", "zip", "range", "abs", "round", "reversed", "map", "filter", "ValueError", "KeyError",
    "TypeError", "Exception")}
ALLOWED_MODULES = {"re", "json", "datetime", "math", "collections", "itertools"}
_real_import = __import__


def _safe_import(name, *a, **kw):
    if name.split(".")[0] not in ALLOWED_MODULES:
        raise ImportError(f"module {name} not allowed")
    return _real_import(name, *a, **kw)


SAFE_BUILTINS["__import__"] = _safe_import


# ---------------------------------------------------------------- episodes

def simplify(messages):
    """Messages as plain dicts: role, content, tool_calls [{name, arguments}], tool results parsed to JSON."""
    out = []
    for m in messages:
        d = {"role": m["role"], "content": m.get("content") or ""}
        if m.get("tool_calls"):
            d["tool_calls"] = [{"name": t["name"], "arguments": t.get("arguments") or {}} for t in m["tool_calls"]]
        if m["role"] == "tool":
            try:
                d["result"] = json.loads(d["content"])
            except (ValueError, TypeError):
                d["result"] = d["content"]
        out.append(d)
    return out


def load():
    eps = []
    for run in RUNS:
        p = ANCHOR / f"airline-{run}" / "results.json"
        if not p.exists():
            continue
        data = json.load(open(p))
        for s in data["simulations"]:
            ri = s.get("reward_info") or {}
            gold = [c["action"] for c in ri.get("action_checks") or []]
            eps.append({"run": run, "task": str(s["task_id"]), "trial": s.get("trial"),
                        "ok": (ri.get("reward") or 0.0) >= 0.999, "msgs": simplify(s["messages"]), "gold": gold,
                        "policy": s.get("policy"), "hand": list(hand.audit(s))})
    return eps


def calls(ep):
    """(index, call) for every agent tool call, in order."""
    for i, m in enumerate(ep["msgs"]):
        if m["role"] == "assistant":
            for tc in m.get("tool_calls") or []:
                yield i, tc


def same(a, b):
    return a["name"] == b["name"] and json.dumps(a.get("arguments"), sort_keys=True) == json.dumps(b.get("arguments"), sort_keys=True)


def culprit(ep):
    gold_names = Counter(g["name"] for g in ep["gold"])
    for i, tc in calls(ep):
        if tc["name"] in WRITES and not any(same(tc, g) for g in ep["gold"]):
            return i, tc, "write not in gold (wrong arguments or extra write)"
        if tc["name"] == "transfer_to_human_agents" and not gold_names.get("transfer_to_human_agents"):
            return i, tc, "transfer to a human not in gold"
    return None


def render(msgs, upto, keep=14, width=260):
    """Last `keep` messages before `upto`: dialogue text and calls in full up to `width`, tool results shorter."""
    lines = []
    for m in msgs[max(0, upto - keep):upto]:
        if m.get("tool_calls"):
            lines.append(f"[assistant calls] " + "; ".join(f"{t['name']}({json.dumps(t['arguments'])})" for t in m["tool_calls"]))
        if m["content"] and m["role"] != "tool":
            lines.append(f"[{m['role']}] {m['content'][:width]}")
        elif m["role"] == "tool":
            lines.append(f"[tool result] {m['content'][:width // 2]}")
    return "\n".join(lines)


# ---------------------------------------------------------------- predicates

def compile_check(code):
    for p in FORBIDDEN:
        if p.search(code):
            raise ValueError(f"forbidden pattern {p.pattern}")
    env = {"__builtins__": SAFE_BUILTINS, "json": json, "re": re}
    exec(compile(code, "<rule>", "exec"), env)  # noqa: S102 - generated predicates, restricted builtins
    if "check" not in env:
        raise ValueError("no check() defined")
    return env["check"]


def audit(fn, eps):
    """task -> Counter(fail, success) of episodes where fn flags at least one call; plus examples."""
    by = defaultdict(Counter)
    errors = 0
    fp = []
    for ep in eps:
        hit = False
        for i, tc in calls(ep):
            try:
                if fn({"name": tc["name"], "arguments": tc["arguments"]}, ep["msgs"][:i]):
                    hit = (i, tc)
                    break
            except Exception:  # noqa: BLE001
                errors += 1
        if hit:
            by[ep["task"]]["fail" if not ep["ok"] else "success"] += 1
            if ep["ok"] and len(fp) < 3:
                fp.append(render(ep["msgs"], hit[0] + 1, keep=6, width=300))
    return by, errors, fp


def score(by, tasks):
    f = sum(by[t]["fail"] for t in tasks)
    s = sum(by[t]["success"] for t in tasks)
    return f, s


def ok_ratio(f, s, min_fail):
    return f >= min_fail and f >= 3 * s


# ---------------------------------------------------------------- miner

PROMPT = """You are improving an airline customer-service agent. Below are its policy, the interface for checks, and
failed episodes: in each, the agent made a call (marked CULPRIT) that the gold solution did not contain, next to the
gold actions. Also shown: correct calls of the same tools from successful episodes.

Write up to 6 CHECKS. A check is a Python function `check(call, history) -> bool` that returns True when the agent's
call should be stopped and re-examined. It runs online, before the call executes, so it may use only `call`
({{"name": str, "arguments": dict}}) and `history` (list of earlier messages: {{"role": "user"|"assistant"|"tool",
"content": str, "tool_calls": [{{"name", "arguments"}}] (assistant only), "result": parsed JSON (tool only)}}).
Never use the gold actions. Modules `json` and `re` are available; nothing else may be imported.

Rules:
- A check must capture a GENERAL mistake pattern that recurs across different customers and requests, grounded in a
  policy clause or in consistency between the call and what the user said / what tool results showed.
- No literal reservation ids, user ids, names, flight numbers, dates or amounts from the examples.
- It must stay False on correct behaviour (a check that fires in successful episodes is harmful).
- Prefer precise conditions over broad ones; return False whenever the needed facts are missing.

Answer with JSON only: {{"checks": [{{"name": "snake_case", "description": "...", "clause": "policy text or
consistency rule it enforces", "code": "def check(call, history):\\n    ..."}}]}}

# POLICY
{policy}

# FAILED EPISODES (mining tasks only)
{cases}

# CORRECT CALLS FROM SUCCESSFUL EPISODES
{contrast}
"""

REVISE = """Your check `{name}` was audited on the logged episodes of the mining tasks: it flagged {f} failed and
{s} successful episodes (needed: >= 2 failed and failed >= 3x successful). {why}
Revise it (same interface, same rules) or answer {{"checks": []}} to drop it. JSON only: {{"checks": [{{...}}]}}.
Current code:
{code}
{fp}"""


def deepseek(prompt):
    body = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": int(os.environ.get("MAX_TOKENS", "32000"))}).encode()
    req = urllib.request.Request("https://api.deepseek.com/chat/completions", body, {
        "Content-Type": "application/json", "Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                resp = json.load(r)
            break
        except Exception as e:  # noqa: BLE001
            if attempt == 3:
                raise
            print("retry", e, flush=True)
            time.sleep(2 ** (attempt + 1))
    text = resp["choices"][0]["message"]["content"]
    with open(LOG, "a") as f:
        f.write(json.dumps({"prompt_chars": len(prompt), "usage": resp.get("usage"), "text": text}) + "\n")
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0))["checks"] if m else []


def cases_for(eps, tasks, rng, n=24):
    fails = [e for e in eps if e["task"] in tasks and not e["ok"]]
    rng.shuffle(fails)
    seen, out = Counter(), []
    for e in fails:
        c = culprit(e)
        if not c or seen[e["task"]] >= 3:
            continue
        i, tc, why = c
        seen[e["task"]] += 1
        gold = "; ".join(f"{g['name']}({json.dumps(g['arguments'])})" for g in e["gold"] if g["name"] in WRITES
                         or g["name"] == "transfer_to_human_agents") or "(no writes)"
        out.append(f"## case {len(out) + 1} ({why})\n{render(e['msgs'], i)}\nCULPRIT: {tc['name']}({json.dumps(tc['arguments'])})\nGOLD WRITES: {gold}")
        if len(out) >= n:
            break
    return out


def contrast_for(eps, tasks, rng, n=8):
    succ = [e for e in eps if e["task"] in tasks and e["ok"]]
    rng.shuffle(succ)
    out, seen = [], Counter()
    for e in succ:
        for i, tc in calls(e):
            if tc["name"] in WRITES and seen[tc["name"]] < 2:
                seen[tc["name"]] += 1
                out.append(f"## correct {tc['name']}\n{render(e['msgs'], i, keep=4, width=300)}\nCALL: {tc['name']}({json.dumps(tc['arguments'])})")
                break
        if len(out) >= n:
            break
    return out


# ---------------------------------------------------------------- main

def evaluate(fn, eps, mine, held):
    by, errors, fp = audit(fn, eps)
    fm, sm = score(by, mine)
    fh, sh = score(by, held)
    return {"mine_fail": fm, "mine_success": sm, "held_fail": fh, "held_success": sh, "errors": errors,
            "held_fail_tasks": len({t for t in held if by[t]["fail"]}),
            "found": ok_ratio(fm, sm, 2), "transfers": ok_ratio(fm, sm, 2) and ok_ratio(fh, sh, 1)}, fp


def reaudit():
    """Re-score the stored final version of every mined check (no API calls), e.g. after fixing the sandbox."""
    out = json.load(open(OUT / "r1.json"))
    eps = load()
    tasks = sorted({e["task"] for e in eps}, key=int)
    folds = [set(f) for f in out["folds"]]
    for rec in out["mined"]:
        mine = folds[rec["fold"]]
        held = set(tasks) - mine
        for key in ("invalid", "mine_fail", "mine_success", "held_fail", "held_success", "errors", "held_fail_tasks"):
            rec.pop(key, None)
        try:
            res, _ = evaluate(compile_check(rec["versions"][-1]["code"]), eps, mine, held)
        except Exception as e:  # noqa: BLE001
            res = {"invalid": str(e)[:200], "found": False, "transfers": False}
        rec.update(res)
        print(rec["fold"], rec["name"], {x: rec.get(x) for x in ("mine_fail", "mine_success", "held_fail", "held_success", "errors", "found", "transfers")}, flush=True)
    out["reaudited"] = True
    (OUT / "r1.json").write_text(json.dumps(out, indent=1))
    report(out)


def main():
    if os.environ.get("REAUDIT"):
        return reaudit()
    OUT.mkdir(parents=True, exist_ok=True)
    eps = load()
    tasks = sorted({e["task"] for e in eps}, key=int)
    rng = random.Random(SEED)
    rng.shuffle(tasks)
    folds = [set(tasks[i::3]) for i in range(3)]
    policy = eps[0]["policy"]
    hand_scores = hand_score_factory(eps)
    out = {"episodes": len(eps), "model": MODEL, "seed": SEED, "folds": [sorted(f, key=int) for f in folds],
           "mined": [], "hand": []}

    only = os.environ.get("ONLY_FOLD")
    if only is not None:  # re-run one fold (e.g. after a truncated reasoner answer), keep the others
        prev = json.load(open(OUT / "r1.json"))
        out["mined"] = [r for r in prev["mined"] if r["fold"] != int(only)]
        out["hand"] = [r for r in prev["hand"] if r["fold"] != int(only)]
    for k, mine in enumerate(folds):
        if only is not None and k != int(only):
            cases_for(eps, mine, rng), contrast_for(eps, mine, rng)  # keep the sampling stream identical
            continue
        held = set(tasks) - mine
        # reference: hand-written checks on the same split
        for name in ["cheapest_not_min", "pax_dob_mismatch", "substitute_book", "transfer_pending"]:
            out["hand"].append({"fold": k, "name": name, **hand_scores[name](mine, held)})

        cases = cases_for(eps, mine, rng)
        contrast = contrast_for(eps, mine, rng)
        print(f"fold {k}: {len(cases)} cases", flush=True)
        proposals = deepseek(PROMPT.format(policy=policy, cases="\n\n".join(cases), contrast="\n\n".join(contrast)))
        for p in proposals:
            rec = {"fold": k, "name": p.get("name"), "description": p.get("description"), "clause": p.get("clause"),
                   "versions": []}
            code = p.get("code", "")
            for rnd in range(2):
                try:
                    fn = compile_check(code)
                    res, fp = evaluate(fn, eps, mine, held)
                except Exception as e:  # noqa: BLE001
                    res, fp = {"invalid": str(e)[:200], "found": False, "transfers": False}, []
                rec["versions"].append({"code": code, **res})
                if res.get("found") or rnd == 1:
                    break
                why = res.get("invalid") or ""
                fps = ("A successful episode it flagged:\n" + fp[0]) if fp else ""
                rev = deepseek(REVISE.format(name=rec["name"], f=res.get("mine_fail", 0), s=res.get("mine_success", 0),
                                             why=why, code=code, fp=fps))
                if not rev:
                    break
                code = rev[0].get("code", "")
            rec.update({k2: v for k2, v in rec["versions"][-1].items() if k2 != "code"})
            out["mined"].append(rec)
            print(k, rec["name"], {x: rec.get(x) for x in ("mine_fail", "mine_success", "held_fail", "held_success", "found", "transfers")}, flush=True)
        (OUT / "r1.json").write_text(json.dumps(out, indent=1))
    out["mined"].sort(key=lambda r: r["fold"])
    out["hand"].sort(key=lambda r: r["fold"])
    (OUT / "r1.json").write_text(json.dumps(out, indent=1))
    report(out)


def hand_score_factory(eps):
    fires = defaultdict(lambda: defaultdict(Counter))
    for ep in eps:
        for r in set(ep["hand"]):
            fires[r][ep["task"]]["fail" if not ep["ok"] else "success"] += 1

    def make(name):
        def f(mine, held):
            by = fires[name]
            fm, sm = score(by, mine)
            fh, sh = score(by, held)
            return {"mine_fail": fm, "mine_success": sm, "held_fail": fh, "held_success": sh,
                    "found": ok_ratio(fm, sm, 2), "transfers": ok_ratio(fm, sm, 2) and ok_ratio(fh, sh, 1)}
        return f
    return defaultdict(lambda: None, {n: make(n) for n in fires})


def report(out):
    lines = ["# RSI R1 — automatically mined checks vs hand-written, 3-fold task split (airline)", "",
             f"{out['episodes']} logged episodes, miner `{out['model']}`, split seed {out['seed']}. "
             "found = mining fold fail ≥ 2 and fail ≥ 3× success; transfers = also held-out fail ≥ 1 and ≥ 3× success.", "",
             "| fold | source | check | mine fail/succ | held fail/succ | held failed tasks | found | transfers |",
             "|---|---|---|---|---|---|---|---|"]
    for r in out["hand"]:
        lines.append(f"| {r['fold']} | hand | {r['name']} | {r['mine_fail']}/{r['mine_success']} | {r['held_fail']}/{r['held_success']} | – | {r['found']} | {r['transfers']} |")
    for r in out["mined"]:
        if "invalid" in r:
            lines.append(f"| {r['fold']} | mined | {r['name']} | invalid | | | False | False |")
            continue
        lines.append(f"| {r['fold']} | mined | {r['name']} | {r['mine_fail']}/{r['mine_success']} | {r['held_fail']}/{r['held_success']} | {r['held_fail_tasks']} | {r['found']} | {r['transfers']} |")
    n_found = sum(bool(r.get("found")) for r in out["mined"])
    n_tr = sum(bool(r.get("transfers")) for r in out["mined"])
    h_found = sum(bool(r.get("found")) for r in out["hand"])
    h_tr = sum(bool(r.get("transfers")) for r in out["hand"])
    lines += ["", f"Mined: {len(out['mined'])} proposals, {n_found} found, {n_tr} transfer. "
              f"Hand-written (4 checks × 3 folds): {h_found} found, {h_tr} transfer."]
    (OUT / "R1.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
