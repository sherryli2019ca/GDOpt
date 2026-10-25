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

## Round 3 (2026-10-24): two more hardenings of the Jev-uncertain steps — self-consistency vote and policy retrieval

Dr Cao asked (14:00 UTC) to explore two ways of making the perturbation-sensitive steps (Jev p_max < 0.8) more robust.
Same airline 50 tasks × 4 trials, seed 300, DeepSeek direct, baseline reused. Modes in `tau2_anchor.py`
(`--modes vote|policy`, `--vote-k 3 --vote-temperature 0.7 --policy-top-k 3`); report `reports/anchor/REPORT_vote_policy.md`.

- **vote**: at p_max < 0.8 the step is generated 3 times (the configured temperature-0 call plus two at T=0.7) and the
  majority *action* (tool name vs message) is kept; ties go to the cold sample. Fired on 736 / 1998 steps (37%).
- **policy**: at p_max < 0.8 the three policy sections most relevant to the request and to Jev's top-two actions are
  retrieved (deterministic IDF-weighted lexical match over the ##/### sections, heading and action-name bonuses) and
  appended as a note, replacing the generic deliberation text. Fired on 683 / 1950 steps (35%).
- **policy + reasoner**: the same note, and the step generated by deepseek-reasoner.

| run | pass^1 | pass^2 | pass^3 | pass^4 | pass@4 | flaky | always fail | LLM calls/step | $/ep (table) | anchor activity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 76.0% | 68.0% | 63.0% | 60.0% | 88.0% | 28% | 12% | 1.00 | 0.0072 | – |
| deliberate + reasoner (round 2b) | **82.0%** | **77.0%** | **74.0%** | **72.0%** | 90.0% | **18%** | 10% | 1.00 | 0.0117 | 30% of steps |
| policy | 77.5% | 71.3% | 67.0% | 64.0% | 86.0% | 22% | 14% | 1.00 | 0.0098 | note on 35% of steps |
| policy + reasoner | 79.0% | 71.7% | 66.5% | 62.0% | 90.0% | 28% | 10% | 1.00 | 0.0113 | note + reasoner on 35% |
| vote | 74.5% | 66.3% | 60.5% | 56.0% | 86.0% | 30% | 14% | 1.67 | 0.0143 | vote on 37% of steps |

Paired vs baseline (successes out of 4): policy +7 / −6 / same 37; policy+reasoner +9 / −7 / same 34; vote +5 / −9 / same 36.
Paired bootstrap (10 000 task resamples): policy Δpass^1 +1.5 [−4, +7.5] P(>0)=0.66, Δpass^4 +4 [0, +10] P=0.87;
policy+reasoner Δpass^1 +3 [−2, +9] P=0.83, Δpass^4 +2 [−10, +14] P=0.57; vote Δpass^1 −1.5 [−5.5, +2.5] P=0.19,
Δpass^4 −4 [−14, +6] P=0.15. Spend: DeepSeek 11.48 CNY (6358.96 → 6347.48, three runs + two 2-task smokes), Jev $1.12
(OpenRouter usage 11.02 → 12.14).

### Reading

1. **Resampling at a fixed history does not reproduce the forks.** In the vote run the two hot samples agreed with the
   cold sample on 88% of the uncertain steps' extra samples, and only 105 of 736 votes (14%) saw any disagreement
   (92 of them tool-vs-message); the majority overturned the cold answer 57 times. Across trials, the same
   steps fork about 20% of the time per aligned step. So the instability measured by pass^k is driven by
   differences in the *context* (user-simulator wording, earlier choices), not by sampling noise at the step —
   exactly the "decision stability under input perturbation" framing. Voting cannot fix what it cannot see, and its
   57 overturns did not help (episodes with an overturned vote succeeded 65% vs 78% without; confounded by step
   difficulty). Cost +67% LLM calls on top of that.
2. **Targeted policy retrieval is at best a weaker version of the deliberation note.** policy alone is +1.5 / +4 with
   flaky 22%, policy+reasoner +3 / +2 — both below deliberate (+3.5 / +2) and well below deliberate+reasoner (+6 / +12).
   The injected sections were mostly Modify / Book / Cancel / General rules (577 / 451 / 374 / 319 of 2049 injections);
   with a 7.7 kB policy already in the system prompt, repeating 3 kB of it adds little beyond the instruction to check
   it, and the lexical retriever ranks the cabin/basic-economy definitions and the booking section over the
   cancellation rules on some cancel requests.
3. **Where the remaining gains are.** The best lever so far is a stronger generator plus an explicit "check the
   preconditions" instruction at the Jev-uncertain steps. What neither variant here addresses is *which* branch is
   right at a fork: the 固化 thread's zero-cost result (a cancellation-eligibility predicate flags 16 cancel calls,
   all in failed episodes) points at certified hard constraints at those steps as the next thing to test.

