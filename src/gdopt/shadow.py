"""Stage 3a: shadow evaluation of a decision model against logged LLM actions.

For each step we ask the decision model the same question the agent answered
("what is the next action?") and compare its answer with what the LLM did.
Agreement and calibration are measured per situation.  Nothing is executed, so
this is safe to run on production logs.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from .decision import NEXT_ACTION_INSTRUCTIONS, ChoiceResult, DecisionModel, conversation_state
from .situation import SituationModel
from .trace import Step


@dataclass
class ShadowRecord:
    trajectory_id: str
    step_index: int
    leaf_id: int
    llm_action: str
    probabilities: dict[str, float]
    cost: float

    @property
    def top(self) -> str:
        return max(self.probabilities, key=self.probabilities.get)

    @property
    def p_max(self) -> float:
        return self.probabilities[self.top]

    @property
    def p_llm(self) -> float:
        return self.probabilities.get(self.llm_action, 0.0)

    @property
    def agree(self) -> bool:
        return self.top == self.llm_action


def expected_calibration_error(confidences: Iterable[float], correct: Iterable[bool], n_bins: int = 10) -> float:
    conf = list(confidences)
    corr = list(correct)
    if not conf:
        return 0.0
    bins: dict[int, list[tuple[float, bool]]] = defaultdict(list)
    for c, ok in zip(conf, corr):
        bins[min(int(c * n_bins), n_bins - 1)].append((c, ok))
    ece = 0.0
    for items in bins.values():
        avg_conf = sum(c for c, _ in items) / len(items)
        acc = sum(1 for _, ok in items if ok) / len(items)
        ece += len(items) / len(conf) * abs(avg_conf - acc)
    return ece


@dataclass
class SituationShadow:
    leaf_id: int
    n: int
    agreement: float
    ece: float
    mean_p_max: float
    # Agreement among steps whose p_max >= tau, and the fraction of steps kept, per tau.
    coverage_curve: dict[float, tuple[float, float]] = field(default_factory=dict)


@dataclass
class ShadowResult:
    records: list[ShadowRecord]
    total_cost: float

    def by_situation(self, taus: Iterable[float] = (0.5, 0.6, 0.7, 0.8, 0.9, 0.95)) -> dict[int, SituationShadow]:
        groups: dict[int, list[ShadowRecord]] = defaultdict(list)
        for r in self.records:
            groups[r.leaf_id].append(r)
        out: dict[int, SituationShadow] = {}
        for leaf_id, recs in groups.items():
            curve = {}
            for tau in taus:
                kept = [r for r in recs if r.p_max >= tau]
                curve[tau] = (
                    sum(r.agree for r in kept) / len(kept) if kept else 0.0,
                    len(kept) / len(recs),
                )
            out[leaf_id] = SituationShadow(
                leaf_id=leaf_id,
                n=len(recs),
                agreement=sum(r.agree for r in recs) / len(recs),
                ece=expected_calibration_error((r.p_max for r in recs), (r.agree for r in recs)),
                mean_p_max=sum(r.p_max for r in recs) / len(recs),
                coverage_curve=curve,
            )
        return out

    @property
    def agreement(self) -> float:
        return sum(r.agree for r in self.records) / len(self.records) if self.records else 0.0


def shadow_evaluate(
    steps: Iterable[Step],
    situation_model: SituationModel,
    decision_model: DecisionModel,
    menu: dict[str, str],
    policy: str | None = None,
    instructions: str = NEXT_ACTION_INSTRUCTIONS,
    state_builder: Callable[[Step], Any] | None = None,
    leaf_filter: Callable[[int], bool] | None = None,
    on_record: Callable[[ShadowRecord], None] | None = None,
) -> ShadowResult:
    records: list[ShadowRecord] = []
    total = 0.0
    for s in steps:
        leaf = situation_model.situation(s.history)
        if leaf_filter is not None and not leaf_filter(leaf.id):
            continue
        state = state_builder(s) if state_builder else conversation_state(s.history, policy)
        res: ChoiceResult = decision_model.choice(instructions, menu, state)
        rec = ShadowRecord(s.trajectory_id, s.index, leaf.id, s.action, dict(res.probabilities), res.cost)
        records.append(rec)
        total += res.cost
        if on_record:
            on_record(rec)
    return ShadowResult(records, total)
