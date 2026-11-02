# RSI full run: E4 + mined checks, airline 50×4 (2026-10-30)

`--modes deliberate,reasoner,rules,consistency --mined reports/rsi/r1.json`, seed 300, τ² HEAD 0c69df4, DeepSeek direct,
run as three fold-isolated sub-runs (`--task-ids <fold k> --mined-exclude-fold k`): every task ran only with checks
mined from other tasks. Outputs `reports/anchor/airline-e4_mined-fold{0,1,2}`, comparison `full_compare.json`
(`examples/determinism/rsi_full_compare.py`).

**The mined checks never fired** (0 fires in 200 episodes; also 0 when the 4 predicates are re-run offline on this
run's calls). At the E4 configuration the agent no longer makes the four mistakes they target — the same pattern as the
certified rules in E3 (2 fires in 1947 steps on top of the reasoner). The run is therefore a replication of E4.

| config | pass^1 | pass^2 | pass^3 | pass^4 | flaky tasks |
|---|---|---|---|---|---|
| baseline | 76.0 | 68.0 | 63.0 | 60.0 | 14 |
| E4 run 1 (2026-10-25) | 84.5 | 81.0 | 78.5 | 76.0 | 7 |
| E4 run 2 (this run, + mined checks that never fired) | 81.0 | 76.3 | 74.0 | 72.0 | 9 |
| E4 pooled, 8 trials/task | 82.8 | 78.4 | 75.9 | 74.1 | 11 |
| deliberate+reasoner pooled, 8 trials/task | 81.8 | 75.8 | 71.8 | 68.9 | 15 |

Run 2 vs run 1: Δpass^1 −3.5 [−8.5, +0.5], Δpass^4 −4 [−12, +4], tasks 3 better / 6 worse — run-to-run spread,
as with deliberate+reasoner (72 vs 64). Pooled E4 vs baseline: Δpass^1 +6.8 [+1.2, +13.2] P=0.99, Δpass^4 +14.1
[+2.7, +26.7] P=0.99. Pooled E4 vs pooled deliberate+reasoner: Δpass^1 +1.0 P=0.63, Δpass^4 +5.1 [−4.7, +14.9] P=0.85.

Reading: (1) E4 now has the two runs the paper rule asks for; its pass^4 settles at ≈ 74 (the single-run 76 was
slightly optimistic). (2) Checks mined from logs of weaker configurations (13 runs, mostly without reasoner/consistency)
target mistakes the current best agent has already stopped making; R2's 12/31 vs 5/31 measured rescue on logged
failures from those weaker runs. For RSI to add to E4, the next round must mine from failures of E4 itself.

Cost: DeepSeek balance 6268.65 → 6257.98 (¥10.67, about twice E4's ¥5.35 although the agent-side cost tables are the
same, $1.88 vs $1.91; the difference could not be attributed — the key may be shared with other work), Jev $0.38
(OpenRouter usage 16.466 → 16.848 of 20).
