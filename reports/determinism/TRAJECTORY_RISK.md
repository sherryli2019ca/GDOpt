# Trajectory-level stability risk from Jev confidence (2026-10-24, zero API cost)

Script: `examples/determinism/trajectory_risk.py` (reads `reports/anchor/airline-*/results.json`, writes
`reports/determinism/trajectory_risk.json`). Data: airline, 50 tasks x 4 trials, DeepSeek agent; Jev p_max logged at
every step in the veto / hint / deliberate / reasoner runs (800 episodes). Framing: decision stability under input
perturbation.

## Step level: Jev p_max is a calibrated fork hazard

For every pair of trials of the same task, walk the shared prefix; at each aligned step record min(p_i, p_j) and
whether the next actions differ (first divergence).

| p_max | veto run (no intervention) | all 4 runs |
| --- | --- | --- |
| < 0.5 | 29.0% (31/107) | 27.0% |
| 0.5-0.6 | 21.9% | 19.9% |
| 0.6-0.7 | 17.8% | 22.4% |
| 0.7-0.8 | 20.6% | 21.4% |
| 0.8-0.9 | 12.1% | 11.7% |
| 0.9-0.95 | 2.2% | 6.8% |
| >= 0.95 | 0.3% (2/582) | 1.3% |

Mixed-outcome pairs vs same-outcome pairs differ only 0.75-2.2x within a bin: Jev sees *that* a step may fork, not
*which* branch fails.

## Trajectory level: sums of per-step risk mostly measure length

| check | Jev score | length control |
| --- | --- | --- |
| task flaky AUC (per run) | cumulative surprisal 0.67-0.77 | steps 0.76-0.82 |
| cross-run (score from run A, flaky in run B, 24 pairs) | 0.69 | 0.76 |
| leave-one-out logistic | steps + Jev 0.61-0.80 | steps only 0.70-0.77 |
| ex-ante prefix, first k = 2/3/4/6 steps | 0.29 / 0.48 / 0.45 / 0.50 | n/a |
| online, alive at t = 3/5/8/12 -> final failure | 0.43 / 0.48 / 0.46 / 0.50 | n/a |
| within flaky task: failed vs succeeded trial (54 groups) | min p 0.61 [0.52, 0.69] | steps 0.58 [0.49, 0.66] |
| trial-pair action divergence (861 / 1200 pairs) | calibrated hazard risk 0.72 | 0.71 |

Scores normalised by length (mean surprisal, share of p < 0.8) are near 0.5. Flaky tasks have *more* confident
openings (first-2-step mean surprisal 0.07-0.15 vs 0.26-0.27 for always-pass tasks). Weighting uncertain steps by
"a write tool is in Jev's top-2" (deliberate run) lowers AUC to 0.58.

Reading: claim per-step stability (hazard curve) + localisation + targeted hardening; do not claim that a Jev
trajectory score forecasts flaky tasks beyond length. Next (needs approval): perturbation probe per step, and a
consequence question (policy-allowed?) to estimate c_t; log the full Jev distribution in future runs.
