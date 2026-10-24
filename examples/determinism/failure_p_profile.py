"""Where and how Jev's confidence p_max differs between failed and successful episodes.

Zero API cost: reads reports/anchor/airline-{veto,hint,deliberate,reasoner}/results.json.
Breakdowns: overall distribution; relative position in the dialogue; action actually taken (read tool / write tool /
message / transfer); task type (always-pass / flaky / always-fail); and a window around the first divergence between
a failed and a successful trial of the same task. Also whether the LLM followed Jev's top choice at low-p steps.
"""
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import trajectory_risk as tr  # noqa: E402

OUT = Path(os.environ.get("OUT_DIR", "reports/determinism"))
WRITE = {"tool:" + x for x in ["book_reservation", "cancel_reservation", "update_reservation_flights",
                               "update_reservation_passengers", "update_reservation_baggages", "send_certificate"]}


def kind(a):
    if a == "message":
        return "message"
    if a == "tool:transfer_to_human_agents":
        return "transfer"
    return "write" if a in WRITE else "read"


def summ(ps):
    if not ps:
        return None
    s = sorted(ps)
    return {"n": len(ps), "mean": round(sum(ps) / len(ps), 3), "median": round(s[len(s) // 2], 3),
            "p<0.6": round(sum(p < 0.6 for p in ps) / len(ps), 3), "p<0.8": round(sum(p < 0.8 for p in ps) / len(ps), 3),
            "p>=0.95": round(sum(p >= 0.95 for p in ps) / len(ps), 3)}


def main():
    data = {r: tr.load(r) for r in tr.RUNS_WITH_JEV}
    rep = {}
    groups = defaultdict(list)          # outcome -> p list
    pos = defaultdict(list)             # (outcome, decile) -> p
    act = defaultdict(list)             # (outcome, kind) -> p
    ttype = defaultdict(list)           # (task type, outcome) -> p
    follow = defaultdict(lambda: [0, 0])  # (outcome, p bin) -> [followed jev top, n]
    lowrun = defaultdict(list)          # outcome -> longest run of consecutive p<0.8
    first_low = defaultdict(list)       # outcome -> relative position of first p<0.8
    for r, eps in data.items():
        cnt = defaultdict(int); n = defaultdict(int)
        for e in eps:
            cnt[e["task"]] += e["success"]; n[e["task"]] += 1
        for e in eps:
            o = "success" if e["success"] else "failure"
            c = cnt[e["task"]]
            tt = "always_pass" if c == n[e["task"]] else "always_fail" if c == 0 else "flaky"
            st = [s for s in e["steps"] if s["p"] is not None]
            T = len(st)
            run = best = 0; fl = None
            for t, s in enumerate(st):
                p = s["p"]
                groups[o].append(p)
                pos[(o, min(4, int(5 * t / T)))].append(p)
                act[(o, kind(s["act"]))].append(p)
                ttype[(tt, o)].append(p)
                b = "<0.6" if p < 0.6 else "0.6-0.8" if p < 0.8 else "0.8-0.95" if p < 0.95 else ">=0.95"
                follow[(o, b)][0] += s["top"] == s["act"]; follow[(o, b)][1] += 1
                run = run + 1 if p < 0.8 else 0; best = max(best, run)
                if p < 0.8 and fl is None:
                    fl = t / T
            lowrun[o].append(best)
            if fl is not None:
                first_low[o].append(fl)
    rep["overall"] = {o: summ(v) for o, v in groups.items()}
    rep["by_position_quintile"] = {f"{o}|q{q + 1}": summ(pos[(o, q)]) for o in ("success", "failure") for q in range(5)}
    rep["by_action_taken"] = {f"{o}|{k}": summ(act[(o, k)]) for o in ("success", "failure")
                              for k in ("read", "write", "message", "transfer")}
    rep["by_task_type"] = {f"{t}|{o}": summ(v) for (t, o), v in sorted(ttype.items())}
    rep["llm_follows_jev_top"] = {f"{o}|{b}": round(f / m, 3) for (o, b), (f, m) in sorted(follow.items())}
    rep["longest_low_run_mean"] = {o: round(sum(v) / len(v), 2) for o, v in lowrun.items()}
    rep["first_low_rel_pos_mean"] = {o: round(sum(v) / len(v), 3) for o, v in first_low.items()}
    # window around first divergence: failed vs successful trial of the same task
    win = defaultdict(lambda: defaultdict(list))
    kinds = defaultdict(lambda: defaultdict(int))
    for r, eps in data.items():
        by = defaultdict(list)
        for e in eps:
            by[e["task"]].append(e)
        for v in by.values():
            for a in v:
                for b in v:
                    if a["success"] or not b["success"]:
                        continue  # a = failed, b = succeeded
                    A, B = a["steps"], b["steps"]
                    t0 = next((t for t in range(min(len(A), len(B))) if A[t]["act"] != B[t]["act"]), None)
                    if t0 is None:
                        continue
                    kinds["failed_took"][kind(A[t0]["act"])] += 1
                    kinds["success_took"][kind(B[t0]["act"])] += 1
                    kinds["jev_top_equals"]["failed" if A[t0]["top"] == A[t0]["act"] else
                                            "success" if A[t0]["top"] == B[t0]["act"] else "neither"] += 1
                    for d in range(-3, 6):
                        for lab, S in (("failed", A), ("success", B)):
                            t = t0 + d
                            if 0 <= t < len(S) and S[t]["p"] is not None:
                                win[lab][d].append(S[t]["p"])
    rep["divergence_window"] = {lab: {str(d): summ(v) for d, v in sorted(w.items())} for lab, w in win.items()}
    rep["divergence_actions"] = {k: dict(v) for k, v in kinds.items()}
    (OUT / "failure_p_profile.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False))
    print(json.dumps(rep, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
