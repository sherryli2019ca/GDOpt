# GDOpt

**Strength reduction for LLM agents.** GDOpt finds the steps of an existing LLM agent that can be taken by a
cheap decision model (TypeSafe's Jev, or any model that returns calibrated probabilities over a fixed option
set) or by a plain rule, rewrites the agent into a tiered policy with LLM fallback, and chooses the fallback
threshold with a statistical guarantee on end-to-end task accuracy.

Design notes (Chinese): the project's design document lives in the GDOpt Claude project; this README is the
code-level view.

## Pipeline

| stage | module | what it does |
| --- | --- | --- |
| 0 | `gdopt.adapters.tau2` | loads τ²-bench result files into framework-neutral trajectories (`gdopt.trace`) |
| 1 | `gdopt.entities`, `gdopt.situation` | learns identifier shapes and an entity table; maps every history to a **situation** (leaf of a decision tree that predicts the next action from generic features: last action, tool status, known entity types, confirmation words) |
| 2 | `gdopt.profile` | per-situation statistics on held-out trials: next-action entropy, majority accuracy, share of steps that are tool calls with all arguments already in context, latest-entity argument rule accuracy, cost share, upper bound on saving; stage-2 candidate tiers |
| 3 | `gdopt.shadow`, `gdopt.replay` | shadow calls of the decision model against logged LLM actions (agreement, ECE, coverage curve per situation); counterfactual replay of single disagreeing steps against a runner |
| 4 | `gdopt.tiers`, `gdopt.calibrate` | tier table (code / jev / llm, per-situation threshold τ) and the `TieredPolicy`; one global knob λ scales all thresholds, chosen by Learn-then-Test with an empirical-Bernstein p-value on paired task losses so that the failure rate rises by at most ε with probability ≥ 1 − δ |

`gdopt.decision.OpenRouterJev` talks to Jev through OpenRouter's `/api/alpha/decisions` endpoint
(`OPENROUTER_API_KEY`). `gdopt.toy` is a small τ²-style environment with a scripted noisy "LLM" and a
simulated Jev so the whole loop runs offline.

## Quick start

```bash
pip install -e .[dev]
pytest

# stage 1-2 on τ²-bench traces shipped with https://github.com/sierra-research/tau2-bench
gdopt profile path/to/tau2-bench/data/tau2/results/final/gpt-4.1-2025-04-14_airline_default_gpt-4.1-2025-04-14_4trials.json --top 20

# full loop on the toy environment (profile -> tiers -> Learn-then-Test -> held-out evaluation)
python examples/toy_pipeline.py
```

`reports/tau2/` holds the stage-2 profiles for the nine τ²-bench runs (GPT-4.1, Claude 3.7 Sonnet, o4-mini ×
airline, retail, telecom); `reports/tau2/SUMMARY.md` summarizes them.

## Using it on another agent

1. Write an adapter that yields `gdopt.trace.Trajectory` objects (messages with roles `user` / `assistant` /
   `tool`; every assistant message is one step; tool calls carry `name` and `arguments`).
2. `fit_situations(train)` and `profile(model, train, test)`.
3. Run `shadow_evaluate` with your decision model on the candidate situations, then
   `TierTable.from_profile(report, shadow.by_situation())`.
4. Implement `gdopt.replay.Runner` for your environment, calibrate λ with `learn_then_test`, and serve
   `TieredPolicy(...).decide(history)` in place of the LLM call.

## Status

First version. What is real: the offline stages on τ²-bench's own traces, the Jev client, the tiered policy, and
the calibration, all exercised end to end on the toy environment. What is not done yet: running Jev shadow
calls on τ²-bench traces (needs an OpenRouter key), plugging the tiered policy into τ²-bench's orchestrator for
counterfactual replay, and the Noul sub-decision extraction for policy checks.
