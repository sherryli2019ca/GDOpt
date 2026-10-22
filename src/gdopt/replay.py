"""Stage 3b: counterfactual replay and end-to-end evaluation.

GDOpt never trusts local agreement alone: a replaced step is judged by what
happens to the task.  Anything that can run an episode with a given policy
implements :class:`Runner`; τ²-bench's orchestrator, a LangGraph graph or the
toy environment in :mod:`gdopt.toy` all fit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol, Sequence

from .trace import Message

Policy = Callable[[list[Message]], Message]


@dataclass
class EpisodeResult:
    task_id: str
    success: bool
    cost: float
    n_steps: int
    n_llm_steps: int
    tiers_used: dict[str, int] = field(default_factory=dict)

    @property
    def loss(self) -> float:
        return 0.0 if self.success else 1.0


class Runner(Protocol):
    def run(self, task_id: str, policy: Policy, seed: int = 0) -> EpisodeResult: ...


@dataclass
class EvalSummary:
    results: list[EpisodeResult]

    @property
    def success_rate(self) -> float:
        return sum(r.success for r in self.results) / len(self.results) if self.results else 0.0

    @property
    def mean_cost(self) -> float:
        return sum(r.cost for r in self.results) / len(self.results) if self.results else 0.0

    @property
    def llm_step_share(self) -> float:
        n = sum(r.n_steps for r in self.results)
        return sum(r.n_llm_steps for r in self.results) / n if n else 0.0

    def losses(self) -> list[float]:
        return [r.loss for r in self.results]


def evaluate(runner: Runner, task_ids: Sequence[str], policy: Policy, seeds: Sequence[int] = (0,)) -> EvalSummary:
    results = [runner.run(t, policy, seed=s) for s in seeds for t in task_ids]
    return EvalSummary(results)


@dataclass
class SensitivityRecord:
    task_id: str
    step_index: int
    original_action: str
    counterfactual_action: str
    original_success: bool
    counterfactual_success: bool


def counterfactual_sensitivity(
    runner: Runner,
    task_id: str,
    original: Policy,
    step_index: int,
    counterfactual_action: Message,
    seed: int = 0,
) -> SensitivityRecord:
    """Re-run a task once with step ``step_index`` forced to ``counterfactual_action``.

    All other steps are produced by the original policy, so the result isolates
    the end-to-end effect of that one disagreement.  Only steps where the
    decision model disagrees with the LLM need this; agreeing steps leave the
    trajectory byte-identical (given a deterministic downstream).
    """
    counter = {"i": 0, "orig": None, "cf": None}

    def forced(history: list[Message]) -> Message:
        i = counter["i"]
        counter["i"] += 1
        if i == step_index:
            counter["orig"] = original(history)
            counter["cf"] = counterfactual_action
            return counterfactual_action
        return original(history)

    base = runner.run(task_id, original, seed=seed)
    cf = runner.run(task_id, forced, seed=seed)
    orig_msg = counter["orig"]
    return SensitivityRecord(
        task_id,
        step_index,
        (orig_msg.action if orig_msg else "?"),
        counterfactual_action.action or "message",
        base.success,
        cf.success,
    )
