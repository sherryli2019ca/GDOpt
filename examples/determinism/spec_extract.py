"""Step 1 of the early-intervention plan (2026-11-02): does a failed trial already differ at the level of the
user's structured request ("spec")?

For every trial of E4's 11 flaky airline tasks (8 trials: E4 run 1 + run 2), deepseek-chat (T=0, JSON mode) extracts a
spec from the USER turns only, at two points: the opening (first 2 user turns) and just before the decisive write
(all user turns before the first write / transfer). Then, per field, the failed trials' specs are compared with the
majority value among the successful trials of the same task.
Output: reports/rsi/spec_extract.json (+ cache spec_cache.json), summary printed.
"""
import json, os, re, sys, hashlib
from collections import Counter
from pathlib import Path
import requests

RUNS = ["deliberate_reasoner_rules_consistency"] + [f"e4_mined-fold{k}" for k in range(3)]
TASKS = ["6", "8", "14", "15", "16", "23", "29", "33", "42", "44", "45"]
WRITES = {"cancel_reservation", "update_reservation_flights", "update_reservation_baggages",
          "update_reservation_passengers", "book_reservation", "send_certificate", "transfer_to_human_agents"}
FIELDS = ["intents", "reservation_ids", "origin", "destination", "dates", "cabin", "flight_criterion",
          "time_constraints", "passengers", "bags", "insurance", "payment_preference", "refund_preference", "other"]
PROMPT = """You read the customer's side of an airline customer-service chat and write down, as a structured spec, what
the customer wants. Use ONLY what the customer said. Use null for anything not stated. Keep values short and normalized
(lowercase; airports as IATA codes; dates as YYYY-MM-DD; reservation ids as given).
Fields: intents (list of: cancel, change_flight, change_cabin, book, add_bags, change_passenger, compensation, info,
other), reservation_ids (list), origin, destination, dates (list), cabin, flight_criterion (e.g. cheapest, nonstop,
specific flight numbers), time_constraints, passengers (list of names or a count), bags (number or "none"),
insurance ("yes"/"no"), payment_preference, refund_preference, other (short list of other explicit wishes).
Return a JSON object with exactly these keys.

Customer turns:
"""
CACHE = Path("reports/rsi/spec_cache.json")
cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
cost = {"in": 0, "out": 0, "hit": 0}


def extract(text):
    key = hashlib.sha1(text.encode()).hexdigest()
    if key in cache:
        return cache[key]
    r = requests.post("https://api.deepseek.com/chat/completions", timeout=120,
                      headers={"Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}"},
                      json={"model": "deepseek-chat", "temperature": 0, "response_format": {"type": "json_object"},
                            "messages": [{"role": "user", "content": PROMPT + text}]}).json()
    u = r.get("usage", {})
    cost["in"] += u.get("prompt_tokens", 0); cost["out"] += u.get("completion_tokens", 0)
    cache[key] = json.loads(r["choices"][0]["message"]["content"])
    return cache[key]


def norm(v):
    if v is None or v == [] or v == "":
        return None
    if isinstance(v, list):
        return tuple(sorted(norm(x) or "" for x in v))
    return re.sub(r"\s+", " ", str(v).strip().lower())


def main():
    ok = lambda s: ((s.get("reward_info") or {}).get("reward") or 0) >= 0.999
    eps = []
    for run in RUNS:
        for s in json.load(open(f"reports/anchor/airline-{run}/results.json"))["simulations"]:
            if str(s["task_id"]) not in TASKS:
                continue
            M = s["messages"]
            w = next((i for i, m in enumerate(M) if m["role"] == "assistant"
                      and any(t["name"] in WRITES for t in m.get("tool_calls") or [])), len(M))
            users = [m.get("content") or "" for m in M[:w] if m["role"] == "user"]
            eps.append({"task": str(s["task_id"]), "run": run, "trial": s["trial"], "success": ok(s),
                        "open": extract("\n---\n".join(users[:2])), "pre_write": extract("\n---\n".join(users))})
            CACHE.write_text(json.dumps(cache))
    rep = {"points": {}}
    for point in ("open", "pre_write"):
        diff_fields, fails_diff, per_task = Counter(), 0, {}
        for t in TASKS:
            E = [e for e in eps if e["task"] == t]
            S = [e for e in E if e["success"]]
            F = [e for e in E if not e["success"]]
            maj = {f: Counter(norm(e[point].get(f)) for e in S).most_common(1)[0][0] if S else None for f in FIELDS}
            # how often successes themselves deviate from their majority (noise floor)
            s_dev = sum(any(norm(e[point].get(f)) != maj[f] for f in FIELDS) for e in S)
            rows = []
            for e in F:
                d = [f for f in FIELDS if norm(e[point].get(f)) != maj[f]]
                diff_fields.update(d)
                fails_diff += bool(d)
                rows.append({"run": e["run"], "trial": e["trial"], "differs": d,
                             "values": {f: e[point].get(f) for f in d}})
            per_task[t] = {"n_success": len(S), "n_fail": len(F), "success_deviating": s_dev,
                           "majority": {f: maj[f] for f in FIELDS}, "failures": rows}
        nf = sum(1 for e in eps if not e["success"])
        rep["points"][point] = {"failures": nf, "failures_with_any_diff": fails_diff,
                                "field_counts": dict(diff_fields.most_common()), "per_task": per_task}
    rep["episodes"] = len(eps)
    rep["specs"] = eps
    # discriminative view: leave-one-out majority among successes, key fields only, failures vs successes
    KEY = [f for f in FIELDS if f not in ("other", "time_constraints", "refund_preference")]
    rep["loo"] = {}
    for point in ("open", "pre_write"):
        rate = {"fail": Counter(), "success": Counter()}
        n = Counter()
        anyd = Counter()
        for t in TASKS:
            E = [e for e in eps if e["task"] == t]
            S = [e for e in E if e["success"]]
            for e in E:
                ref = [x for x in S if x is not e]
                if not ref:
                    continue
                k = "success" if e["success"] else "fail"
                n[k] += 1
                d = [f for f in KEY if norm(e[point].get(f)) != Counter(norm(x[point].get(f)) for x in ref).most_common(1)[0][0]]
                rate[k].update(d)
                anyd[k] += bool(d)
        rep["loo"][point] = {"n": dict(n), "any_key_field_differs": {k: round(anyd[k] / n[k], 2) for k in n},
                             "field_rate": {f: {k: round(rate[k][f] / n[k], 2) for k in n} for f in KEY}}
    rep["tokens"] = cost
    Path("reports/rsi/spec_extract.json").write_text(json.dumps(rep, indent=1, default=list))
    for p, v in rep["points"].items():
        print(p, v["failures_with_any_diff"], "/", v["failures"], v["field_counts"])
        print("  success deviating:", {t: (x["success_deviating"], x["n_success"]) for t, x in v["per_task"].items()})
    print(json.dumps(rep["loo"], indent=1))
    print(cost)


main()
