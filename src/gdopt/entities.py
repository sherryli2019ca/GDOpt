"""Entity table: typed values that are already present in the context.

Closed-form tool arguments (``reservation_id``, ``user_id``, ``flight_number``,
...) are almost always copies of a value that appeared earlier, either in a
tool result or in a user message.  The entity table collects those values per
*type*, where the type is simply the argument/field name.  A tool argument is
*closed* at a step when its value is in the table at that step; a closed
argument can be filled by a decision model choosing among the candidates
instead of by a generative model.

Values inside user messages have no field name, so we learn a surface *shape*
per type from the corpus (``H8Q05L`` -> ``[A-Z0-9]{6}``) and match user text
against it.  Shapes are only learned for types whose values look like
identifiers, not free text.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable

from .trace import Message, Trajectory

_RUN_RE = re.compile(r"[A-Z]+|[a-z]+|[0-9]+|[^A-Za-z0-9]+")
_CLASS = {"upper": "[A-Z]", "lower": "[a-z]", "digit": "[0-9]"}


def _run_class(run: str) -> str:
    if run.isupper():
        return "upper"
    if run.islower():
        return "lower"
    if run.isdigit():
        return "digit"
    return "other"


def _normalize(value: Any) -> str | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value.strip()
    return None


@dataclass
class Shape:
    """Regex-like surface pattern learned from a set of identifier values."""

    pattern: str
    coverage: float  # fraction of training values the pattern matches
    regex: re.Pattern = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.regex = re.compile(r"(?<![A-Za-z0-9_])(" + self.pattern + r")(?![A-Za-z0-9_])")

    def find(self, text: str) -> list[str]:
        return [m.group(1) for m in self.regex.finditer(text)]


def learn_shape(values: Iterable[str], min_coverage: float = 0.9) -> Shape | None:
    """Learn one pattern that matches at least ``min_coverage`` of the values.

    Returns ``None`` when the values do not share a structure (free text) or
    when the pattern would be too generic to be useful (e.g. a single short
    word).
    """
    vals = [v for v in values if v and len(v) <= 40 and " " not in v]
    if len(vals) < 3:
        return None
    fine = _learn_fine_shape(vals, min_coverage)
    if fine is not None:
        return fine
    return _learn_coarse_shape(vals, min_coverage)


_COARSE_CLASSES = (
    ("[A-Z0-9]", re.compile(r"[A-Z0-9]+")),
    ("[a-z0-9_]", re.compile(r"[a-z0-9_]+")),
    ("[A-Za-z0-9_-]", re.compile(r"[A-Za-z0-9_-]+")),
)


def _learn_coarse_shape(vals: list[str], min_coverage: float) -> Shape | None:
    """Fallback for identifiers whose letter/digit runs vary (``H8Q05L``, ``3ZQ1LD``)."""
    # Identifiers mix letters and digits, but not every instance has a digit (airline ``IFOYYZ``), so only
    # require that a clear majority does; this keeps plain words out without dropping real id types.
    with_digit = sum(1 for v in vals if any(c.isdigit() for c in v)) / len(vals)
    if with_digit < 0.5:
        return None
    for cls, rx in _COARSE_CLASSES:
        matched = [v for v in vals if rx.fullmatch(v)]
        if len(matched) / len(vals) < min_coverage:
            continue
        lengths = sorted({len(v) for v in matched})
        if lengths[-1] - lengths[0] > 4:
            return None  # too variable to be a fixed-format identifier
        q = f"{{{lengths[0]}}}" if len(lengths) == 1 else f"{{{lengths[0]},{lengths[-1]}}}"
        pattern = cls + q
        coverage = sum(1 for v in vals if re.fullmatch(pattern, v)) / len(vals)
        return Shape(pattern=pattern, coverage=coverage)
    return None


def _learn_fine_shape(vals: list[str], min_coverage: float) -> Shape | None:
    sigs: Counter[tuple[tuple[str, int], ...]] = Counter()
    for v in vals:
        runs = _RUN_RE.findall(v)
        sigs[tuple((_run_class(r), len(r)) for r in runs)] += 1
    # Group signatures by class sequence; lengths may vary per run.
    by_classes: dict[tuple[str, ...], list[tuple[tuple[tuple[str, int], ...], int]]] = defaultdict(list)
    for sig, n in sigs.items():
        by_classes[tuple(c for c, _ in sig)].append((sig, n))
    best_classes, best_n = None, 0
    for classes, members in by_classes.items():
        n = sum(m for _, m in members)
        if n > best_n:
            best_classes, best_n = classes, n
    if best_classes is None or best_n / len(vals) < min_coverage:
        return None
    members = by_classes[best_classes]
    parts: list[str] = []
    for i, cls in enumerate(best_classes):
        lengths = {sig[i][1] for sig, _ in members}
        if cls == "other":
            literal = Counter(_RUN_RE.findall(v)[i] for v in vals if tuple(_run_class(r) for r in _RUN_RE.findall(v)) == best_classes)
            lit, _ = literal.most_common(1)[0]
            parts.append(re.escape(lit))
            continue
        q = f"{{{min(lengths)}}}" if len(lengths) == 1 else f"{{{min(lengths)},{max(lengths)}}}"
        parts.append(_CLASS[cls] + q)
    pattern = "".join(parts)
    # Reject generic shapes: a single run of letters is just a word.
    has_digit = any(c == "digit" for c in best_classes)
    if not has_digit and len(best_classes) < 3:
        return None
    coverage = sum(1 for v in vals if re.fullmatch(pattern, v)) / len(vals)
    if coverage < min_coverage:
        return None
    return Shape(pattern=pattern, coverage=coverage)


def _walk_json(obj: Any, out: list[tuple[str, str]]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            s = _normalize(v)
            if s is not None:
                out.append((k, s))
            else:
                _walk_json(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _walk_json(v, out)


def scalar_fields(message: Message) -> list[tuple[str, str]]:
    """All (field_name, scalar_value) pairs in a message's structured content."""
    out: list[tuple[str, str]] = []
    for tc in message.tool_calls:
        _walk_json(tc.arguments, out)
    if message.role == "tool" and message.content:
        try:
            _walk_json(json.loads(message.content), out)
        except (ValueError, TypeError):
            pass
    return out


