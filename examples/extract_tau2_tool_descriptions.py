"""Extract tool descriptions from τ²-bench domain tool modules (no import needed).

Usage: python examples/extract_tau2_tool_descriptions.py <tau2-bench>/src/tau2/domains/<domain>/tools.py out.json

Takes every method decorated with ``@is_tool`` and uses the summary paragraph
of its docstring, so the action menu sent to the decision model reads the same
way the tool schema read to the LLM.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path


def extract(path: Path) -> dict[str, str]:
    tree = ast.parse(path.read_text())
    out: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        is_tool = any(
            (isinstance(d, ast.Call) and getattr(d.func, "id", "") == "is_tool") or getattr(d, "id", "") == "is_tool"
            for d in node.decorator_list
        )
        if not is_tool:
            continue
        doc = ast.get_docstring(node) or ""
        summary = doc.split("\n\n")[0].replace("\n", " ").strip()
        out[node.name] = summary
    return out


if __name__ == "__main__":
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    tools = extract(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(tools, indent=1, ensure_ascii=False))
    print(f"{len(tools)} tools -> {dst}")
