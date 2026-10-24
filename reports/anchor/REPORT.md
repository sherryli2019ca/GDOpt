# pass^k comparison

50 tasks × 4 trials per run.

| run | pass^1 | pass^2 | pass^3 | pass^4 | pass@4 | flaky | always fail | steps/ep | $/ep | Jev $/ep | LLM calls/step | hints/step | vetoes/step | veto changed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 76.0% | 68.0% | 63.0% | 60.0% | 88.0% | 28% | 12% | 10.9 | 0.0072 | 0.0000 | 1.00 | 0% | 0.0% | – |
| hint | 75.0% | 69.3% | 66.5% | 64.0% | 86.0% | 22% | 14% | 10.7 | 0.0093 | 0.0021 | 1.00 | 42% | 0.0% | – |
| veto | 76.0% | 68.0% | 63.5% | 60.0% | 90.0% | 30% | 10% | 10.6 | 0.0089 | 0.0020 | 1.00 | 0% | 0.0% | – |
| checklist | 71.0% | 62.0% | 57.5% | 56.0% | 86.0% | 30% | 14% | 10.9 | 0.0096 | 0.0020 | 1.00 | 0% | 0.0% | – |

## Per-task successes out of 4 (vs baseline)

- hint: more successes on 7 tasks, fewer on 8, same on 35
- veto: more successes on 11 tasks, fewer on 9, same on 30
- checklist: more successes on 4 tasks, fewer on 13, same on 33
