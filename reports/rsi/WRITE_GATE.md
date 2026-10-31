# Write gate — counterfactual replay (airline, 2026-10-31)

Mode `writegate` (`src/gdopt/adapters/tau2_rules.py`): whenever the agent's step contains a write or a transfer to a
human, deepseek-reasoner re-derives the step independently from the same context (without seeing the proposed call);
if the write calls differ (transfers compared by name only), neither is executed and the step is regenerated with a
note listing both readings and asking the agent to confirm the exact details with the user first.

Replay points (`wg_flagged.json`, from `e4_forks.py`): the 33 failed trials of E4's flaky tasks, cut right before
their decisive write (first write-level difference from the closest successful trial of the same task), and 33
successful trials of the same tasks cut before their corresponding / first write (harm check; one could not be
replayed, 32 ran). Both arms run the E4 configuration; the treated arm adds the write gate. One continuation each.

| replay points | control (E4) | E4 + write gate |
|---|---|---|
| failed trials, at the decisive write (33) | 1 | 0 |
| successful trials, at a write (32) | 30 | 30 |

The gate checked 97 write steps and disagreed on 13. **At the decisive wrong write, the independent reasoner proposed
the same wrong write in 27 of 33 episodes**, and even the control arm rescued only 1 of 33 from that point.

Reading: by the time of the decisive write the failure is already fixed by the conversation so far — a second,
stronger model reading the same context makes the same choice. Like the fixed-context vote (14% split), this is
direct evidence that the instability is in the context (what the user simulator and the agent said earlier), not in
the write step itself; checks at the write cannot recover it. No harm on successful trials (30 vs 30).
The point of no return lies between the first divergence from a successful trial (median message index 2, i.e. usually the
user's opening turn; 19 of 37 user-first) and the decisive write.

Cost: DeepSeek ¥1.88 (6254.87 → 6252.99), Jev $0.14 (OpenRouter usage 16.85 → 16.99).
