# Solidified policy rules — E1 audit and E2 replay (airline, 2026-10-25)

Scripts: `examples/determinism/clause_audit.py` (E1), `examples/tau2_rule_replay.py` (E2); rules and agent in
`src/gdopt/adapters/tau2_rules.py`. Model: DeepSeek direct `deepseek-chat` (agent and user simulator, temperature 0).

## E1 — clause audit on 1600 logged episodes (8 runs × 50 tasks × 4 trials, 1230 successes / 370 failures)

| rule | fires in successes | fires in failures | failed episodes |
| --- | --- | --- | --- |
| cancel_ineligible | 0 | 16 | 15 |
| book_payment (>1 certificate etc.) | 0 | 11 | 10 |
| cancel_flown | 0 | 10 | 10 |
| modify_basic_economy | 0 | 2 | 2 |
| bag_remove | 0 | 1 | 1 |
| confirm_before_write (regex) | 38 | 22 | 16 |

The five forbid rules: 40 fires, all in failed episodes (38 of 370 = 10%), none in 1230 successes; pooled
Clopper-Pearson 95% upper bound on harm 7.2%. The confirmation rule is not usable as written (38 fires in successes).
Rules modify_route, cabin_after_flown, pax_count, comp_* never fired.

## E2 — counterfactual replay from the step before the first violation (38 episodes, 10 base tasks)

| arm | success |
| --- | --- |
| control (plain agent continues) | 0 / 38 |
| rules enforced (1 regeneration, then refusal) | 25 / 38 (66%); task-macro 59% |

Paired: rules better 25, control better 0. Rules fired 40 times, regeneration complied 39, refusal 1.
By rule: cancel_ineligible 15/15, cancel_flown 7/10, bag_remove 1/1, book_payment 2/10, modify_basic_economy 0/2.
By task: 1 13/13, 9 4/4, 41 2/2, 18 1/1, 45 1/1, 20 2/4, 39 2/5, 14 0/4, 23 0/2, 32 0/2.
Cost ≈ 0.33 CNY (balance 6347.36 → 6347.03), no Jev.

Counterfactual pass^1 / pass^4 if the rescued episodes had succeeded (`passk_counterfactual.json`):
baseline 76/60 → 78.5/62; checklist 71/56 → 74.5/62; deliberate+reasoner 82/72 → 82.5/74;
deliberate and reasoner alone unchanged (they no longer make these calls).

Caveats: one continuation per episode per arm; control at temperature 0 mostly re-takes the logged failing action;
task 1 contributes 13 of 38 episodes; rules were hand-written from the policy, not learned, so evaluation on the same
tasks is not leakage, but the 40-fire sample is small.

## E3 — rules on top of deliberate+reasoner, airline 50×4 (2026-10-25)

`--modes deliberate,reasoner,rules`, seed 300, DeepSeek 4.80 CNY (6346.92 → 6342.12) + Jev $0.38. τ²-bench HEAD 0c69df4
(earlier runs used an older checkout). Table: `E3_REPORT.md`.

| run | pass^1 | pass^2 | pass^3 | pass^4 | flaky |
| --- | --- | --- | --- | --- | --- |
| baseline (none) | 76.0 | 68.0 | 63.0 | 60.0 | 28% |
| deliberate+reasoner (2026-10-24) | 82.0 | 77.0 | 74.0 | 72.0 | 18% |
| deliberate+reasoner+rules (this run) | 81.5 | 73.7 | 68.0 | 64.0 | 28% |
| deliberate+reasoner, both runs pooled (8 trials/task) | 81.8 | 75.8 | 71.8 | 68.9 | – |

The rules fired only twice in 1947 steps (task 14, book_payment, Jev p 0.87 and 0.83; one episode still failed), so this
run is effectively a replication of deliberate+reasoner. Its pass^1 replicates (81.5 vs 82); its pass^4 does not
(64 vs 72; paired vs the earlier run 5 tasks better / 5 worse, Δpass^4 −8 [−18, 0]). Against the baseline:
Δpass^1 +5.5 [0, +12] P(>0)=0.97, Δpass^4 +4 [−8, +16] P=0.70. Pooled over 8 trials the config gives pass^4 ≈ 69.
Reading: the reasoner fallback already removes almost all policy-forbidden writes, so the certified rules add nothing
measurable on top of it; their value is as a guard for configurations without a reasoner and as a guarantee.

## Consistency rules — local replay (2026-10-25)

