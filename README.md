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

# stage 3a: local verification without calibration or replay (needs OPENROUTER_API_KEY)
# samples 400 held-out steps from the candidate situations, shadow-calls Jev, and reports agreement,
# calibration, the coverage curve and gold-action verdicts for every disagreement; ~$0.05 at Jev prices
export OPENROUTER_API_KEY=...
gdopt shadow path/to/tau2-bench/data/tau2/results/final/gpt-4.1-2025-04-14_airline_default_gpt-4.1-2025-04-14_4trials.json \
  --policy path/to/tau2-bench/data/tau2/domains/airline/policy.md --max-steps 400 --out-dir reports/shadow

# stage 3b/4 replay on τ²-bench itself: original agent vs tiered agent on the same tasks
# (τ²-bench importable via PYTHONPATH; agent + user simulator through OpenRouter)
PYTHONPATH=path/to/tau2-bench/src:src python examples/tau2_replay.py --domain airline \
  --fit-results path/to/tau2-bench/data/tau2/results/final/gpt-4.1-2025-04-14_airline_default_gpt-4.1-2025-04-14_4trials.json \
  --shadow reports/shadow-desc/gpt-4.1-2025-04-14_airline_default_gpt-4.1-2025-04-14_4trials.shadow.json \
  --llm openrouter/deepseek/deepseek-chat --num-tasks 50 --min-tool-coverage 0.16 --out reports/replay/airline
python examples/tau2_replay_report.py reports/replay/airline
```

`gdopt.adapters.tau2_agent.TieredLLMAgent` is a τ²-bench agent that runs `TieredPolicy` in front of the LLM:
cheap-tier tool calls are executed without an LLM call, every assistant message records the tier, the
confidence, the proposed action and the decision cost in `raw_data["gdopt"]`. `reports/replay/` holds the
airline runs and `reports/replay/SUMMARY.md` the findings. `gdopt shadow` caches every Jev answer in
`<out-dir>/<stem>.shadow-cache.json`, so re-running (for example with more steps) only pays for new calls.

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

What is real: the offline stages on τ²-bench's own traces, the Jev client, the tiered policy and the
calibration (end to end on the toy environment); `gdopt shadow` run against the live Jev API on the three
τ²-bench domains (`reports/shadow/SUMMARY.md`); and the tiered agent replayed inside τ²-bench on airline
against the original agent (`reports/replay/SUMMARY.md`). The replay caught two defects the offline stages
could not (an unlearned id shape and cheap-tier loops), both fixed with tests. Not done yet: calibration of λ
on τ²-bench (needs more tasks than one domain has), retail/telecom replays, and the Noul sub-decision
extraction for policy checks.
