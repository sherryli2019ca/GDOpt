"""Stage 2: trace profiling per situation.

For every situation (tree leaf) we measure, on held-out trajectories:

* how predictable the next action is (normalized entropy, accuracy of the
  majority action),
* how often the step is a tool call whose arguments are all *closed* (copies
  of known entities), i.e. a step that needs no generative model at all,
* how often the trivial "latest entity of that type" rule reproduces the
  arguments,
* the step's share of total agent cost.

These numbers rank situations for the (expensive) shadow and replay stages and
already identify code-tier candidates.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from .entities import EntitySchema, argument_closure, build_entity_table
from .situation import FeatureVocab, SituationModel, normalized_entropy
from .trace import Step, Trajectory, action_tool_name, all_steps, is_tool_action, tool_names

JEV_USD_PER_INPUT_TOKEN = 0.042 / 1e6  # typesafe/jev-1.14 list price, output free


@dataclass
class StepFacts:
    """Static facts about one step, independent of the situation model."""

    action: str
    is_tool: bool
    all_args_closed: bool
    latest_rule_ok: bool  # args reproduced by "latest entity of each type"
    n_args: int
    n_closed: int
    cost: float
    prompt_tokens: int


def step_facts(step: Step, schema: EntitySchema) -> StepFacts:
    tc = step.tool_call
    if tc is None:
        return StepFacts(step.action, False, False, False, 0, 0, step.cost, step.message.prompt_tokens)
    table = build_entity_table(step.history, schema)
    closure = argument_closure(tc.arguments, table)
    n_closed = sum(1 for v in closure.values() if v is not None)
    all_closed = n_closed == len(closure)
    latest_ok = all_closed and all(
        str(tc.arguments[k]).strip() == table.latest(t) for k, t in closure.items() if t is not None
    )
    return StepFacts(step.action, True, all_closed, latest_ok, len(closure), n_closed, step.cost, step.message.prompt_tokens)


@dataclass
class SituationProfile:
    leaf_id: int
    rule: str
    n_train: int
    n_test: int
    train_counts: dict[str, int]
    test_counts: dict[str, int]
    majority: str
    majority_test_acc: float
    norm_entropy_test: float
    tool_rate: float  # fraction of test steps that are tool calls
    closed_tool_rate: float  # fraction of test steps that are tool calls with all args closed
    latest_rule_acc: float  # among closed tool steps, fraction reproduced by the latest-entity rule
    mean_cost: float
    cost_share: float  # share of total test cost spent in this situation
    mean_prompt_tokens: float
    # Upper bound on cost saved if every closed tool step here skipped the LLM.
    max_saving_share: float


@dataclass
class ProfileReport:
    n_trajectories_train: int
    n_trajectories_test: int
    n_steps_test: int
    n_options: int
    total_cost_test: float
    action_counts_test: dict[str, int]
    closed_tool_step_rate: float  # over all test steps
    max_saving_share: float  # sum over situations
    llm_usd_per_prompt_token: float
    jev_to_llm_price_ratio: float
    situations: list[SituationProfile] = field(default_factory=list)
    tree: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def split_by_trial(trajectories: list[Trajectory], train_trials: Iterable[int]) -> tuple[list[Trajectory], list[Trajectory]]:
    tr = set(train_trials)
    train = [t for t in trajectories if t.trial in tr]
    test = [t for t in trajectories if t.trial not in tr]
    return train, test


def fit_situations(train: list[Trajectory], schema: EntitySchema | None = None, **tree_kw) -> SituationModel:
    schema = schema or EntitySchema.from_trajectories(train)
    vocab = FeatureVocab.from_trajectories(train, schema)
    return SituationModel.fit(all_steps(train), schema, vocab, **tree_kw)


def profile(model: SituationModel, train: list[Trajectory], test: list[Trajectory]) -> ProfileReport:
    n_options = len(tool_names(train)) + 1  # tools + message
    leaf_steps: dict[int, list[tuple[Step, StepFacts]]] = defaultdict(list)
    train_counts: dict[int, Counter] = defaultdict(Counter)
    for s in all_steps(train):
        train_counts[model.situation(s.history).id][s.action] += 1
    for s in all_steps(test):
        leaf_steps[model.situation(s.history).id].append((s, step_facts(s, model.schema)))

    test_steps = [sf for lst in leaf_steps.values() for sf in lst]
    total_cost = sum(f.cost for _, f in test_steps) or 1e-12
    total_tokens = sum(f.prompt_tokens for _, f in test_steps)
    llm_price = total_cost / total_tokens if total_tokens else 0.0
    ratio = JEV_USD_PER_INPUT_TOKEN / llm_price if llm_price else 0.0

    leaves_by_id = {n.id: n for n in model.tree.leaves()}
    situations: list[SituationProfile] = []
    for leaf_id, node in leaves_by_id.items():
        sfs = leaf_steps.get(leaf_id, [])
        tcounts = Counter(f.action for _, f in sfs)
        trc = train_counts.get(leaf_id, Counter())
        majority = trc.most_common(1)[0][0] if trc else "message"
        n_test = len(sfs)
        acc = tcounts[majority] / n_test if n_test else 0.0
        tools = [f for _, f in sfs if f.is_tool]
        closed = [f for f in tools if f.all_args_closed]
        latest_ok = sum(1 for f in closed if f.latest_rule_ok)
        cost = sum(f.cost for _, f in sfs)
        situations.append(
            SituationProfile(
                leaf_id=leaf_id,
                rule=node.rule(),
                n_train=sum(trc.values()),
                n_test=n_test,
                train_counts=dict(trc),
                test_counts=dict(tcounts),
                majority=majority,
                majority_test_acc=acc,
                norm_entropy_test=normalized_entropy(tcounts, n_options),
                tool_rate=len(tools) / n_test if n_test else 0.0,
                closed_tool_rate=len(closed) / n_test if n_test else 0.0,
                latest_rule_acc=latest_ok / len(closed) if closed else 0.0,
                mean_cost=cost / n_test if n_test else 0.0,
                cost_share=cost / total_cost,
                mean_prompt_tokens=sum(f.prompt_tokens for _, f in sfs) / n_test if n_test else 0.0,
                max_saving_share=sum(f.cost for f in closed) * (1 - ratio) / total_cost,
            )
        )
    situations.sort(key=lambda s: s.max_saving_share, reverse=True)
    n_closed_all = sum(1 for _, f in test_steps if f.is_tool and f.all_args_closed)
    return ProfileReport(
        n_trajectories_train=len(train),
        n_trajectories_test=len(test),
        n_steps_test=len(test_steps),
        n_options=n_options,
        total_cost_test=total_cost,
        action_counts_test=dict(Counter(f.action for _, f in test_steps)),
        closed_tool_step_rate=n_closed_all / len(test_steps) if test_steps else 0.0,
        max_saving_share=sum(s.max_saving_share for s in situations),
        llm_usd_per_prompt_token=llm_price,
        jev_to_llm_price_ratio=ratio,
        situations=situations,
        tree=model.tree.to_dict(),
    )


def candidate_tiers(
    report: ProfileReport,
    code_acc: float = 0.98,
    code_min_test: int = 20,
    jev_max_entropy: float = 0.75,
) -> dict[int, str]:
    """Stage-2 candidate tier per situation, before any decision-model call.

    ``code``: the next action is (almost) deterministic and its arguments are
    reproduced by the latest-entity rule, so a rule can replace the step.
    ``jev``: the action is fairly predictable; worth a shadow evaluation.
    ``llm``: everything else.
    """
    out: dict[int, str] = {}
    for s in report.situations:
        if (
            s.n_test >= code_min_test
            and s.majority_test_acc >= code_acc
            and is_tool_action(s.majority)
            and s.closed_tool_rate >= code_acc
            and s.latest_rule_acc >= code_acc
        ):
            out[s.leaf_id] = "code"
        elif s.norm_entropy_test <= jev_max_entropy:
            out[s.leaf_id] = "jev"
        else:
            out[s.leaf_id] = "llm"
    return out


def majority_tool(s: SituationProfile) -> str | None:
    return action_tool_name(s.majority)
