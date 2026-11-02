# Spec pinning from the first divergence (airline E4 flaky failures, 2026-11-02)

Mode `specpin` (`tau2_rules.py`): after the customer's first two turns, deepseek-chat extracts a typed spec of the
request (intents, reservation ids, cabin, flight criterion, time constraints, passengers, bags, insurance, payment and
refund preference); it is then kept as a system note in every prompt with four instructions: lead with the option that
best meets the stated criterion, computed exactly, without volunteering extra alternatives; if the customer departs
from the pinned request, state old vs new and ask them to confirm (follow the new wish if confirmed); take every
attribute of a new booking from what the customer said, never from the old reservation; finish every step of an agreed
multi-step plan.

Replay: the 33 E4 flaky failures, cut at the first divergence from the closest successful trial (`spec_flagged.json`,
same cuts as PONR.md), one continuation, E4 + specpin. Control = the E4 continuation from the same cuts in PONR.md
(same seed, run on 2026-10-31).

| arm | successes / 33 |
|---|---|
| E4 (control, PONR run) | 16 (48%) |
| E4 + spec pinning | 13 (39%) |

Paired 3 better / 6 worse; by task (spec / control): 15 2/4, 16 2/3, 23 2/2, 29 0/1, 33 2/2, 42 2/0, 44 0/1, others
equal. No improvement (the difference is within one-run noise, but the sign is negative).

Why it failed where it was aimed (tasks 15/16): the spec was extracted correctly ("cheapest economy, day after") and the
agent did announce departures ("you first asked for the cheapest ($207), you are now choosing $216 … confirm?"), but the
simulated user simply confirmed the change. The drift is triggered earlier, by the agent first presenting the wrong
"cheapest" ($216 via ORD) and then correcting itself to $207 with its midnight arrival. Across all 2800 logged episodes,
task 16 succeeds in 28/34 trials where the first price the agent quotes is the true cheapest $207 vs 7/22 where it is
$216 (task 15: 10/20 vs 21/36, no difference). So in 16 the lever is computing the right answer before the first
presentation (a deterministic "cheapest itinerary" executor over the search results), not pinning the request.

Conclusion: putting the request in the prompt does not change what the agent gets wrong (its own computation and
selection) and cannot stop a simulated user that changes its mind; asking for confirmation of a change only adds turns.

Cost: DeepSeek ¥0.99 by balance (6233.93 → 6232.94, billing may lag), Jev $0.095 (OpenRouter 17.40 → 17.49 of 20).
