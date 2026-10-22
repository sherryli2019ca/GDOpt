"""Situation keys: mapping a history to a discrete situation.

The situation key is the "call site" of a step-wise agent.  Its features are
generic across tool-using agents (what happened last, which tools have been
called, which entity types are known).  Instead of hand-picking a granularity
we grow a decision tree that predicts the next action from these features; each
leaf is a situation, and the leaf's action distribution is its entropy.  This is
process mining on LLM agent logs.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from .entities import EntitySchema, build_entity_table
from .trace import Message, Step, tool_names

CONFIRM_RE = re.compile(
    r"\b(yes|yeah|yep|sure|ok(ay)?|confirm(ed)?|go ahead|proceed|please do|that'?s (right|correct)|correct)\b"
    r"|是的|确认|可以|好的|没问题",
    re.IGNORECASE,
)
NEGATE_RE = re.compile(r"\b(no|not|don'?t|cancel that|never ?mind|wait)\b|不要|不用|别|等等", re.IGNORECASE)

Features = dict[str, str]


@dataclass
class FeatureVocab:
    tools: list[str]
    entity_types: list[str]

    @classmethod
    def from_trajectories(cls, trajectories, schema: EntitySchema) -> "FeatureVocab":
        types = sorted({a for args in schema.arg_types.values() for a in args})
        return cls(tools=tool_names(trajectories), entity_types=types)


def featurize(history: list[Message], vocab: FeatureVocab, schema: EntitySchema) -> Features:
    """Generic situation features of a history.  All values are strings."""
    f: Features = {}
    prev = history[-1] if history else None
    f["prev_role"] = prev.role if prev else "start"
    f["prev_tool"] = (prev.tool_name or "?") if prev and prev.role == "tool" else "-"
    f["prev_tool_error"] = "1" if prev and prev.role == "tool" and prev.error else "0"
    last_action = "-"
    for m in reversed(history):
        if m.role == "assistant":
            last_action = m.action or "message"
            break
    f["last_agent_action"] = last_action
    if prev and prev.role == "user" and prev.content:
        text = prev.content
        f["user_confirms"] = "1" if CONFIRM_RE.search(text) and not NEGATE_RE.search(text) else "0"
        f["user_short"] = "1" if len(text) < 80 else "0"
    else:
        f["user_confirms"] = "0"
        f["user_short"] = "0"
    n_calls = sum(1 for m in history if m.role == "assistant" and m.tool_calls)
    f["n_tool_calls"] = str(min(n_calls, 3)) if n_calls < 3 else "3+"
    called = {tc.name for m in history for tc in m.tool_calls}
    for t in vocab.tools:
        f[f"called:{t}"] = "1" if t in called else "0"
    table = build_entity_table(history, schema)
    for e in vocab.entity_types:
        f[f"have:{e}"] = "1" if table.has(e) else "0"
    return f


def entropy(counts: Counter) -> float:
    n = sum(counts.values())
    if n == 0:
        return 0.0
    return -sum(c / n * math.log2(c / n) for c in counts.values() if c)


def normalized_entropy(counts: Counter, n_options: int) -> float:
    if n_options <= 1:
        return 0.0
    return max(0.0, entropy(counts) / math.log2(n_options))


@dataclass
class Node:
    id: int
    depth: int
    path: list[tuple[str, str]]  # (feature, value) tests from the root
    counts: Counter = field(default_factory=Counter)
    split_feature: str | None = None
    children: dict[str, "Node"] = field(default_factory=dict)
    default_child: str | None = None  # value with most samples, for unseen values

    @property
    def is_leaf(self) -> bool:
        return self.split_feature is None

    @property
    def n(self) -> int:
        return sum(self.counts.values())

    @property
    def majority(self) -> str:
        return self.counts.most_common(1)[0][0] if self.counts else "message"

    def rule(self) -> str:
        return " & ".join(f"{k}={v}" for k, v in self.path) or "(root)"


class SituationTree:
    """ID3-style tree over categorical features, entropy criterion.

    Leaves are situations.  ``max_depth`` / ``min_leaf`` keep situations large
    enough that per-situation statistics are meaningful; ``min_gain`` stops
    splitting situations that are already (nearly) deterministic.
    """

    def __init__(self, max_depth: int = 6, min_leaf: int = 25, min_gain: float = 0.02):
        self.max_depth = max_depth
        self.min_leaf = min_leaf
        self.min_gain = min_gain
        self.root: Node | None = None
        self._next_id = 0

    # -- fitting -----------------------------------------------------------
    def fit(self, X: list[Features], y: list[str]) -> "SituationTree":
        idx = list(range(len(X)))
        self._next_id = 0
        self.root = self._grow(X, y, idx, depth=0, path=[])
        return self

    def _new_node(self, depth: int, path: list[tuple[str, str]], y: list[str], idx: list[int]) -> Node:
        node = Node(id=self._next_id, depth=depth, path=path, counts=Counter(y[i] for i in idx))
        self._next_id += 1
        return node

    def _grow(self, X, y, idx, depth, path) -> Node:
        node = self._new_node(depth, path, y, idx)
        if depth >= self.max_depth or len(idx) < 2 * self.min_leaf or len(node.counts) == 1:
            return node
        h_parent = entropy(node.counts)
        best_feat, best_gain, best_groups = None, 0.0, None
        used = {k for k, _ in path}
        for feat in X[idx[0]].keys():
            if feat in used:
                continue
            groups: dict[str, list[int]] = {}
            for i in idx:
                groups.setdefault(X[i].get(feat, "?"), []).append(i)
            if len(groups) < 2 or min(len(g) for g in groups.values()) < self.min_leaf:
                continue
            h_children = sum(len(g) / len(idx) * entropy(Counter(y[i] for i in g)) for g in groups.values())
            gain = h_parent - h_children
            if gain > best_gain:
                best_feat, best_gain, best_groups = feat, gain, groups
        if best_feat is None or best_gain < self.min_gain:
            return node
        node.split_feature = best_feat
        node.default_child = max(best_groups, key=lambda v: len(best_groups[v]))
        for value, g in best_groups.items():
            node.children[value] = self._grow(X, y, g, depth + 1, path + [(best_feat, value)])
        return node

    # -- inference ---------------------------------------------------------
    def leaf(self, x: Features) -> Node:
        assert self.root is not None, "tree not fitted"
        node = self.root
        while not node.is_leaf:
            v = x.get(node.split_feature, "?")
            node = node.children.get(v) or node.children[node.default_child]
        return node

    def leaves(self) -> list[Node]:
        out: list[Node] = []

        def rec(n: Node) -> None:
            if n.is_leaf:
                out.append(n)
            else:
                for c in n.children.values():
                    rec(c)

        if self.root is not None:
            rec(self.root)
        return out

    def to_dict(self) -> dict[str, Any]:
        def rec(n: Node) -> dict[str, Any]:
            d: dict[str, Any] = {"id": n.id, "counts": dict(n.counts)}
            if not n.is_leaf:
                d["split"] = n.split_feature
                d["default"] = n.default_child
                d["children"] = {v: rec(c) for v, c in n.children.items()}
            return d

        return rec(self.root) if self.root else {}


@dataclass
class SituationModel:
    """Everything needed to map a history to a situation id at runtime."""

    schema: EntitySchema
    vocab: FeatureVocab
    tree: SituationTree

    def situation(self, history: list[Message]) -> Node:
        return self.tree.leaf(featurize(history, self.vocab, self.schema))

    @classmethod
    def fit(cls, steps: list[Step], schema: EntitySchema, vocab: FeatureVocab, **tree_kw) -> "SituationModel":
        X = [featurize(s.history, vocab, schema) for s in steps]
        y = [s.action for s in steps]
        tree = SituationTree(**tree_kw).fit(X, y)
        return cls(schema=schema, vocab=vocab, tree=tree)
