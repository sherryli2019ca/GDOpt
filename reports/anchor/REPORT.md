# pass^k comparison

50 tasks × 4 trials per run.

| run | pass^1 | pass^2 | pass^3 | pass^4 | pass@4 | flaky | always fail | steps/ep | $/ep | Jev $/ep | LLM calls/step | hints/step | vetoes/step | veto changed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 76.0% | 68.0% | 63.0% | 60.0% | 88.0% | 28% | 12% | 10.9 | 0.0072 | 0.0000 | 1.00 | 0% | 0.0% | – |
| hint | 75.0% | 69.3% | 66.5% | 64.0% | 86.0% | 22% | 14% | 10.7 | 0.0093 | 0.0021 | 1.00 | 42% | 0.0% | – |
| veto | 76.0% | 68.0% | 63.5% | 60.0% | 90.0% | 30% | 10% | 10.6 | 0.0089 | 0.0020 | 1.00 | 0% | 0.0% | – |
| checklist | 71.0% | 62.0% | 57.5% | 56.0% | 86.0% | 30% | 14% | 10.9 | 0.0096 | 0.0020 | 1.00 | 0% | 0.0% | – |
| deliberate | 79.5% | 70.7% | 65.5% | 62.0% | 94.0% | 32% | 6% | 10.9 | 0.0122 | 0.0023 | 1.00 | 0% | 0.0% | – |
| reasoner | 80.0% | 73.3% | 69.5% | 66.0% | 92.0% | 26% | 8% | 10.8 | 0.0105 | 0.0020 | 1.00 | 0% | 0.0% | – |
| deliberate_reasoner | 82.0% | 77.0% | 74.0% | 72.0% | 90.0% | 18% | 10% | 10.5 | 0.0117 | 0.0020 | 1.00 | 0% | 0.0% | – |
| deliberate_all | 75.5% | 64.3% | 57.5% | 52.0% | 94.0% | 42% | 6% | 9.7 | 0.0118 | 0.0000 | 1.00 | 0% | 0.0% | – |

## Per-task successes out of 4 (vs baseline)

- hint: more successes on 7 tasks, fewer on 8, same on 35
- veto: more successes on 11 tasks, fewer on 9, same on 30
- checklist: more successes on 4 tasks, fewer on 13, same on 33
- deliberate: more successes on 10 tasks, fewer on 6, same on 34
- reasoner: more successes on 10 tasks, fewer on 6, same on 34
- deliberate_reasoner: more successes on 9 tasks, fewer on 3, same on 38
- deliberate_all: more successes on 10 tasks, fewer on 12, same on 28
