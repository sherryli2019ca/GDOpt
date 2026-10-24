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

## Round 2 (2026-10-24): use Jev's *uncertainty* as the signal

Dr Cao's inversion of the idea: instead of pushing the LLM where Jev is sure (where it already agrees), make the LLM
work harder where Jev is unsure. Three more runs, same 50 airline tasks × 4 trials, same seed, same baseline:

- **deliberate**: when Jev's p_max < 0.8, append a system note "a calibrated decision model finds this step ambiguous
  (torn between A and B, confidence p): quote the policy rules that apply, check each precondition, then decide".
- **reasoner**: when Jev's p_max < 0.8, generate that step with `deepseek-reasoner` instead of `deepseek-chat`.
- **deliberate_all** (control): the same careful-reasoning note on every step, no Jev.

| run | pass^1 | pass^2 | pass^3 | pass^4 | pass@4 | flaky | always fail | steps/ep | completion tok/ep | $/ep (table) | anchor activity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 76.0% | 68.0% | 63.0% | 60.0% | 88.0% | 28% | 12% | 10.9 | 1 314 | 0.0072 | – |
| deliberate (p_max < 0.8) | 79.5% | 70.7% | 65.5% | 62.0% | 94.0% | 32% | 6% | 10.9 | 2 383 | 0.0122 | note on 738 / 1990 steps (37%) |
| reasoner (p_max < 0.8) | **80.0%** | **73.3%** | **69.5%** | **66.0%** | 92.0% | 26% | 8% | 10.8 | 2 104 | 0.0105 | reasoner on 669 / 1951 steps (34%) |
| deliberate_all (every step) | 75.5% | 64.3% | 57.5% | 52.0% | 94.0% | 42% | 6% | 9.7 | 4 573 | 0.0118 | note on 1748 / 1748 steps |

Paired per task (successes out of 4 vs baseline): deliberate +10 / −6 / same 34; reasoner +10 / −6 / same 34;
deliberate_all +10 / −12 / same 28.

Paired bootstrap over tasks (10 000 resamples):

| run | Δpass^1 | 95% CI | P(Δ>0) | Δpass^4 | 95% CI | P(Δ>0) |
| --- | --- | --- | --- | --- | --- | --- |
| deliberate | +3.5 | [−1.5, +9.0] | 0.89 | +2 | [−8, +12] | 0.64 |
| reasoner | +4.0 | [−2.0, +10.0] | 0.89 | +6 | [−6, +18] | 0.77 |
| deliberate_all | −0.5 | [−6.5, +5.5] | 0.45 | −8 | [−20, +2] | 0.05 |
| (round 1) hint | −1.0 | | | +4 | | 0.71 |
| (round 1) checklist | −5.0 | | 0.06 | −4 | | |

Spend for round 2: DeepSeek 13.75 CNY (6377.70 → 6363.95; deliberate 3.67, reasoner 3.69, deliberate_all 6.39) and
Jev $0.81 (OpenRouter usage 9.83 → 10.64). The reasoner run cost the same as the deliberate run in real CNY because
reasoning tokens replaced the longer prompts and the step count was slightly lower.

### Reading

1. **Targeting matters more than the intervention.** The same careful-reasoning note helps when it is placed on the 37%
   of steps Jev finds ambiguous (pass^1 +3.5, always-fail 12% → 6%) and hurts consistency when it is placed on every
   step (pass^4 −8, flaky 28% → 42%, completion tokens ×3.5). With the note everywhere the model over-deliberates on
   routine steps and its trials diverge more; with Jev as the gate the routine steps stay untouched.
2. **A stronger generator at the uncertain steps is the best configuration so far**: reasoner is the only run that
   improves every pass^k (76/68/63/60 → 80/73/70/66) and lowers flakiness (28% → 26%), at 34% of steps and the same
   real cost as the prompt-only variant. This is executor tier 4 of the design ("expensive generator") selected by
   the decision model's uncertainty rather than by a fixed routing rule.
3. **Still underpowered.** Both targeted runs have P(Δpass^1 > 0) ≈ 0.89 and wide pass^4 intervals; the control's
   pass^4 drop is the only effect near significance (P = 0.05). 50 tasks cannot separate +4 from 0.
4. **Round 1 vs round 2.** Confidence-gated anchors (hint, veto) could not reach the flips because the LLM already
   agrees with Jev when Jev is sure; uncertainty-gated interventions reach exactly the steps where the forks are
   (Jev < 0.8 covers 54% of divergence points at 35% of steps, see the determinism doc), and that is where the gains
   appear.

