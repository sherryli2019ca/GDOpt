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
