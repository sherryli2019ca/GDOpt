# GDOpt stage-2 profiles on τ²-bench traces

Source: result files shipped in `tau2-bench/data/tau2/results/final/` (4 trials per task; the user simulator
is GPT-4.1 in every run). Situations are fitted on trials 0–1 and every number below is measured on the
held-out trials 2–3. Generated with `gdopt profile ... --out-dir reports/tau2`.

"Closed tool steps" are agent steps that call a tool whose every argument is a copy of a value already in the
context (a user-given id, a field of an earlier tool result). Such a step needs no generative model: a decision
model picks the tool, the arguments come from the entity table. "Max saving" is the share of agent cost spent
on those steps, net of Jev's price, i.e. the ceiling for stages 3–4.

| agent | domain | test steps | closed tool steps | max saving | code-tier situations (steps) |
| --- | --- | ---: | ---: | ---: | --- |
| GPT-4.1 | airline | 1107 | 16.6% | 15.9% | 0 |
| GPT-4.1 | retail | 2787 | 13.1% | 11.8% | 0 |
| GPT-4.1 | telecom | 4118 | 24.0% | 25.5% | 1 (228, 5.5%) |
| Claude 3.7 Sonnet | airline | 1417 | 26.0% | 27.9% | 0 |
| Claude 3.7 Sonnet | retail | 3376 | 16.1% | 17.2% | 0 |
| Claude 3.7 Sonnet | telecom | 4237 | 20.0% | 19.4% | 2 (228, 5.4%) |
| o4-mini | airline | 1062 | 20.9% | 21.1% | 0 |
| o4-mini | retail | 3187 | 14.9% | 15.6% | 0 |
| o4-mini | telecom | 4264 | 29.9% | 28.1% | 1 (223, 5.2%) |

## What the profiles say

1. **13–30 % of agent steps are closed tool calls.** They are the only steps that can skip the LLM entirely;
   every other step either sends a message (text still needs a generative model) or has an open argument
   (`calculate(expression)`, `transfer_to_human_agents(summary)`, lists of flights or passengers).
2. **One code-tier situation is found automatically in telecom, by all three agents:**
   `n_tool_calls=0 & have:phone_number=1 -> get_customer_by_phone(phone_number=<latest>)`, 100 % of the
   time on held-out trials, arguments reproduced by the latest-entity rule. It is 3–4 % of agent cost and
   needs no model at all.
3. **Most situations have real entropy (0.3–0.6 normalized)** because the message-vs-tool choice depends
   on what the user said, not only on the structural features. That is the part a decision model has to
   resolve; stage 3 (shadow Jev calls) decides which of these situations are safe.
4. **The latest-entity rule fills arguments correctly in most closed situations** (85–100 % where a tool is
   the majority action), so argument filling is not the bottleneck; action choice is.
5. The Jev/LLM input price ratio is 0.013 (Claude 3.7) to 0.06 (o4-mini), so the cost condition
   `p_fallback < 1 - ratio` is met in every situation; thresholds only trade accuracy and latency.

Next: run `gdopt.shadow.shadow_evaluate` with `OpenRouterJev` on the `jev` candidates of one domain (≈1–4k
calls, well under a dollar at Jev prices), then plug `TieredPolicy` into τ²-bench's orchestrator for
counterfactual replay and calibration.
