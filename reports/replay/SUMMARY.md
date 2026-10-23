# Stage 3b/4 replay on τ²-bench airline: original agent vs tiered agent

Setup: τ²-bench airline, the first 50 tasks, one trial each, seed 300. Agent and user simulator are
`deepseek/deepseek-chat` through OpenRouter (temperature 0); the decision model is `typesafe/jev-1.14`.
Situations and tier thresholds come from the offline stages on the shipped GPT-4.1 traces
(`gdopt profile` + `gdopt shadow` with tool descriptions). The tiered agent (`TieredLLMAgent`) executes a
cheap-tier *tool* decision without calling the LLM when the situation is in the Jev tier, Jev's confidence is
at least the situation's τ, and every argument can be filled from the entity table; everything else (and
every "send a message" decision) goes to the LLM. Costs are OpenRouter prices for the agent LLM plus the Jev
calls (≈ $0.00018 each vs ≈ $0.0022 per DeepSeek step, ratio ≈ 8 %); the user simulator is not counted.
`communicate_info` is scored with τ²'s original substring rule (its new default is an OpenAI judge).

| run | success | assistant steps | steps with LLM call | Jev calls | steps without LLM | cost / task | of which Jev | cost vs run 1 | marginal net saving | notes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| original, run 1 | 42% | 349 | 349 (100.0%) | 0 | 0 | $0.0146 | $0.00000 | -0.0% | +0.0% | LLM every step |
| original, run 2 | 32% | 363 | 363 (100.0%) | 0 | 0 | $0.0148 | $0.00000 | +1.5% | +0.0% | same config, repeated: run-to-run noise |
| tiered v1 | 44% | 511 | 439 (85.9%) | 451 | 72 | $0.0303 | $0.00344 | +107.7% | +3.2% | before the id-shape fix and loop guard |
| tiered v2 | 44% | 402 | 357 (88.8%) | 324 | 45 | $0.0168 | $0.00113 | +15.1% | +5.0% | all 16 Jev situations, per-situation τ from shadow |
| tiered v3 | 40% | 370 | 346 (93.5%) | 71 | 24 | $0.0144 | $0.00020 | -0.9% | +5.5% | cost-aware table: 5 Jev situations with confident-tool coverage ≥ 0.16 |

"Marginal net saving" is the noise-free accounting inside the tiered run: (steps without LLM) × (mean LLM
step cost in that run) − (all Jev calls), as a share of the run's cost. "Cost vs run 1" is the raw total,
which also carries dialogue-length noise.

## What the replay showed

1. **The replay found two defects the offline stages could not see.** In v1 the entity table had no learned
   shape for airline reservation ids (the coarse-shape rule demanded a digit in 90 % of values; ids like
   `IFOYYZ` have none), so a user correction ("it's actually M20IZO") was not picked up and the "latest
   entity" rule re-filled the stale id; nothing stopped the cheap tier from repeating the same call, so one
   task ran a 90-step loop (and the LLM, once it fell back, imitated the loop). Fixes: digit majority suffices
   for an id shape; a cheap tier never repeats a call already made since the last user turn ("duplicate
   call" fallback). Both have tests. This is the argument for stage 3b: shadow agreement (78 %) said nothing
   about argument filling or dynamics.
2. **Accuracy is within run-to-run noise.** The same original agent scored 42 % and 32 % on two runs (5 of 50
   tasks flipped), so one trial resolves differences of roughly ±10 points only. Tiered v2/v3 scored 44 % /
   40 %, paired outcomes vs run 1: v2 lost 2 tasks and gained 3, v3 lost 3 and gained 2. No sign of a
   systematic accuracy drop at this sample size, and no ability to certify one either — the Learn-then-Test
   calibration needs several hundred paired tasks (pool domains, more trials).
3. **The cost saving is real but small, and the cost condition bites.** In v2 Jev was consulted on 324 of 402
   steps and acted on 45 (fallback rate 86 %, break-even 92 %): gross saving 11 % of LLM calls, half of it
   eaten by Jev calls, net ≈ 5 %. The reason is structural: Jev's confident decision is usually *message*
   (which still needs the LLM for the text) or a tool with an open argument. v3 keeps only situations whose
   confident-*tool* coverage on the shadow data is ≥ 0.16 (twice break-even): 5 situations instead of 16, Jev
   calls 324 → 71, fallback rate 66 %, the same net ≈ 5.5 %, raw cost −1 % vs run 1 instead of +15 %. The
   cheap tier executed `get_user_details`, `get_reservation_details` and one `search_direct_flight` — the
   opening lookups, exactly what stage 2 predicted.
4. **Raw totals are dominated by dialogue length.** Episodes of the same task vary from 3 to 10 LLM steps
   between runs with no cheap-tier intervention at all (task 37), so the +15 % raw cost of v2 is mostly noise
   plus the extra tool lookups the cheap tier makes where the LLM would have asked first.
5. **The ratio matters.** With DeepSeek the Jev/LLM step cost ratio is ≈ 8 %; with GPT-4.1 ($2/M input) it is
   ≈ 1 %, so the net saving approaches the gross share of skipped steps (≈ 11 % here, ceiling 12–28 % from
   stage 2). The cost-aware tier table (`min_tool_coverage`) is the knob to set from that ratio.

## Files

- `airline/`: original run 1 (`baseline.json`) and tiered v2 (`tiered.json`, `tier_table.json`, `REPORT.md`).
- `airline-baseline-rep2/`: original run 2.
- `airline-v1-before-guard/`: tiered v1 with the loop (kept as evidence; `REPORT.md`).
- `airline-v3-cost-aware/`: tiered v3 (`REPORT.md` compares with run 1).

## Next

Retail and telecom replays (telecom has the only code-tier rule); two or more trials per task so the
paired comparison can detect ≤ 5-point drops; then pool domains for the Learn-then-Test calibration of λ.
