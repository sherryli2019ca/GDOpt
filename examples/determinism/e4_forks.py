"""Where do the remaining E4 failures fork from success?  Zero-cost analysis of the two E4 airline runs (8 trials/task).

For every failed trial of a flaky task, pick the successful trial of the same task with the longest common message
prefix and report: who diverged first (user simulator or agent), the first ACTION divergence (failed branch vs success
branch), the Jev p_max and generator at that step in the failed trial (was it already routed to the reasoner?), and
the τ² failure type.  Always-failing tasks get the failure type only.

Run from repo root; writes reports/rsi/e4_forks.json.
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import instability_sources as I  # noqa: E402

RUNS = ["deliberate_reasoner_rules_consistency"] + [f"e4_mined-fold{k}" for k in range(3)]


def act(m):
    s = I.sig(m)
    return "message" if s[1] == "message" else "+".join(x[0] for x in s[2])


def anchor(m):
    g = ((m.get("raw_data") or {}).get("gdopt") or {})
    a = g.get("anchor") or {}
    return a.get("jev_p"), g.get("generator") or g.get("tier"), a


DECISIVE = I.WRITES | {"transfer_to_human_agents"}


def writes(M):
    """(message index, name, args) of every write / transfer call, in order."""
    return [(i, tc["name"], json.dumps(tc.get("arguments"), sort_keys=True)) for i, m in enumerate(M) if m.get("role") == "assistant"
            for tc in (m.get("tool_calls") or []) if tc["name"] in DECISIVE]


def decisive(f, s):
    """First write-level difference: failed trial's write (or None = it stopped earlier), success trial's write."""
    a, b = writes(f), writes(s)
    for k in range(max(len(a), len(b))):
        x = a[k] if k < len(a) else None
        y = b[k] if k < len(b) else None
        if x is None or y is None or x[1:] != y[1:]:
            return x, y
    return None, None


def common_prefix(A, B):
    n = 0
    for x, y in zip(A, B):
        if I.sig(x) != I.sig(y):
            break
        n += 1
    return n


def main():
    sims = defaultdict(list)
    for run in RUNS:
        for s in json.load(open(f"reports/anchor/airline-{run}/results.json"))["simulations"]:
            s["_ok"] = ((s.get("reward_info") or {}).get("reward") or 0) >= 0.999
            sims[str(s["task_id"])].append(s)
    out = {"failures": [], "summary": {}}
    for t, ss in sorted(sims.items(), key=lambda x: int(x[0])):
        succ = [s for s in ss if s["_ok"]]
        for f in (s for s in ss if not s["_ok"]):
            ftype, _ = I.failure_type(f)
            rec = {"task": t, "flaky": bool(succ), "types": ftype, "n_success": len(succ), "n": len(ss)}
            if succ:
                best = max(succ, key=lambda s: common_prefix(f["messages"], s["messages"]))
                i, origin, kind = I.first_divergence(f["messages"], best["messages"])
                ad = I.first_action_divergence(f["messages"], best["messages"])
                rec.update(first_divergence_index=i, origin=origin, agent_kind=kind)
                if ad:
                    k, fi, si = ad
                    p, gen, a = anchor(f["messages"][fi])
                    rec.update(action_step=k, failed_action=act(f["messages"][fi]), success_action=act(best["messages"][si]),
                               jev_p=p, uncertain=(p is not None and p < 0.8), generator=a.get("generator") or gen,
                               consistency=bool(a.get("consistency")),
                               user_before=f["messages"][fi - 1]["content"][:300] if fi and f["messages"][fi - 1].get("role") == "user" else None)
                x, y = decisive(f["messages"], best["messages"])
                if x is not None:
                    p, gen, a = anchor(f["messages"][x[0]])
                    rec.update(decisive_failed=x[1], decisive_success=y[1] if y else None, decisive_same_tool=bool(y) and x[1] == y[1],
                               decisive_jev_p=p, decisive_uncertain=(p is not None and p < 0.8),
                               decisive_generator=a.get("generator"), decisive_consistency=bool(a.get("consistency")))
                else:
                    rec.update(decisive_failed=None, decisive_success=y[1] if y else None)
            out["failures"].append(rec)
    F = out["failures"]
    fl = [r for r in F if r["flaky"]]
    out["summary"] = {
        "failures": len(F), "flaky_failures": len(fl), "always_fail_failures": len(F) - len(fl),
        "origin": dict(Counter(r.get("origin") for r in fl)),
        "fork_uncertain": dict(Counter(r.get("uncertain") for r in fl)),
        "fork_kind": dict(Counter((r.get("failed_action") == "message", r.get("success_action") == "message") for r in fl if "failed_action" in r)),
        "decisive_kind": dict(Counter(("omitted" if r.get("decisive_failed") is None else "same_tool_diff_args" if r.get("decisive_same_tool")
                                       else "extra" if r.get("decisive_success") is None else "different_write") for r in fl)),
        "decisive_uncertain": dict(Counter(r.get("decisive_uncertain") for r in fl if r.get("decisive_failed"))),
        "decisive_reasoner": dict(Counter(str(r.get("decisive_generator")) for r in fl if r.get("decisive_failed"))),
        "decisive_pairs": dict(Counter(f"{r.get('decisive_failed')} | {r.get('decisive_success')}" for r in fl).most_common(12)),
        "types_flaky": dict(Counter(x for r in fl for x in r["types"])),
        "types_always": dict(Counter(x for r in F if not r["flaky"] for x in r["types"])),
        "fork_pairs": dict(Counter(f"{r.get('failed_action')} | {r.get('success_action')}" for r in fl if "failed_action" in r).most_common(15)),
    }
    out["summary"]["fork_kind"] = {f"failed_msg={a},success_msg={b}": v for (a, b), v in out["summary"]["fork_kind"].items()}
    Path("reports/rsi/e4_forks.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out["summary"], indent=1))


if __name__ == "__main__":
    main()