## Round 4: retail validation (2026-10-25)

Retail, all 114 tasks × 4 trials, seed 300, DeepSeek direct (`deepseek-chat` agent and user), τ² HEAD 0c69df4. `deliberate,reasoner` at Jev p_max < 0.8 (reasoner `deepseek-reasoner`). Rules / consistency checks are airline-policy specific and were not used. Comparison: `reports/anchor/retail_compare.json` (`examples/determinism/retail_compare.py`).

| config | pass^1 | pass^2 | pass^3 | pass^4 | flaky | always-fail |
|---|---|---|---|---|---|---|
| baseline | 82.7 | 75.0 | 70.2 | 66.7 | 28.1% | 5.3% |
| deliberate+reasoner | 84.4 | 77.8 | 73.9 | 71.1 | 24.6% | 4.4% |

Paired bootstrap (task resampling): Δpass^1 +1.8 [−2.4, +5.7] P=0.79; Δpass^2 +2.8 [−2.8, +8.3] P=0.83; Δpass^4 +4.4 [−3.5, +12.3] P=0.85; tasks better/worse 23/14. Reasoner triggered on 1775 of 5433 agent steps (33%, same share as airline).

Reading: same direction as airline (every pass^k up, flaky down), but smaller and not significant on its own; retail baseline is already strong (pass^1 83 vs airline 76), leaving less room.

Deviation: in τ² HEAD, retail tasks with NL assertions are judged by an OpenAI model that is not reachable here (403). The judge was replaced with `deepseek-chat` at T=0 (`--nl-judge`), identically for both arms. Must be stated in the paper.

Cost: DeepSeek ¥47.6 and Jev $2.28 in total, of which roughly ¥20 + $0.7 was wasted on simulations that crashed in the judge before the fix (each retried 4×).

## Round 4b: retail with retail-specific consistency checks (2026-10-25)

Checks: `src/gdopt/adapters/tau2_retail_rules.py`, audited on the 912 logged retail episodes (`examples/determinism/retail_rule_audit.py`, `reports/determinism/retail_rule_audit.json`). Active: status precondition, cancel reason vs user's words, refund method, unavailable/different-product new item, option count (total vs available variants), dollar arithmetic in agent messages (hard); transfer to human with an unattempted in-scope request (soft). Not active: order not mentioned, address not typed by user, payment kind not mentioned, partial item list — they fire mostly in successful episodes. Active checks fire in ~34 of 150 logged failures.

| config | pass^1 | pass^2 | pass^3 | pass^4 | flaky | always-fail |
|---|---|---|---|---|---|---|
| baseline | 82.7 | 75.0 | 70.2 | 66.7 | 28.1% | 5.3% |
| deliberate+reasoner | 84.4 | 77.8 | 73.9 | 71.1 | 24.6% | 4.4% |
| + retail consistency checks | 86.6 | 79.2 | 74.1 | 70.2 | 27.2% | 2.6% |

Paired bootstrap: vs baseline Δpass^1 +3.9 [−0.4, +8.3] P=0.96, Δpass^4 +3.5 [−5.3, +12.3] P=0.76 (tasks 23/16); vs deliberate+reasoner Δpass^1 +2.2 P=0.88, Δpass^4 −0.9 P=0.37 (tasks 20/14).

Fires: 26 corrections in 24 of 456 episodes (option_count 10, transfer_in_scope 15, arithmetic 1); the action changed 8 times. The targeted option-count tasks 2/3/4 went from 5/12 (deliberate+reasoner) to 11/12 successes. Overall the checks raise pass^1 but not pass^4: they fire too rarely to move consistency on retail, where most failures stem from the user simulator (changed minds, reasons that differ from the gold) rather than from checkable agent errors.

Cost: DeepSeek ¥14.75 (6286.85 → 6272.10), Jev $1.02 (OpenRouter usage 15.36 → 16.38 of 20).