@dataclass
class EntitySchema:
    """Corpus-level knowledge: which argument types exist and their shapes."""

    arg_types: dict[str, set[str]]  # tool name -> argument names
    shapes: dict[str, Shape]  # type -> shape learned from corpus values

    @classmethod
    def from_trajectories(cls, trajectories: list[Trajectory]) -> "EntitySchema":
        arg_types: dict[str, set[str]] = defaultdict(set)
        values: dict[str, list[str]] = defaultdict(list)
        for t in trajectories:
            for m in t.messages:
                for tc in m.tool_calls:
                    arg_types[tc.name].update(tc.arguments.keys())
                for k, v in scalar_fields(m):
                    values[k].append(v)
        shapes = {}
        for k, vals in values.items():
            shape = learn_shape(vals)
            if shape is not None:
                shapes[k] = shape
        return cls(arg_types=dict(arg_types), shapes=shapes)


@dataclass
class EntityTable:
    """Values seen so far in a history, grouped by type, newest last."""

    values: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))

    def add(self, type_: str, value: str) -> None:
        lst = self.values[type_]
        if value in lst:
            lst.remove(value)
        lst.append(value)

    def candidates(self, type_: str) -> list[str]:
        return list(self.values.get(type_, []))

    def latest(self, type_: str) -> str | None:
        lst = self.values.get(type_)
        return lst[-1] if lst else None

    def has(self, type_: str) -> bool:
        return bool(self.values.get(type_))

    def types(self) -> list[str]:
        return sorted(k for k, v in self.values.items() if v)

    def contains(self, value: str) -> str | None:
        """Return the type under which ``value`` is known, if any."""
        for k, lst in self.values.items():
            if value in lst:
                return k
        return None


def build_entity_table(history: list[Message], schema: EntitySchema) -> EntityTable:
    table = EntityTable()
    for m in history:
        for k, v in scalar_fields(m):
            table.add(k, v)
        if m.role == "user" and m.content:
            for type_, shape in schema.shapes.items():
                for v in shape.find(m.content):
                    table.add(type_, v)
    return table


def argument_closure(tool_call_args: dict[str, Any], table: EntityTable) -> dict[str, str | None]:
    """For each argument, the entity type its value was copied from, or None (open)."""
    out: dict[str, str | None] = {}
    for k, v in tool_call_args.items():
        s = _normalize(v)
        if s is None:
            out[k] = None  # lists / nested objects are treated as open
            continue
        if s in table.candidates(k):
            out[k] = k
        else:
            out[k] = table.contains(s)
    return out
