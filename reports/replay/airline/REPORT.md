# τ²-bench airline replay v2: original vs tiered agent (DeepSeek V3 via OpenRouter, 50 tasks, 1 trial)

50 paired episodes (same tasks, same seed, same user simulator). Costs are OpenRouter prices for the agent LLM plus Jev decision calls; the user simulator is not counted.

| agent | success | mean reward | agent cost / task | of which decision model | assistant steps | steps with LLM call | LLM-step share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| original (LLM every step) | 42.0% | 0.420 | $0.0146 | $0.00000 | 349 | 349 | 100.0% |
| tiered (code / Jev / LLM) | 44.0% | 0.440 | $0.0168 | $0.00113 | 402 | 357 | 88.8% |

Cost change: **15.1%** (increase); success change: **+2.0 points**.

## Paired outcome

| both succeed | only original | only tiered | neither |
| ---: | ---: | ---: | ---: |
| 19 | 2 | 3 | 26 |

## Tiered agent: where each step was decided

| tier that produced the step | steps |
| --- | ---: |
| jev | 131 |
| llm | 271 |

| fallback reason (step still went to the LLM) | steps |
| --- | ---: |
| jev: below threshold | 154 |
| message text needs LLM | 86 |
| jev: duplicate call | 22 |
| jev: open argument | 17 |

In-loop shadow check on fallback steps (cheap tier proposed an action, LLM then decided): same action 204 / 279 (73.1%).

| disagreement (proposed -> LLM did) | steps |
| --- | ---: |
| tool:get_reservation_details -> message | 20 |
| message -> tool:search_direct_flight | 10 |
| tool:transfer_to_human_agents -> message | 7 |
| message -> tool:get_reservation_details | 7 |
| tool:get_user_details -> message | 3 |
| message -> tool:cancel_reservation | 3 |
| message -> tool:get_user_details | 3 |
| tool:search_direct_flight -> message | 3 |
| tool:get_reservation_details -> tool:get_user_details | 3 |
| message -> tool:transfer_to_human_agents | 2 |
| tool:get_reservation_details -> tool:search_direct_flight | 2 |
| message -> tool:list_all_airports | 1 |
| tool:cancel_reservation -> message | 1 |
| message -> tool:update_reservation_flights | 1 |
| message -> tool:calculate | 1 |
| tool:search_onestop_flight -> tool:search_direct_flight | 1 |
| tool:update_reservation_passengers -> message | 1 |
| tool:get_user_details -> tool:book_reservation | 1 |
| tool:transfer_to_human_agents -> tool:search_direct_flight | 1 |
| message -> tool:get_flight_status | 1 |
| tool:update_reservation_flights -> tool:update_reservation_baggages | 1 |
| tool:update_reservation_flights -> message | 1 |
| tool:get_reservation_details -> tool:cancel_reservation | 1 |

## Per situation

| leaf | tier | τ | rule | steps | skipped LLM | below threshold |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| 26 | jev | 0.95 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=0 & called:update_reservation_flights=0 & called:get_flight_status=0` | 69 | 5 | 48 |
| 19 | jev | 0.70 | `n_tool_calls=2 & user_confirms=0 & prev_role=tool` | 40 | 2 | 11 |
| 4 | jev | 0.50 | `n_tool_calls=0 & have:user_id=0 & prev_role=user` | 36 | 0 | 0 |
| 13 | jev | 0.70 | `n_tool_calls=1 & called:get_user_details=0 & prev_role=user` | 35 | 5 | 21 |
| 35 | llm | 1.00 | `n_tool_calls=3+ & user_confirms=1 & called:calculate=0` | 33 | 0 | 0 |
| 12 | jev | 0.90 | `n_tool_calls=1 & called:get_user_details=0 & prev_role=tool` | 27 | 0 | 19 |
| 9 | jev | 0.95 | `n_tool_calls=0 & have:user_id=1 & have:reservation_id=0 & user_short=0` | 26 | 13 | 13 |
| 31 | jev | 0.80 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=1 & called:calculate=0 & called:cancel_reservation=0` | 24 | 4 | 14 |
| 15 | llm | 1.00 | `n_tool_calls=1 & called:get_user_details=1 & prev_role=tool` | 22 | 0 | 0 |
| 6 | llm | 1.00 | `n_tool_calls=0 & have:user_id=1 & have:reservation_id=1` | 19 | 0 | 0 |
| 16 | jev | 0.50 | `n_tool_calls=1 & called:get_user_details=1 & prev_role=user` | 18 | 5 | 0 |
| 20 | jev | 0.70 | `n_tool_calls=2 & user_confirms=0 & prev_role=user` | 14 | 4 | 6 |
| 28 | jev | 0.90 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=0 & called:update_reservation_flights=1` | 10 | 2 | 5 |
| 33 | jev | 0.90 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=1 & called:calculate=1` | 8 | 0 | 8 |
| 21 | jev | 0.80 | `n_tool_calls=2 & user_confirms=1` | 7 | 4 | 2 |
| 32 | jev | 0.60 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=1 & called:calculate=0 & called:cancel_reservation=1` | 7 | 1 | 4 |
| 27 | llm | 1.00 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=0 & called:update_reservation_flights=0 & called:get_flight_status=1` | 4 | 0 | 0 |
| 36 | jev | 0.90 | `n_tool_calls=3+ & user_confirms=1 & called:calculate=1` | 3 | 0 | 3 |

## Per task

