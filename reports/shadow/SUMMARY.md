# Local verification with Jev on τ²-bench traces (GPT-4.1 agent)

`gdopt shadow` on 400 sampled held-out steps per domain from the candidate situations, model
`typesafe/jev-1.14` via OpenRouter, state = domain policy + full conversation, question = "what is the
agent's correct next action?" over the menu {message, tool:<name> ...}. No calibration, no replay.
Cost: about $0.07 per domain (≈ $0.00018 per call), 0.6–0.7 s per call.

| domain | agreement with LLM | on successful trajectories | ECE | agreement @ p ≥ 0.9 (steps kept) | agreement @ p ≥ 0.8 (kept) | decidable disagreements: LLM right / Jev right |
| --- | ---: | ---: | ---: | --- | --- | --- |
| airline | 78.2% | 80.9% | 0.031 | 95.6% (45.5%) | 92.2% (61.3%) | 11 / 1 |
| retail | 81.2% | 82.6% | 0.059 | 98.8% (42.5%) | 95.8% (65.2%) | 23 / 0 |
| telecom | 72.5% | 76.2% | 0.085 | 100% (24.8%) | 88.4% (41.0%) | 1 / 2 |

## Where the disagreements are

| domain | LLM sent a message: Jev agrees | LLM called a tool: Jev agrees | both chose a tool: same tool |
| --- | ---: | ---: | ---: |
| airline | 221 / 236 (93.6%) | 92 / 164 (56.1%) | 92 / 101 (91.1%) |
| retail | 210 / 220 (95.5%) | 115 / 180 (63.9%) | 115 / 118 (97.5%) |
| telecom | 225 / 261 (86.2%) | 65 / 139 (46.8%) | 65 / 92 (70.7%) |

Reading:

1. **Jev is calibrated.** ECE 0.03–0.09, and the coverage curve is monotone: at p_max ≥ 0.9 it agrees with
   the LLM 96–100 % of the time while covering 25–46 % of steps. Those are the steps a tiered policy would
   take without the LLM; the rest fall back.
2. **The dominant failure is "message instead of tool", not the wrong tool.** When the LLM called a tool,
   Jev chose *send a message* in 36–53 % of cases; when both chose a tool they picked the same one 91–98 % of
   the time in airline/retail (71 % in telecom, which has many similar diagnostic tools). Jev is
   conservative: it prefers asking or confirming. Those steps are "undecidable" by the reference actions
   because a message is never a reference action.
3. **On decidable disagreements the LLM is usually right** (airline 11:1, retail 23:0), i.e. when Jev picks
   a different tool it is mostly a mistake. Telecom is the exception (1:2) but the counts are tiny.
4. **Situations differ a lot.** Opening situations (no tool calls yet) are at 93–100 % agreement with 80–100 %
   coverage at p ≥ 0.9; mid-conversation situations after several tool calls are at 55–75 % agreement with
   5–50 % coverage. The per-situation tables in the `.shadow.md` files are the input to the tier table.

## What this means for the design

* The tier table should use per-situation thresholds from these coverage curves (`TierTable.from_profile(...,
  shadow=local.by_situation())` does exactly that with `min_agreement`), not one global cut.
* The message-vs-tool bias suggests two cheap fixes to try next: (a) add short tool descriptions to the menu
  (the shadow run used tool names only, since τ²-bench result files do not carry descriptions), and (b) a
  two-stage question, Noul "does the agent need to call a tool now?" then Choice over tools.
* Agreement with GPT-4.1 is a proxy. The reference-action check settles only tool-vs-tool disagreements;
  message-vs-tool disagreements need counterfactual replay (stage 3b), which is the next experiment.

## Variants: tool descriptions and a two-stage question (same 400 sampled steps per domain)

| domain | variant | agreement | on success | ECE | @ p≥0.9 (kept) | @ p≥0.8 (kept) | LLM called tool: agree | LLM sent msg: agree | same tool when both tool (n) | LLM right / Jev right |
| --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: |
| airline | baseline (names only) | 78.2% | 80.9% | 0.031 | 95.6% (45.5%) | 92.2% (61.3%) | 56.1% | 93.6% | 91.1% (101) | 11 / 1 |
| airline | + tool descriptions | 78.8% | 83.3% | 0.045 | 95.5% (49.8%) | 91.0% (66.5%) | 56.1% | 94.5% | 92.0% (100) | 11 / 0 |
| airline | + descriptions, two-stage | 74.0% | 76.6% | 0.069 | 98.8% (20.0%) | 87.8% (57.2%) | 37.2% | 99.6% | 95.3% (64) | 21 / 1 |
| retail | baseline (names only) | 81.2% | 82.6% | 0.059 | 98.8% (42.5%) | 95.8% (65.2%) | 63.9% | 95.5% | 97.5% (118) | 23 / 0 |
| retail | + tool descriptions | 86.2% | 88.4% | 0.054 | 98.9% (45.8%) | 98.0% (63.5%) | 75.0% | 95.5% | 97.1% (139) | 15 / 0 |
| retail | + descriptions, two-stage | 75.2% | 76.5% | 0.127 | 100.0% (9.2%) | 92.9% (63.7%) | 46.1% | 99.1% | 100.0% (83) | 40 / 0 |
| telecom | baseline (names only) | 72.5% | 76.2% | 0.085 | 100.0% (24.8%) | 88.4% (41.0%) | 46.8% | 86.2% | 70.7% (92) | 1 / 2 |
| telecom | + tool descriptions | 71.2% | 80.0% | 0.088 | 100.0% (21.0%) | 88.3% (38.5%) | 51.8% | 81.6% | 76.6% (94) | 0 / 2 |
| telecom | + descriptions, two-stage | 70.5% | 67.6% | 0.070 | 100.0% (7.2%) | 88.7% (35.2%) | 17.3% | 98.9% | 88.9% (27) | 1 / 2 |

Reading:

* **Tool descriptions help where tools are many and similar** (retail +5 points overall, tool-step agreement
  64 → 75 %) and are neutral elsewhere. They cost nothing extra, so they are now the default input
  (`examples/tau2_tool_descriptions/`, extracted from the τ²-bench tool docstrings).
* **The two-stage question does not fix the message-vs-tool bias; it makes it worse.** The Noul gate
  "should the next step be a tool call?" says *no* even more often (tool-step agreement drops to 17–46 %),
  while the second-stage Choice, once reached, picks the right tool 95–100 % of the time. The product
  `p(tool) · p(which tool)` also lowers tool confidences structurally, so high-confidence coverage shrinks to
  7–20 %. Two calls per step, half the coverage: not worth it as formulated. The gate's criteria wording may
  be part of the cause (it enumerates many reasons to send a message); a neutral wording is worth one more
  try, but the single-question form with descriptions is the one to build on.
* **The remaining disagreements are of one kind**: the LLM calls a tool, Jev wants to talk to the user
  first. In these domains that is often *also* policy-compliant (confirm before a write, ask for a missing
  id), just slower and more expensive; sometimes it is a needless question. Only counterfactual replay can
  tell these apart, which is why replay is the next stage rather than more prompt variants.
