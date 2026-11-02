"""Cut points right before the agent's proposal turn (2026-11-02).

For every entry of ``reports/rsi/wg_flagged.json`` (E4 flaky tasks: decisive wrong writes of failed trials, and the
matching writes of successful trials as harm controls), the cut is the last assistant text message (no tool calls)
before the decisive write, i.e. the turn in which the agent puts the plan to the user. Output
``reports/rsi/proposal_flagged.json`` in the replay format (``first_msg_index`` = cut, ``cut = "proposal"``).
"""
import json
from pathlib import Path

src = json.loads(Path("reports/rsi/wg_flagged.json").read_text())["flagged"]
sims = {}
out, gaps = [], []
for x in src:
    run = x["run"]
    if run not in sims:
        sims[run] = {(str(s["task_id"]), s["trial"]): s for s in
                     json.load(open(f"reports/anchor/airline-{run}/results.json"))["simulations"]}
    msgs = sims[run][(x["task"], x["trial"])]["messages"]
    w = x["first_msg_index"]
    cut = next((i for i in range(w - 1, -1, -1) if msgs[i]["role"] == "assistant" and not msgs[i].get("tool_calls")
                and (msgs[i].get("content") or "").strip()), None)
    if cut is None:
        continue
    gaps.append(w - cut)
    out.append({**x, "first_msg_index": cut, "write_index": w, "cut": "proposal", "rules": ["cut_proposal"],
                "proposal": msgs[cut]["content"][:400]})
Path("reports/rsi/proposal_flagged.json").write_text(json.dumps({"flagged": out}, indent=1))
print(len(out), "entries; fail", sum(not x["success"] for x in out), "; write - cut:",
      {g: gaps.count(g) for g in sorted(set(gaps))})
