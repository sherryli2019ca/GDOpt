# Point of no return in E4's flaky failures (airline, 2026-10-31)

For the 33 failed trials of E4's flaky tasks (`ponr_flagged.json`), the logged conversation was cut at three points and
continued once with the E4 configuration (deliberate + reasoner at Jev p < 0.8, certified rules, consistency checks):
the first divergence from the closest successful trial of the same task (median message index 2, i.e. usually the
user's opening turn), the midpoint between that and the decisive write (median 0.5 of the window), and right before the
decisive write (from the write-gate run's control arm).

| cut point | successes / 33 |
|---|---|
| first divergence from a successful trial | 16 (48%) |
| midpoint | 16 (48%) |
| right before the decisive write | 1 (3%) |

So the outcome is still open halfway through and is locked in during the last stretch before the write. In 25 of the
33 failures the decisive write is two messages after an agent message that proposes the action, followed by the user's
"yes" (in 32 of 33 the last agent text message is exactly 2 messages before the write): the **agent's proposal turn**
is the commitment point — once a wrong plan is put to the user and confirmed, every model makes the write.

By task (first-divergence cut): 15 4/4, 16 3/3, 33 2/2, 6/8/45 1/1, 23 2/5, 29 1/7, 44 1/6, 14 0/1, 42 0/2 — tasks 29
and 44 stay mostly lost even from the start (their failures are close to "always" under E4).

Implication for stability: intervene at the proposal turn (before the agent asks the user to confirm a write), not at
the write. Next test: cut right before the proposal message to confirm it is the boundary, then a "proposal gate"
(independent derivation of the plan by the reasoner before it is presented).

Cost: DeepSeek ¥2.63 (6252.99 → 6250.36), Jev $0.18 (OpenRouter usage 16.99 → 17.17 of 20).