| task | trial | original reward | tiered reward | original cost | tiered cost (incl. Jev) | tiered LLM steps / steps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0 | 1.0 | 1.0 | $0.0053 | $0.0077 | 4 / 4 |
| 1 | 0 | 1.0 | 1.0 | $0.0092 | $0.0243 | 10 / 13 |
| 10 | 0 | 1.0 | 1.0 | $0.0219 | $0.0252 | 11 / 13 |
| 11 | 0 | 0.0 | 1.0 | $0.0073 | $0.0102 | 5 / 5 |
| 12 | 0 | 0.0 | 0.0 | $0.0055 | $0.0058 | 3 / 3 |
| 13 | 0 | 1.0 | 1.0 | $0.0055 | $0.0058 | 3 / 3 |
| 14 | 0 | 0.0 | 0.0 | $0.0417 | $0.0319 | 14 / 14 |
| 15 | 0 | 0.0 | 0.0 | $0.0320 | $0.0166 | 7 / 9 |
| 16 | 0 | 0.0 | 0.0 | $0.0185 | $0.0298 | 13 / 15 |
| 17 | 0 | 0.0 | 0.0 | $0.0208 | $0.0359 | 15 / 21 |
| 18 | 0 | 0.0 | 0.0 | $0.0268 | $0.0537 | 20 / 24 |
| 19 | 0 | 0.0 | 0.0 | $0.0161 | $0.0082 | 4 / 5 |
| 2 | 0 | 1.0 | 1.0 | $0.0139 | $0.0132 | 6 / 7 |
| 20 | 0 | 0.0 | 0.0 | $0.0103 | $0.0273 | 8 / 8 |
| 21 | 0 | 0.0 | 0.0 | $0.0378 | $0.0477 | 16 / 19 |
| 22 | 0 | 0.0 | 0.0 | $0.0239 | $0.0086 | 4 / 7 |
| 23 | 0 | 0.0 | 0.0 | $0.0359 | $0.0256 | 8 / 8 |
| 24 | 0 | 0.0 | 0.0 | $0.0053 | $0.0256 | 11 / 12 |
| 25 | 0 | 0.0 | 0.0 | $0.0140 | $0.0085 | 4 / 5 |
| 26 | 0 | 1.0 | 1.0 | $0.0090 | $0.0083 | 4 / 5 |
| 27 | 0 | 0.0 | 1.0 | $0.0130 | $0.0095 | 5 / 5 |
| 28 | 0 | 1.0 | 1.0 | $0.0076 | $0.0099 | 5 / 5 |
| 29 | 0 | 0.0 | 0.0 | $0.0122 | $0.0155 | 7 / 8 |
| 3 | 0 | 1.0 | 0.0 | $0.0074 | $0.0057 | 3 / 3 |
| 30 | 0 | 1.0 | 0.0 | $0.0138 | $0.0111 | 5 / 5 |
| 31 | 0 | 1.0 | 1.0 | $0.0153 | $0.0083 | 4 / 5 |
| 32 | 0 | 0.0 | 0.0 | $0.0208 | $0.0206 | 9 / 10 |
| 33 | 0 | 0.0 | 0.0 | $0.0148 | $0.0248 | 10 / 10 |
| 34 | 0 | 0.0 | 1.0 | $0.0124 | $0.0065 | 3 / 4 |
| 35 | 0 | 0.0 | 0.0 | $0.0208 | $0.0259 | 11 / 14 |
| 36 | 0 | 1.0 | 1.0 | $0.0056 | $0.0081 | 4 / 4 |
| 37 | 0 | 0.0 | 0.0 | $0.0055 | $0.0251 | 10 / 10 |
| 38 | 0 | 1.0 | 1.0 | $0.0155 | $0.0196 | 9 / 10 |
| 39 | 0 | 0.0 | 0.0 | $0.0234 | $0.0129 | 6 / 6 |
| 4 | 0 | 1.0 | 1.0 | $0.0135 | $0.0211 | 9 / 10 |
| 40 | 0 | 1.0 | 1.0 | $0.0074 | $0.0097 | 5 / 5 |
| 41 | 0 | 0.0 | 0.0 | $0.0119 | $0.0127 | 5 / 5 |
| 42 | 0 | 0.0 | 0.0 | $0.0124 | $0.0251 | 10 / 11 |
| 43 | 0 | 1.0 | 1.0 | $0.0092 | $0.0394 | 16 / 17 |
| 44 | 0 | 0.0 | 0.0 | $0.0144 | $0.0141 | 5 / 6 |
| 45 | 0 | 1.0 | 1.0 | $0.0094 | $0.0099 | 5 / 5 |
| 46 | 0 | 1.0 | 1.0 | $0.0017 | $0.0019 | 1 / 1 |
| 47 | 0 | 1.0 | 1.0 | $0.0091 | $0.0120 | 6 / 6 |
| 48 | 0 | 0.0 | 0.0 | $0.0073 | $0.0056 | 3 / 3 |
| 49 | 0 | 1.0 | 1.0 | $0.0094 | $0.0098 | 5 / 5 |
| 5 | 0 | 1.0 | 1.0 | $0.0092 | $0.0096 | 5 / 5 |
| 6 | 0 | 1.0 | 1.0 | $0.0074 | $0.0096 | 5 / 5 |
| 7 | 0 | 0.0 | 0.0 | $0.0196 | $0.0133 | 6 / 8 |
| 8 | 0 | 0.0 | 0.0 | $0.0280 | $0.0106 | 5 / 6 |
| 9 | 0 | 0.0 | 0.0 | $0.0102 | $0.0110 | 5 / 5 |