### Next

- Power: retail (114 tasks) with baseline + reasoner, or 8 trials on airline, before claiming an effect.
- Sweep τ_uncertain (0.7 / 0.8 / 0.9): the trade-off is coverage of forks vs cost and over-deliberation.
- Cheaper note variants: a one-line "check the policy preconditions for A vs B" without the full template, to see how
  much of the deliberate gain is the content vs the mere interruption.
- Combine: reasoner on uncertain steps + hint on confident steps (the two gates are disjoint).

## Round 2b (2026-10-24): deliberation note + reasoner together

Dr Cao asked for the fourth cell of the 2×2 (note yes/no × reasoner yes/no, both only at Jev p_max < 0.8):
`--modes deliberate,reasoner`. Same 50 airline tasks × 4 trials, same seed, same user simulator. The first launch died
after 24 episodes (process reaped when the shell exited); the run was resumed from τ²'s checkpoint
(`auto_resume=True` now set in `examples/tau2_anchor_replay.py`), so the 200 episodes come from two processes.

| at Jev-uncertain steps | no reasoner | reasoner |
| --- | --- | --- |
| no note | baseline 76.0 / 60.0 (flaky 28%) | reasoner 80.0 / 66.0 (flaky 26%) |
| note | deliberate 79.5 / 62.0 (flaky 32%) | **deliberate+reasoner 82.0 / 72.0 (flaky 18%)** |

(cells: pass^1 / pass^4; the untargeted control deliberate_all is 75.5 / 52.0, flaky 42%.)

Full row for the new run: pass^1 82.0%, pass^2 77.0%, pass^3 74.0%, pass^4 72.0%, pass@4 90%, flaky 18%, always-fail
10%, 10.5 steps/ep, trigger on 626 / 2097 steps (29.9%), completion tokens 3 127/ep (baseline 1 314, reasoner 2 104),
prompt tokens 68 825/ep (baseline 71 191). Spend: DeepSeek 4.99 CNY (6363.95 → 6358.96), Jev $0.38–0.40.

Paired bootstrap over tasks (10 000 resamples):

| comparison | tasks +/−/= | Δpass^1 | 95% CI | P(Δ>0) | Δpass^4 | 95% CI | P(Δ>0) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| vs baseline | 9 / 3 / 38 | +6.0 | [+0.5, +12.5] | 0.98 | +12 | [0, +24] | 0.97 |
| vs reasoner alone | 8 / 8 / 34 | +2.0 | [−3.5, +8.0] | 0.71 | +6 | [−6, +18] | 0.77 |
| vs deliberate alone | 9 / 7 / 34 | +2.5 | [−2.0, +7.5] | 0.82 | +10 | [−2, +22] | 0.92 |

### Reading

1. **First configuration that clears the noise floor against the baseline.** pass^1 +6 (CI excludes 0) and pass^4 +12
   (CI touches 0), with only 3 tasks worse. Flaky tasks fall from 28% to 18%: the gain is mostly consistency, i.e.
   decision stability under input perturbation, which is the framing Dr Cao chose for the paper.
2. **The two factors are complementary, not redundant.** Each alone gives +3.5–4 on pass^1 and +2–6 on pass^4; together
   +6 / +12. The note tells the reasoner *what* is ambiguous (the two candidate actions and "check the policy
   preconditions"); the reasoner has the budget to act on it. Against either single factor the improvement is not yet
   significant (P ≈ 0.7–0.9), so "complementary" is the reading, not a proven interaction.
3. **Cost stays in the same band.** 4.99 CNY vs 3.69 (reasoner) and 3.67 (deliberate) for 200 episodes: the reasoner
   spends more completion tokens when it also gets the note, but the trigger fires on only 30% of steps, so the run is
   still far from the untargeted control (6.39 CNY, and worse results).
4. **Trigger rate drifted down** (37% → 34% → 30% across deliberate / reasoner / combined) because more consistent
   agents reach fewer ambiguous mid-dialogue states; the trigger is state-dependent, not a fixed budget.
5. Caveats unchanged: 50 tasks, one domain, one LLM; the resumed run mixes two processes (identical config and seed, so
   the only difference is wall-clock). Needs retail and a second LLM before it is a claim.

### Next

- Replicate on retail (114 tasks) with baseline and deliberate+reasoner: ~15 CNY + $1 Jev.
- τ_uncertain sweep on the combined mode (0.7 / 0.9) to trace the coverage–cost curve.
- Compare against PolicyGuard-style verification before write tools on the same tasks (closest published competitor).
