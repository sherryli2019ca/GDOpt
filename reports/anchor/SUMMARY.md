# Decision-model anchors for an LLM agent — airline, 50 tasks × 4 trials (2026-10-24)

Agent and user simulator: direct DeepSeek API, model id `deepseek-chat` (the API reports `deepseek-flash`), temperature 0,
seed 300, substring communicate scorer. Jev `typesafe/jev-1.14` via OpenRouter, full conversation + policy as state,
same next-action question as the shadow evaluation. Runner: `examples/tau2_anchor_replay.py`; report: `examples/tau2_passk_report.py`.

| run | pass^1 | pass^2 | pass^3 | pass^4 | pass@4 | flaky tasks | always fail | steps/ep | $/ep (LLM+Jev) | Jev $/ep | anchor activity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline (plain LLM) | 76.0% | 68.0% | 63.0% | 60.0% | 88.0% | 28% | 12% | 10.9 | 0.0072 | – | – |
| hint (Jev suggestion in prompt when p_max ≥ 0.9) | 75.0% | 69.3% | 66.5% | 64.0% | 86.0% | 22% | 14% | 10.7 | 0.0093 | 0.0021 | hint on 42% of steps |
| veto (reconsider when Jev ≥ 0.9 disagrees) | 76.0% | 68.0% | 63.5% | 60.0% | 90.0% | 30% | 10% | 10.6 | 0.0089 | 0.0020 | 0 vetoes fired |
| checklist (3 Noul answers in prompt) | 71.0% | 62.0% | 57.5% | 56.0% | 86.0% | 30% | 14% | 10.9 | 0.0096 | 0.0020 | every step |

Paired per task (successes out of 4 vs baseline): hint +7 / −8 / same 35; veto +11 / −9 / same 30; checklist +4 / −13 / same 33.
Standard error of pass^4 on 50 tasks ≈ 7 points, so none of the differences is significant; the checklist's 13-vs-4 is the only suggestive one.

Spend: DeepSeek 10.98 CNY (balance 6388.89 → 6377.91) for all four runs ≈ $1.5; Jev $1.16 (OpenRouter usage 8.67 → 9.83).

## What the runs say

1. **Veto never fired.** In 920 steps where Jev was ≥ 0.9 confident, the LLM's action matched Jev's 100% of the time
   (shadow on GPT-4.1 traces: 95.6%). There was nothing to veto on this model.
2. **Hint removed the confident flips but there are few of them.** With hints, flaky tasks fell 28% → 22% and pass^4 rose
   60% → 64%, while pass^1 was unchanged (76 → 75). Both within noise.
3. **Checklist hurt slightly** (pass^1 −5, 13 tasks worse vs 4 better). It did not change behaviour where intended: write
   calls per episode 1.17 vs 1.15, message steps 7.17 vs 7.16, and the tracker said "confirmed" before 136 of 152 write
   calls. The damage is prompt noise and/or wrong Noul answers; the three questions were never validated against traces.
4. **The remaining flips sit where Jev is unsure too.** At the first step where a successful and a failed trial of the
   same task diverge, Jev's confidence has median 0.77 (veto run) vs 0.88 over all steps; only 28% of divergence points
   are ≥ 0.9, and in the hint run only 7% (the hint already fixed those). 36 of 39 divergences are "call a tool vs talk
   to the user". A confidence-gated anchor cannot reach these by construction.

## Caveats

- `deepseek-chat` on the direct API now resolves to a different, stronger model than the OpenRouter `deepseek/deepseek-chat`
  used on 2026-10-23 (76% vs 42%/32% pass^1); results are not comparable with the earlier replays.
- 50 tasks × 4 trials is underpowered for effects of a few points; retail (114 tasks) or more trials are needed.
- 2 of 200 veto episodes ended with `infrastructure_error` (counted as failures).

## Where this leaves the "Jev as anchor" idea

The lever is not the gate but Jev's confidence on the ambiguous "act now vs ask first" steps. Options: (a) a question
that is answerable with confidence there ("has the user supplied everything the policy needs before acting?") instead of
the generic next-action menu; (b) scoped state; (c) Noul questions validated by shadow evaluation before they go in a
prompt; (d) use low-confidence disagreement to escalate to a stronger generator (needs one that is reachable).
