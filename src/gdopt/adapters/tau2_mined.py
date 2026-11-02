"""Checks mined automatically from failed trajectories (RSI round R1), used online as soft review triggers.

A mined check is the Python predicate ``check(call, history) -> bool`` proposed by the miner
(``examples/determinism/rsi_mine.py``) and kept only if it passed the audit on its mining fold and transferred to the
held-out tasks.  ``MinedChecker`` runs every loaded predicate on each tool call of a proposed assistant message; a fire
is "soft": the agent regenerates the step with the reasoner and a review note built from the check's description and
clause (the same path as the soft consistency checks in ``tau2_rules``).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Iterable

ALLOWED_MODULES = {"re", "json", "datetime", "math", "collections", "itertools"}
_SAFE = ("len", "any", "all", "sum", "min", "max", "sorted", "set", "list", "dict", "tuple", "str", "int", "float",
         "bool", "isinstance", "enumerate", "zip", "range", "abs", "round", "reversed", "map", "filter", "ValueError",
         "KeyError", "TypeError", "Exception")

NOTE = ("Review before acting: an automatic consistency check flagged your proposed call {call}. Check: {description} "
        "Basis: {clause} Re-read the user's requests and the tool results, then either make the correct call or "
        "explain to the user what is needed.")


def _safe_import(name: str, *a: Any, **kw: Any):
    if name.split(".")[0] not in ALLOWED_MODULES:
        raise ImportError(f"module {name} not allowed")
    return __import__(name, *a, **kw)


def compile_check(code: str) -> Callable[[dict, list], bool]:
    import builtins
    env: dict = {"__builtins__": {k: getattr(builtins, k) for k in _SAFE} | {"__import__": _safe_import},
                 "json": json, "re": re}
    exec(compile(code, "<mined-check>", "exec"), env)  # noqa: S102 - audited predicates, restricted builtins
    return env["check"]


def load_checks(path: str | Path, only_transferring: bool = True) -> list[dict]:
    """Final versions of the mined checks in an R1 result file (default: those that transferred)."""
    out = []
    for r in json.loads(Path(path).read_text())["mined"]:
        if only_transferring and not r.get("transfers"):
            continue
        out.append({"name": r["name"], "description": r.get("description") or "", "clause": r.get("clause") or "",
                    "fold": r["fold"], "fn": compile_check(r["versions"][-1]["code"])})
    return out


def simplify(messages: Iterable[Any]) -> list[dict]:
    """τ² messages (objects or dicts) in the plain shape the predicates were written against."""
    out = []
    for m in messages:
        m = m if isinstance(m, dict) else m.model_dump()
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


class MinedChecker:
    def __init__(self, checks: list[dict]):
        self.checks = checks

    def check(self, messages: Iterable[Any], am: Any) -> list[tuple[str, str, str]]:
        am = am if isinstance(am, dict) else am.model_dump()
        tcs = am.get("tool_calls") or []
        if not tcs:
            return []
        hist = simplify(messages)
        hits = []
        for tc in tcs:
            call = {"name": tc["name"], "arguments": tc.get("arguments") or {}}
            for c in self.checks:
                try:
                    fired = bool(c["fn"](call, hist))
                except Exception:  # noqa: BLE001 - a crashing predicate never blocks the agent
                    fired = False
                if fired:
                    hits.append((f"mined:{c['name']}", "soft", NOTE.format(
                        call=f"{call['name']}({json.dumps(call['arguments'])})", description=c["description"],
                        clause=c["clause"])))
        return hits
