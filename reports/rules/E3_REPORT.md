# pass^k comparison

50 tasks × 4 trials per run.

| run | pass^1 | pass^2 | pass^3 | pass^4 | pass@4 | flaky | always fail | steps/ep | $/ep | Jev $/ep | LLM calls/step | hints/step | vetoes/step | veto changed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 76.0% | 68.0% | 63.0% | 60.0% | 88.0% | 28% | 12% | 10.9 | 0.0072 | 0.0000 | 1.00 | 0% | 0.0% | – |
| best | 82.0% | 77.0% | 74.0% | 72.0% | 90.0% | 18% | 10% | 10.5 | 0.0117 | 0.0020 | 1.00 | 0% | 0.0% | – |
| best_rules | 81.5% | 73.7% | 68.0% | 64.0% | 92.0% | 28% | 8% | 10.6 | 0.0119 | 0.0020 | 1.00 | 0% | 0.0% | – |

## Per-task successes out of 4 (vs baseline)

- best: more successes on 9 tasks, fewer on 3, same on 38
- best_rules: more successes on 10 tasks, fewer on 4, same on 36
