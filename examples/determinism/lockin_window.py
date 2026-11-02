"""Lock-in window analysis (zero cost, 2026-11-02).

For E4 flaky failures whose midpoint continuation succeeded but proposal-turn continuation failed (PONR + proposal-gate
control arms), print the original failed trajectory and the successful continuation side by side from the midpoint,
up to the decisive write, so the first point where they part can be read.
"""
import json, sys
from pathlib import Path

ok = lambda s: ((s.get("reward_info") or {}).get("reward") or 0) >= 0.999
pm = json.loads(Path("reports/rsi/ponr-replay/replay_tasks.json").read_text())
P = {s["task_id"]: s for s in json.load(open("reports/rsi/ponr-replay/control.json"))["simulations"]}
G = {s["task_id"]: s for s in json.load(open("reports/rsi/pg-replay/control.json"))["simulations"]}
orig = {}


def short(m, n=260):
    if m.get("tool_calls"):
        return "CALL " + "; ".join(f"{t['name']}({json.dumps(t.get('arguments'))[:160]})" for t in m["tool_calls"])
    c = (m.get("content") or "").replace("\n", " ")
    return (c[:n] + "…") if len(c) > n else c


def main():
    cases = []
    for tid, m in pm.items():
        if m["cut"] != "mid":
            continue
        base = tid[:-4]
        g = G.get(base + "_proposal")
        if not (ok(P[tid]) and g is not None and not ok(g)):
            continue
        run = m["run"]
        if run not in orig:
            orig[run] = {(str(s["task_id"]), s["trial"]): s for s in
                         json.load(open(f"reports/anchor/airline-{run}/results.json"))["simulations"]}
        F = orig[run][(m["task"], m["trial"])]["messages"]
        S = P[tid]["messages"]
        cut, w = m["first_msg_index"], m["write_index"]
        print(f"\n===== {base}  mid cut {cut}, failed write at {w}")
        i = cut
        while i < max(w + 1, cut + 1) and i < len(F):
            f, s = F[i], S[i] if i < len(S) else {}
            same = short(f) == short(s)
            if f.get("role") != "tool" or not same:
                print(f"[{i}] {'=' if same else '≠'} {f['role']:9s} F: {short(f) if f.get('role')!='tool' else short(f,120)}")
                if not same:
                    print(f"      {s.get('role','-'):9s} S: {short(s) if s.get('role')!='tool' else short(s,120)}")
            i += 1
        cases.append(base)
    print(len(cases), "cases")


main()
