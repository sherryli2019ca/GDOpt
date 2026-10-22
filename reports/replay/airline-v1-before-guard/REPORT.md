# τ²-bench airline replay: original vs tiered agent (DeepSeek V3 via OpenRouter, 50 tasks, 1 trial)

50 paired episodes (same tasks, same seed, same user simulator). Costs are OpenRouter prices for the agent LLM plus Jev decision calls; the user simulator is not counted.

| agent | success | mean reward | agent cost / task | of which decision model | assistant steps | steps with LLM call | LLM-step share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| original (LLM every step) | 42.0% | 0.420 | $0.0146 | $0.00000 | 349 | 349 | 100.0% |
| tiered (code / Jev / LLM) | 44.0% | 0.440 | $0.0337 | $0.00344 | 511 | 439 | 85.9% |

Cost change: **131.4%** (increase); success change: **+2.0 points**.

## Paired outcome

| both succeed | only original | only tiered | neither |
| ---: | ---: | ---: | ---: |
| 18 | 3 | 4 | 25 |

## Tiered agent: where each step was decided

| tier that produced the step | steps |
| --- | ---: |
| jev | 163 |
| llm | 348 |

| fallback reason (step still went to the LLM) | steps |
| --- | ---: |
| jev: below threshold | 266 |
| message text needs LLM | 91 |
| jev: open argument | 22 |

In-loop shadow check on fallback steps (cheap tier proposed an action, LLM then decided): same action 249 / 379 (65.7%).

| disagreement (proposed -> LLM did) | steps |
| --- | ---: |
| tool:transfer_to_human_agents -> tool:update_reservation_passengers | 52 |
| tool:get_reservation_details -> message | 20 |
| message -> tool:search_direct_flight | 13 |
| message -> tool:get_reservation_details | 10 |
| tool:search_onestop_flight -> message | 6 |
| message -> tool:update_reservation_flights | 4 |
| message -> tool:cancel_reservation | 4 |
| tool:search_direct_flight -> message | 3 |
| message -> tool:transfer_to_human_agents | 2 |
| message -> tool:calculate | 2 |
| tool:get_user_details -> message | 2 |
| message -> tool:book_reservation | 2 |
| message -> tool:get_user_details | 1 |
| tool:get_reservation_details -> tool:search_direct_flight | 1 |
| tool:get_reservation_details -> tool:update_reservation_baggages | 1 |
| tool:update_reservation_flights -> tool:search_direct_flight | 1 |
| tool:get_user_details -> tool:transfer_to_human_agents | 1 |
| message -> tool:search_onestop_flight | 1 |
| message -> tool:get_flight_status | 1 |
| tool:get_reservation_details -> tool:transfer_to_human_agents | 1 |
| tool:transfer_to_human_agents -> message | 1 |
| tool:get_reservation_details -> tool:cancel_reservation | 1 |

## Per situation