New checks in `ConsistencyChecker` (`src/gdopt/adapters/tau2_rules.py`): hard `pax_dob_mismatch`; soft (reasoner
re-generates with a review note) `substitute_book`, `transfer_pending`, `price_quote` (code-computed price × passengers
when the user stated a budget), `cheapest_check` (code-ranked itineraries), `basic_economy_path` (allow-side hint when
the agent refuses a basic-economy change). Of 73 failed trials in the two pooled deliberate+reasoner runs, 44 have a
step where a check (or a certified rule) fires on the logged action; each was replayed from that step once per arm,
both arms deliberate+reasoner (Jev at p<0.8), treated arm adds rules+consistency.

| arm | success |
| --- | --- |
| control (deliberate+reasoner) | 7 / 44 (16%) |
| + rules + consistency checks | 16 / 44 (36%) |

Paired: treated better 10, control better 1. By first-firing check (treated vs control successes):
basic_economy_path 9 vs 5 of 11, transfer_pending 2 vs 0 of 9, price_quote 2 vs 1 of 10, cheapest_check 1 vs 0 of 8,
substitute_book 0 vs 0 of 4, pax_dob 1 vs 0 of 1, cancel_flown 1 vs 1 of 1. Always-failing tasks 7/29/44 (15 trials)
gain nothing. Cost DeepSeek ≈ 1.59 CNY (6341.97 → 6340.38, incl. 2-episode pilot) + Jev $0.14.

Caveat: the soft checks also fire in successful episodes (basic_economy_path 33, price_quote 31, cheapest_check 11,
transfer_pending 4 of 1393+), where the reasoner re-generation could change a correct step; only a full 50×4 run
measures the net effect on pass^k.

## E4: full airline 50×4 with consistency checks (2026-10-25)

`--modes deliberate,reasoner,rules,consistency`, seed 300, τ² HEAD 0c69df4, output `reports/anchor/airline-deliberate_reasoner_rules_consistency`, comparison `reports/rules/e4_compare.json`.

| config | pass^1 | pass^2 | pass^3 | pass^4 | flaky | always-fail |
|---|---|---|---|---|---|---|
| baseline | 76.0 | 68.0 | 63.0 | 60.0 | 28% | 12% |
| deliberate+reasoner run 1 | 82.0 | 77.0 | 74.0 | 72.0 | 18% | 10% |
| deliberate+reasoner run 2 (+rules, E3) | 81.5 | 73.7 | 68.0 | 64.0 | 28% | 8% |
| deliberate+reasoner pooled (8 trials) | 81.8 | 75.8 | 71.8 | 68.9 | 30% | 8% |
| **+ rules + consistency (E4)** | **84.5** | **81.0** | **78.5** | **76.0** | **14%** | 10% |

Paired bootstrap (task resampling, 5000 draws), E4 minus reference:

| reference | Δpass^1 [95% CI] P(>0) | Δpass^4 [95% CI] P(>0) | tasks better/worse |
|---|---|---|---|
| baseline | +8.5 [+2.5, +15.0] 1.00 | +16.0 [+4, +30] 0.99 | 13 / 4 |
| run 1 | +2.5 [−1.5, +7.0] 0.85 | +4.0 [−6, +14] 0.72 | 7 / 4 |
| run 2 | +3.0 [−2.0, +8.0] 0.87 | +12.0 [+2, +22] 0.98 | 10 / 4 |
| pooled 8 trials | +2.8 [−1.2, +7.0] 0.89 | +7.1 [−1.3, +15.8] 0.95 | 11 / 5 |

Consistency checks fired at 108 of 1954 steps (5.5%) in 71 of 200 episodes (54 successful, 17 failed); the regenerated action differed from the original 32 times. Per rule (success / failed episodes' fires): price_quote 36/16, basic_economy_path 33/8, cheapest_check 10/5, transfer_pending 4/6, substitute_book 0/1, pax_dob_mismatch 1/0. Certified forbid rules fired once. Reasoner steps 654 (33%).

Cost: DeepSeek ¥5.35 (6340.15 → 6334.80), Jev $0.41 (1713 calls; OpenRouter usage 12.67 → 13.07 of 20).

Reading: best single run so far and the first with flaky below 15%. Against the pooled 8-trial estimate of the previous best config the gain is +2.8 pass^1 / +7.1 pass^4 (P 0.89 / 0.95) — suggestive, not conclusive, and E4 is a single run (the paper rule requires ≥2 runs per config). Run-to-run spread of the same config was 8 pass^4 points (72 vs 64).
