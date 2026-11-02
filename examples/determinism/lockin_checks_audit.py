"""Zero-cost audit of two checks suggested by the lock-in window analysis (2026-11-02).

slot_provenance: a book_reservation with insurance="yes" or total_baggages > 0 although no user message in the
    conversation mentions insurance / bags (attribute carried over from the old reservation or invented).
unfinished_cancel: the agent booked a new reservation and, earlier, proposed cancelling reservation X, but X was
    never cancelled by the end of the episode.
Counts fires in failed vs successful episodes across all logged airline runs.
"""
import json, re
from collections import Counter
from pathlib import Path

RES = re.compile(r"\b[A-Z0-9]{6}\b")
ok = lambda s: ((s.get("reward_info") or {}).get("reward") or 0) >= 0.999


def calls(M):
    for i, m in enumerate(M):
        if m["role"] == "assistant":
            for t in m.get("tool_calls") or []:
                yield i, t["name"], t.get("arguments") or {}


def slot_provenance(M):
    hits = []
    for i, n, a in calls(M):
        if n != "book_reservation":
            continue
        users = " ".join((m.get("content") or "") for m in M[:i] if m["role"] == "user").lower()
        neg = lambda w: re.search(r"(\bno\b|n't|\bnot\b|without|skip)[^.?!]{0,40}" + w, users)
        if a.get("insurance") == "yes" and (neg("insur") or "insur" not in users):
            hits.append("insurance")
        if (a.get("total_baggages") or 0) > 0 and (neg("bag") or not re.search(r"\bbag", users)):
            hits.append("bags")
    return hits


def unfinished_cancel(M):
    cs = [(i, n, a) for i, n, a in calls(M)]
    if not any(n == "book_reservation" for _, n, _ in cs):
        return []
    cancelled = {a.get("reservation_id") for _, n, a in cs if n == "cancel_reservation"}
    known = {a.get("reservation_id") for _, n, a in cs if n == "get_reservation_details"}
    proposed = set()
    for m in M:
        if m["role"] == "assistant" and not m.get("tool_calls"):
            for sent in re.split(r"(?<=[.!?\n])", m.get("content") or ""):
                if re.search(r"\bcancel", sent, re.I) and re.search(r"\bbook|new reservation|rebook", m.get("content") or "", re.I) and not re.search(r"cannot|can't|not (be )?(cancel|eligible)|unable", sent, re.I):
                    proposed |= set(RES.findall(sent)) & known
    return sorted(proposed - cancelled)


def main():
    tot = Counter()
    by = {"slot_provenance": Counter(), "unfinished_cancel": Counter()}
    tasks = {"slot_provenance": Counter(), "unfinished_cancel": Counter()}
    for d in sorted(Path("reports/anchor").glob("airline-*")):
        for s in json.load(open(d / "results.json"))["simulations"]:
            k = "success" if ok(s) else "fail"
            tot[k] += 1
            for name, fn in (("slot_provenance", slot_provenance), ("unfinished_cancel", unfinished_cancel)):
                if fn(s["messages"]):
                    by[name][k] += 1
                    tasks[name][(str(s["task_id"]), k)] += 1
    out = {"episodes": dict(tot), "fires": {n: dict(c) for n, c in by.items()},
           "by_task": {n: {f"{t}:{k}": v for (t, k), v in sorted(c.items())} for n, c in tasks.items()}}
    Path("reports/rsi/lockin_checks_audit.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


main()
