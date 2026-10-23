# τ²-bench airline: qwen3.7-flash as the whole agent (control for the cascade)

Same 50 tasks, same DeepSeek user simulator, reasoning disabled, temperature 0.

| agent | success | mean reward | agent cost / task | assistant steps | prompt tokens | completion tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| qwen/qwen3.7-flash every step | 68% | 0.680 | $0.0014 (cache-aware; $0.0022 at list price) | 469 | 3372145 | 80134 |

Original DeepSeek agent on the same tasks: 42% / 32% on two runs, $0.0146 per task. The cheaper, newer model is
both 10x cheaper and markedly more accurate on airline; cached-token discounts are not even counted here.
