# Determinism of τ²-bench agents (zero-cost analysis, 2026-10-23)

Scripts: `examples/determinism/` (run with `PYTHONPATH=src`, `TAU2_BENCH_ROOT` pointing at a tau2-bench clone).
Inputs: the 4-trial result files shipped with tau2-bench (`data/tau2/results/final/*_default_*_4trials.json`,
user simulator GPT-4.1) and our two DeepSeek airline baseline runs (`reports/replay/airline`, `reports/replay/airline-baseline-rep2`).

## Our two baseline runs (airline, 50 tasks, DeepSeek agent + user, identical seed)

| both pass | only run 1 | only run 2 | neither | pass^1 | pass^2 (est.) | first action same | full tool sequence same | tool-set Jaccard |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 16 | 5 | 0 | 29 | 42% / 32% | 32% | 100% | 32% | 0.74 |

## Shipped 4-trial results

pass^k as defined by τ-bench (all k trials succeed). "flaky" = 1–3 successes out of 4.
"write seq. unanimous" = the sequence of state-changing tool names (τ²'s `ToolType.WRITE` + transfer) is identical
across the trials compared. "within-task entropy share" = H(action | situation, task) / H(action | situation)
with situations from the GDOpt tree fitted on trials 0–1 (includes user-simulator randomness, so an upper bound).

| agent | domain | pass^1 | pass^4 | flaky tasks | write seq. unanimous, successes | write seq. unanimous, failures | within-task entropy share | first divergence = tool vs message |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GPT-4.1 | airline | 56% | 40% | 38% | 69% | 35% | 43% | 78% |
| GPT-4.1 | retail | 74% | 53% | 38% | 80% | 30% | 38% | 83% |
| GPT-4.1 | telecom | 34% | 19% | 31% | 93% | 30% | 59% | 89% |
| Claude 3.7 Sonnet | airline | 50% | 36% | 32% | 70% | 48% | 48% | 51% |
| Claude 3.7 Sonnet | retail | 79% | 60% | 33% | 80% | 41% | 50% | 86% |
| Claude 3.7 Sonnet | telecom | 49% | 25% | 45% | 89% | 48% | 56% | 88% |
| o4-mini | airline | 59% | 38% | 38% | 59% | 22% | 46% | 88% |
| o4-mini | retail | 72% | 46% | 46% | 77% | 44% | 51% | 89% |
| o4-mini | telecom | 42% | 26% | 33% | 30% | 3% | 69% | 65% |

Findings:

1. One third to one half of tasks flip between trials; pass^4 is 15–25 points below pass^1.
2. The first agent action is identical across trials in every file; the whole tool sequence almost never is (1–24%).
   But the write-tool sequence agrees across successful trials 59–93% of the time and across failed trials only 3–48%:
   the correct path is nearly unique, the failures scatter.
3. Roughly half of the per-situation action entropy remains after conditioning on the task (upper bound on
   agent+user-sim noise; isolating the agent needs resampling at fixed histories).
4. Aligning a successful and a failed trial of the same task step by step, the first differing action is
   "one called a tool, the other messaged the user" in 51–89% of pairs, in the first half of the dialogue.

## Jev reproducibility (2026-10-23, `examples/determinism/jev_reproducibility.py`, $0.012)

Identical decision calls (same instructions, options, state as in the shadow caches), 8 sequential + 8 concurrent per state.

| state (from shadow-desc cache) | distinct vectors / 16 | max abs diff | p_max range today | p_max yesterday | argmax changed |
| --- | --- | --- | --- | --- | --- |
| airline, saturated (p_max = 1.0) | 1 | 0.00 | 1.00 | 1.00 | no |
| airline, near threshold (p_max ≈ 0.9) | 5 | 0.04 | 0.88–0.92 | 0.89 | no |
| airline, close top-2 (p_max ≈ 0.5) | 12 | 0.10 | 0.50–0.59 | 0.50 | yes (message vs update_reservation_flights) |
| telecom, close top-2 yesterday | 14 | 0.12 | 0.59–0.71 | 0.47 | no (today); ~0.2 shift vs yesterday |

Reading: Jev is not byte-reproducible except for saturated decisions. Probabilities jitter by a few hundredths on
confident states and by up to ~0.1 on uncertain ones; the argmax flips only when the top two are within the jitter.
Between days one state moved by ~0.2 (one observation, cause unknown: serving or model update). Design consequence:
the Jev tier is action-deterministic if it acts only when p_max ≥ τ with a margin δ larger than the jitter (τ = 0.9
already implies a top-2 gap ≥ 0.8), and memoizing (situation, state view) → decision removes the act/defer toggling
for the 5–10% of steps whose p_max sits within ±0.02 of τ. A fixed probe set re-queried periodically is a cheap drift canary.
The fifth planned state (telecom, p_max ≈ 0.6) was not run: the budget cap ($0.012) was reached after four.
