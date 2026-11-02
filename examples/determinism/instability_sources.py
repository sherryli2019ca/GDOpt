"""Where does trial-to-trial instability come from?  Zero-cost decomposition on the logged airline 50x4 runs.

(A) Origin of divergence.  For every pair of trials of the same task in the same run, walk both message lists in
lockstep and find the first message that differs.  Classify it by who produced it:
  user   - the user simulator said something different (text)
  agent  - the agent differs: tool vs message, different tool, same tool different arguments, or message text only
  tool   - an environment response differs (should not happen: the environment is deterministic)
Also find the first ACTION-level divergence (tool call vs message, tool name or arguments) and report who diverged
first before it (wording drift on either side precedes most action forks).  Split by pair outcome (both pass / both
fail / mixed).
(B) Failure taxonomy.  For every failed episode, from τ²'s own action checks and the E1 clause predicates:
forbidden write (a certified rule fires), wrong arguments on a gold write, gold write missing, extra write not in the
gold actions, transfer to a human that the gold does not contain, communicate-only failure, max-steps / error
termination, and the rest.

Reads reports/anchor/airline-*/results.json. Run from repo root. Env: ANCHOR_DIR, OUT_DIR.
"""
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from gdopt.adapters.tau2_rules import CERTIFIED, PolicyFacts  # noqa: E402

ANCHOR = Path(os.environ.get("ANCHOR_DIR", "reports/anchor"))
OUT = Path(os.environ.get("OUT_DIR", "reports/determinism"))
RUNS = ["none", "veto", "hint", "checklist", "deliberate", "reasoner", "deliberate_all", "deliberate_reasoner"]
WRITES = {"cancel_reservation", "update_reservation_flights", "update_reservation_baggages", "update_reservation_passengers",
          "book_reservation", "send_certificate"}


def norm(t):
    return " ".join((t or "").lower().split())


def sig(m):
    """Comparable signature of a message: (role, kind, detail)."""
    role = m.get("role")
    tcs = m.get("tool_calls") or []
    if role == "assistant":
        if tcs:
            return ("assistant", "tool", tuple((tc["name"], json.dumps(tc.get("arguments"), sort_keys=True)) for tc in tcs))
        return ("assistant", "message", norm(m.get("content")))
    if role == "user":
        return ("user", "tool" if tcs else "message", norm(m.get("content")))
    return (role, "content", norm(m.get("content")))


def agent_kind(a, b):
    if a[1] != b[1]:
        return "tool_vs_message"
    if a[1] == "message":
        return "message_text"
    na, nb = [x[0] for x in a[2]], [x[0] for x in b[2]]
    return "same_tool_diff_args" if na == nb else "different_tool"


def first_divergence(A, B):
    for i in range(min(len(A), len(B))):
        sa, sb = sig(A[i]), sig(B[i])
        if sa != sb:
            if sa[0] != sb[0]:
                return i, "turn_order", None
            if sa[0] == "assistant":
                return i, "agent", agent_kind(sa, sb)
            return i, sa[0], None
    return None, "identical", None


def first_action_divergence(A, B):
    """First assistant step whose ACTION (tool name+args or 'message') differs, comparing the k-th assistant steps."""
    def acts(M):
        out = []
        for i, m in enumerate(M):
            if m.get("role") == "assistant":
                s = sig(m)
                out.append((i, s[2] if s[1] == "tool" else "message"))
        return out
    a, b = acts(A), acts(B)
    for k in range(min(len(a), len(b))):
        if a[k][1] != b[k][1]:
            return k, a[k][0], b[k][0]
    return None