| leaf | tier | τ | rule | steps | skipped LLM | below threshold |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| 26 | jev | 0.95 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=0 & called:update_reservation_flights=0 & called:get_flight_status=0` | 148 | 39 | 108 |
| 28 | jev | 0.90 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=0 & called:update_reservation_flights=1` | 65 | 0 | 61 |
| 19 | jev | 0.70 | `n_tool_calls=2 & user_confirms=0 & prev_role=tool` | 41 | 5 | 17 |
| 31 | jev | 0.80 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=1 & called:calculate=0 & called:cancel_reservation=0` | 35 | 8 | 20 |
| 4 | jev | 0.50 | `n_tool_calls=0 & have:user_id=0 & prev_role=user` | 34 | 0 | 0 |
| 9 | jev | 0.90 | `n_tool_calls=0 & have:user_id=1 & user_short=0 & user_confirms=0` | 25 | 12 | 13 |
| 15 | llm | 1.00 | `n_tool_calls=1 & called:get_user_details=1 & prev_role=tool` | 25 | 0 | 0 |
| 12 | jev | 0.90 | `n_tool_calls=1 & called:get_user_details=0 & prev_role=tool` | 24 | 0 | 18 |
| 16 | jev | 0.50 | `n_tool_calls=1 & called:get_user_details=1 & prev_role=user` | 24 | 1 | 1 |
| 13 | jev | 0.70 | `n_tool_calls=1 & called:get_user_details=0 & prev_role=user` | 23 | 3 | 11 |
| 8 | llm | 1.00 | `n_tool_calls=0 & have:user_id=1 & user_short=0 & user_confirms=1` | 19 | 0 | 0 |
| 21 | jev | 0.80 | `n_tool_calls=2 & user_confirms=1` | 16 | 2 | 11 |
| 20 | jev | 0.70 | `n_tool_calls=2 & user_confirms=0 & prev_role=user` | 13 | 2 | 5 |
| 35 | llm | 1.00 | `n_tool_calls=3+ & user_confirms=1 & called:calculate=0` | 11 | 0 | 0 |
| 27 | llm | 1.00 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=0 & called:update_reservation_flights=0 & called:get_flight_status=1` | 5 | 0 | 0 |
| 32 | jev | 0.60 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=1 & called:calculate=0 & called:cancel_reservation=1` | 2 | 0 | 1 |
| 6 | jev | 0.60 | `n_tool_calls=0 & have:user_id=1 & user_short=1` | 1 | 0 | 0 |

## Per task

| task | trial | original reward | tiered reward | original cost | tiered cost (incl. Jev) | tiered LLM steps / steps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0 | 1.0 | 1.0 | $0.0053 | $0.0082 | 4 / 4 |
| 1 | 0 | 1.0 | 1.0 | $0.0092 | $0.0223 | 9 / 12 |
| 10 | 0 | 1.0 | 0.0 | $0.0219 | $0.0138 | 6 / 7 |
| 11 | 0 | 0.0 | 0.0 | $0.0073 | $0.0060 | 3 / 3 |
| 12 | 0 | 0.0 | 0.0 | $0.0055 | $0.3945 | 61 / 62 |
| 13 | 0 | 1.0 | 1.0 | $0.0055 | $0.0218 | 9 / 9 |
| 14 | 0 | 0.0 | 0.0 | $0.0417 | $0.0160 | 7 / 7 |
| 15 | 0 | 0.0 | 0.0 | $0.0320 | $0.0277 | 12 / 15 |
| 16 | 0 | 0.0 | 1.0 | $0.0185 | $0.0224 | 8 / 10 |
| 17 | 0 | 0.0 | 0.0 | $0.0208 | $0.0176 | 8 / 8 |
| 18 | 0 | 0.0 | 1.0 | $0.0268 | $0.0255 | 8 / 9 |
| 19 | 0 | 0.0 | 0.0 | $0.0161 | $0.0114 | 5 / 6 |
| 2 | 0 | 1.0 | 1.0 | $0.0139 | $0.0254 | 11 / 11 |
| 20 | 0 | 0.0 | 0.0 | $0.0103 | $0.0342 | 10 / 11 |
| 21 | 0 | 0.0 | 0.0 | $0.0378 | $0.0153 | 5 / 7 |
| 22 | 0 | 0.0 | 0.0 | $0.0239 | $0.0100 | 5 / 5 |
| 23 | 0 | 0.0 | 0.0 | $0.0359 | $0.0148 | 6 / 6 |
| 24 | 0 | 0.0 | 0.0 | $0.0053 | $0.0059 | 3 / 3 |
| 25 | 0 | 0.0 | 0.0 | $0.0140 | $0.0136 | 6 / 6 |
| 26 | 0 | 1.0 | 1.0 | $0.0090 | $0.0292 | 8 / 24 |
| 27 | 0 | 0.0 | 1.0 | $0.0130 | $0.0106 | 5 / 6 |
| 28 | 0 | 1.0 | 1.0 | $0.0076 | $0.0082 | 4 / 4 |
| 29 | 0 | 0.0 | 0.0 | $0.0122 | $0.0175 | 7 / 7 |
| 3 | 0 | 1.0 | 1.0 | $0.0074 | $0.0066 | 3 / 4 |
| 30 | 0 | 1.0 | 1.0 | $0.0138 | $0.0169 | 7 / 7 |
| 31 | 0 | 1.0 | 1.0 | $0.0153 | $0.0108 | 4 / 8 |
| 32 | 0 | 0.0 | 0.0 | $0.0208 | $0.0245 | 10 / 11 |
| 33 | 0 | 0.0 | 0.0 | $0.0148 | $0.0139 | 6 / 6 |
| 34 | 0 | 0.0 | 1.0 | $0.0124 | $0.0116 | 5 / 5 |
| 35 | 0 | 0.0 | 0.0 | $0.0208 | $0.5558 | 84 / 97 |
| 36 | 0 | 1.0 | 1.0 | $0.0056 | $0.0061 | 3 / 3 |
| 37 | 0 | 0.0 | 0.0 | $0.0055 | $0.0183 | 8 / 9 |
| 38 | 0 | 1.0 | 1.0 | $0.0155 | $0.0139 | 6 / 6 |
| 39 | 0 | 0.0 | 0.0 | $0.0234 | $0.0093 | 4 / 4 |
| 4 | 0 | 1.0 | 1.0 | $0.0135 | $0.0062 | 3 / 4 |
| 40 | 0 | 1.0 | 1.0 | $0.0074 | $0.0124 | 6 / 6 |
| 41 | 0 | 0.0 | 0.0 | $0.0119 | $0.0135 | 5 / 5 |
| 42 | 0 | 0.0 | 0.0 | $0.0124 | $0.0372 | 11 / 16 |
| 43 | 0 | 1.0 | 1.0 | $0.0092 | $0.0379 | 11 / 21 |
| 44 | 0 | 0.0 | 0.0 | $0.0144 | $0.0128 | 5 / 5 |
| 45 | 0 | 1.0 | 1.0 | $0.0094 | $0.0129 | 6 / 6 |
| 46 | 0 | 1.0 | 1.0 | $0.0017 | $0.0020 | 1 / 1 |
| 47 | 0 | 1.0 | 0.0 | $0.0091 | $0.0106 | 5 / 5 |
| 48 | 0 | 0.0 | 0.0 | $0.0073 | $0.0101 | 5 / 5 |
| 49 | 0 | 1.0 | 0.0 | $0.0094 | $0.0083 | 4 / 4 |
| 5 | 0 | 1.0 | 1.0 | $0.0092 | $0.0079 | 4 / 4 |
| 6 | 0 | 1.0 | 1.0 | $0.0074 | $0.0105 | 5 / 5 |
| 7 | 0 | 0.0 | 0.0 | $0.0196 | $0.0188 | 7 / 9 |
| 8 | 0 | 0.0 | 0.0 | $0.0280 | $0.0168 | 7 / 9 |
| 9 | 0 | 0.0 | 0.0 | $0.0102 | $0.0084 | 4 / 4 |
