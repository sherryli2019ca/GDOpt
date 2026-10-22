"""Local verification without calibration or replay.

Three checks that need only logged traces, a decision model and (optionally)
the benchmark's reference actions:

1. **Agreement with the LLM**, per situation, with the coverage curve
   (agreement among steps whose confidence is at least tau, and how many steps
   that keeps).  This is the standard shadow metric.
2. **Consistency filter**: agreement measured only on steps of successful
   trajectories, where the LLM's action is known to have led to a correct
   outcome.  Disagreements on failed trajectories are reported separately,
   since there the LLM may be the one that was wrong.
3. **Gold-action check**: when the benchmark lists the reference tool calls of
   a task (τ²-bench ``evaluation_criteria.actions``), a proposed tool call is
   scored against them: does the decision model's choice (with arguments
   filled by the latest-entity rule) match a reference action that has not
   been executed yet?  The same score is computed for the LLM's logged action,
   so disagreements can be split into "Jev was right", "LLM was right",
   "neither" and "undecidable" without running the environment.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from .entities import build_entity_table
from .shadow import ShadowRecord, ShadowResult, expected_calibration_error
from .situation import SituationModel
from .trace import Trajectory, action_tool_name, is_tool_action

GoldActions = dict[str, list[tuple[str, dict[str, Any]]]]


def _norm_args(args: dict[str, Any]) -> dict[str, str]:
    return {k: str(v).strip() for k, v in args.items() if not isinstance(v, (list, dict))}


def _executed(traj: Trajectory, upto: int) -> list[tuple[str, dict[str, str]]]:
    out = []
    for m in traj.messages[:upto]:
        for tc in m.tool_calls:
            out.append((tc.name, _norm_args(tc.arguments)))
    return out


def gold_hit(tool: str, args: dict[str, Any] | None, gold: list[tuple[str, dict[str, Any]]], executed: list[tuple[str, dict[str, str]]]) -> bool | None:
    """True / False when decidable, None when the tool is not a reference action at all.

    A reference action counts as hit when its name matches and every scalar
    argument of the reference equals the proposal's (list arguments are not
    compared), and the same reference action has not already been executed.
    """
    refs = [(n, _norm_args(a)) for n, a in gold if n == tool]
    if not refs:
        return None
    if args is None:
        return False
    a = _norm_args(args)
    for name, ref in refs:
        if (name, ref) in executed:
            continue
        if all(a.get(k) == v for k, v in ref.items()):
            return True
    return False


@dataclass
class StepVerdict:
    record: ShadowRecord
    trajectory_success: bool
    llm_gold: bool | None
    jev_gold: bool | None
    jev_args: dict[str, Any] | None

    @property
    def verdict(self) -> str:
        if self.record.agree:
            return "agree"
        if self.jev_gold is True and self.llm_gold is not True:
            return "jev_right"
        if self.llm_gold is True and self.jev_gold is not True:
            return "llm_right"
        if self.jev_gold is False and self.llm_gold is False:
            return "neither"
        return "undecidable"


@dataclass
class SituationLocalEval:
    leaf_id: int
    n: int
    agreement: float
    agreement_on_success: float
    n_success: int
    ece: float
    coverage_curve: dict[float, tuple[float, float]]
    verdicts: dict[str, int] = field(default_factory=dict)


@dataclass
class LocalEvalReport:
    n: int
    agreement: float
    agreement_on_success: float
    ece: float
    verdicts: dict[str, int]
    coverage_curve: dict[float, tuple[float, float]]
    situations: list[SituationLocalEval]
    decision_cost: float
    steps: list[StepVerdict] = field(default_factory=list)


def _coverage(recs: list[ShadowRecord], taus) -> dict[float, tuple[float, float]]:
    out = {}
    for tau in taus:
        kept = [r for r in recs if r.p_max >= tau]
        out[tau] = (sum(r.agree for r in kept) / len(kept) if kept else 0.0, len(kept) / len(recs) if recs else 0.0)
    return out


def local_evaluate(
    shadow: ShadowResult,
    trajectories: list[Trajectory],
    situation_model: SituationModel,
    gold: GoldActions | None = None,
    taus=(0.5, 0.6, 0.7, 0.8, 0.9, 0.95),
) -> LocalEvalReport:
    by_id = {t.id: t for t in trajectories}
    steps: list[StepVerdict] = []
    for r in shadow.records:
        traj = by_id[r.trajectory_id]
        history = traj.messages[: r.step_index]
        g = (gold or {}).get(traj.task_id, [])
        executed = _executed(traj, r.step_index)
        llm_gold = jev_gold = None
        jev_args = None
        if g:
            if is_tool_action(r.llm_action):
                tc = traj.messages[r.step_index].tool_calls[0]
                llm_gold = gold_hit(tc.name, tc.arguments, g, executed)
            if is_tool_action(r.top):
                tool = action_tool_name(r.top) or ""
                table = build_entity_table(history, situation_model.schema)
                jev_args = {}
                for name in sorted(situation_model.schema.arg_types.get(tool, ())):
                    v = table.latest(name)
                    if v is None:
                        jev_args = None
                        break
                    jev_args[name] = v
                jev_gold = gold_hit(tool, jev_args, g, executed)
        steps.append(StepVerdict(r, traj.success, llm_gold, jev_gold, jev_args))

    groups: dict[int, list[StepVerdict]] = defaultdict(list)
    for s in steps:
        groups[s.record.leaf_id].append(s)
    sits = []
    for leaf_id, ss in sorted(groups.items()):
        recs = [s.record for s in ss]
        succ = [s.record for s in ss if s.trajectory_success]
        sits.append(
            SituationLocalEval(
                leaf_id=leaf_id,
                n=len(ss),
                agreement=sum(r.agree for r in recs) / len(recs),
                agreement_on_success=sum(r.agree for r in succ) / len(succ) if succ else 0.0,
                n_success=len(succ),
                ece=expected_calibration_error((r.p_max for r in recs), (r.agree for r in recs)),
                coverage_curve=_coverage(recs, taus),
                verdicts=dict(Counter(s.verdict for s in ss)),
            )
        )
    recs = [s.record for s in steps]
    succ = [s.record for s in steps if s.trajectory_success]
    return LocalEvalReport(
        n=len(steps),
        agreement=sum(r.agree for r in recs) / len(recs) if recs else 0.0,
        agreement_on_success=sum(r.agree for r in succ) / len(succ) if succ else 0.0,
        ece=expected_calibration_error((r.p_max for r in recs), (r.agree for r in recs)),
        verdicts=dict(Counter(s.verdict for s in steps)),
        coverage_curve=_coverage(recs, taus),
        situations=sits,
        decision_cost=shadow.total_cost,
        steps=steps,
    )


def local_eval_markdown(rep: LocalEvalReport, rules: dict[int, str] | None = None, title: str = "GDOpt local verification") -> str:
    rules = rules or {}
    pct = lambda x: f"{100 * x:.1f}%"
    lines = [f"# {title}", "",
             f"- shadow calls: {rep.n}; decision-model cost ${rep.decision_cost:.4f}",
             f"- agreement with the LLM: {pct(rep.agreement)} (on successful trajectories: {pct(rep.agreement_on_success)}); ECE {rep.ece:.3f}",
             f"- disagreement verdicts against reference actions: {rep.verdicts}",
             "", "## Coverage curve (all steps)", "", "| tau | agreement among kept | steps kept |", "| ---: | ---: | ---: |"]
    for tau, (agree, cov) in sorted(rep.coverage_curve.items()):
        lines.append(f"| {tau} | {pct(agree)} | {pct(cov)} |")
    lines += ["", "## Per situation", "", "| # | rule | n | agreement | on success | ECE | agree@0.9 / kept | verdicts |", "| ---: | --- | ---: | ---: | ---: | ---: | --- | --- |"]
    for s in sorted(rep.situations, key=lambda s: -s.n):
        a9, c9 = s.coverage_curve.get(0.9, (0.0, 0.0))
        lines.append(f"| {s.leaf_id} | `{rules.get(s.leaf_id, '')}` | {s.n} | {pct(s.agreement)} | {pct(s.agreement_on_success)} ({s.n_success}) | {s.ece:.2f} | {pct(a9)} / {pct(c9)} | {s.verdicts} |")
    return "\n".join(lines) + "\n"