def failure_type(s):
    ri = s.get("reward_info") or {}
    br = ri.get("reward_breakdown") or {}
    checks = ri.get("action_checks") or []
    gold = [c["action"] for c in checks]
    gold_writes = [g for g in gold if g["name"] in WRITES]
    gold_names = Counter(g["name"] for g in gold)
    unmatched_writes = [c["action"] for c in checks if c["action"]["name"] in WRITES and not c.get("action_match")]
    calls = [tc for m in s["messages"] if m.get("role") == "assistant" for tc in (m.get("tool_calls") or [])]
    made = Counter(tc["name"] for tc in calls)
    facts, forbidden = PolicyFacts(), False
    for m in s["messages"]:
        if m.get("role") == "assistant":
            for tc in m.get("tool_calls") or []:
                forbidden |= any(r in CERTIFIED for r, _ in facts.check(tc["name"], tc.get("arguments") or {}))
        facts.observe(m)
    term = s.get("termination_reason")
    types = []
    if term in ("max_steps", "too_many_errors", "agent_error", "user_error"):
        types.append("termination:" + str(term))
    if forbidden:
        types.append("forbidden_write")
    if any(made[g["name"]] for g in unmatched_writes):
        types.append("wrong_args_on_gold_write")
    if any(not made[g["name"]] for g in unmatched_writes):
        types.append("missing_gold_write")
    if any(made[n] > gold_names.get(n, 0) for n in WRITES if made[n]):
        types.append("extra_write")
    if made["transfer_to_human_agents"] and not gold_names.get("transfer_to_human_agents"):
        types.append("unexpected_transfer")
    if not types and br.get("COMMUNICATE", 1.0) < 1 and br.get("DB", 1.0) >= 1:
        types.append("communicate_only")
    if not types and br.get("DB", 1.0) < 1:
        types.append("db_mismatch_other")
    if not types and not gold_writes and made.keys() & WRITES:
        types.append("extra_write")
    return types or ["other"], bool(gold_writes)


def main():
    origin = defaultdict(Counter)
    agent_kinds = defaultdict(Counter)
    act_prior = defaultdict(Counter)
    act_kind = defaultdict(Counter)
    pos = defaultdict(list)
    fail = Counter()
    fail_primary = Counter()
    n_fail = 0
    for run in RUNS:
        p = ANCHOR / f"airline-{run}" / "results.json"
        if not p.exists():
            continue
        sims = json.load(open(p))["simulations"]
        by = defaultdict(list)
        for s in sims:
            ok = ((s.get("reward_info") or {}).get("reward") or 0.0) >= 0.999
            by[str(s["task_id"])].append((s, ok))
            if not ok:
                n_fail += 1
                types, _ = failure_type(s)
                fail.update(types)
                order = ["termination:max_steps", "forbidden_write", "unexpected_transfer", "wrong_args_on_gold_write",
                         "extra_write", "missing_gold_write", "communicate_only", "db_mismatch_other"]
                fail_primary[next((t for t in order if t in types), types[0])] += 1
        for eps in by.values():
            for i in range(len(eps)):
                for j in range(i + 1, len(eps)):
                    (sa, oa), (sb, ob) = eps[i], eps[j]
                    grp = "mixed" if oa != ob else ("both_pass" if oa else "both_fail")
                    A, B = sa["messages"], sb["messages"]
                    k, who, kind = first_divergence(A, B)
                    origin[grp][who] += 1
                    if who == "agent":
                        agent_kinds[grp][kind] += 1
                    if k is not None:
                        pos[grp].append(k)
                    fa = first_action_divergence(A, B)
                    if fa is None:
                        act_prior[grp]["no_action_divergence"] += 1
                        continue
                    _, ia, ib = fa
                    # who diverged first strictly before this action fork?
                    prior = "none (fork from identical context)"
                    if k is not None and k < min(ia, ib):
                        prior = "user wording first" if who == "user" else ("agent wording first" if who == "agent" else who)
                    act_prior[grp][prior] += 1
                    act_kind[grp][agent_kind(sig(A[ia]), sig(B[ib]))] += 1
    out = {"pairs": {g: sum(c.values()) for g, c in origin.items()}, "first_divergence_origin": origin,
           "first_divergence_agent_kind": agent_kinds, "first_divergence_index_median":
           {g: sorted(v)[len(v) // 2] for g, v in pos.items()},
           "action_fork_preceded_by": act_prior, "action_fork_kind": act_kind,
           "failed_episodes": n_fail, "failure_types_multi": fail, "failure_primary": fail_primary}
    print(json.dumps(out, indent=1, default=dict))
    (OUT / "instability_sources.json").write_text(json.dumps(out, indent=1, default=dict))


if __name__ == "__main__":
    main()
