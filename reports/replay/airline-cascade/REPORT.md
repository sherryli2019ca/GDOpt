# τ²-bench airline: cascade (DeepSeek strong, qwen3.7-flash writes confident message steps, Jev routes)

50 paired episodes (same tasks, same seed, same user simulator). Costs are OpenRouter prices for the agent LLM plus Jev decision calls; the user simulator is not counted.

| agent | success | mean reward | agent cost / task | of which decision model | assistant steps | steps with LLM call | LLM-step share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| original (LLM every step) | 42.0% | 0.420 | $0.0146 | $0.00000 | 349 | 349 | 100.0% |
| tiered (code / Jev / LLM) | 44.0% | 0.440 | $0.0133 | $0.00116 | 398 | 351 | 88.2% |

Cost change: **-8.4%** (saving); success change: **+2.0 points**.

## Paired outcome

| both succeed | only original | only tiered | neither |
| ---: | ---: | ---: | ---: |
| 18 | 3 | 4 | 25 |

## Tiered agent: where each step was decided

| tier that produced the step | steps |
| --- | ---: |
| jev | 132 |
| llm | 266 |

| fallback reason (step still went to the LLM) | steps |
| --- | ---: |
| jev: below threshold | 147 |
| message text by message_llm | 85 |
| jev: open argument | 23 |
| jev: duplicate call | 17 |

In-loop shadow check on fallback steps (cheap tier proposed an action, LLM then decided): same action 177 / 272 (65.1%).

| disagreement (proposed -> LLM did) | steps |
| --- | ---: |
| tool:get_reservation_details -> message | 17 |
| message -> tool:get_reservation_details | 11 |
| tool:get_user_details -> message | 9 |
| message -> tool:search_direct_flight | 8 |
| message -> tool:get_user_details | 6 |
| message -> tool:cancel_reservation | 6 |
| tool:search_direct_flight -> message | 5 |
| tool:transfer_to_human_agents -> message | 5 |
| message -> tool:get_flight_status | 5 |
| tool:get_reservation_details -> tool:get_user_details | 3 |
| message -> tool:update_reservation_flights | 3 |
| tool:get_user_details -> tool:update_reservation_flights | 2 |
| tool:search_onestop_flight -> message | 2 |
| tool:search_onestop_flight -> tool:search_direct_flight | 2 |
| tool:get_reservation_details -> tool:update_reservation_baggages | 2 |
| tool:update_reservation_baggages -> message | 1 |
| tool:transfer_to_human_agents -> tool:update_reservation_flights | 1 |
| tool:transfer_to_human_agents -> tool:search_direct_flight | 1 |
| tool:search_direct_flight -> tool:search_onestop_flight | 1 |
| message -> tool:book_reservation | 1 |
| tool:get_reservation_details -> tool:update_reservation_passengers | 1 |
| message -> tool:calculate | 1 |
| message -> tool:update_reservation_passengers | 1 |
| tool:get_reservation_details -> tool:cancel_reservation | 1 |

## Per situation

| leaf | tier | τ | rule | steps | skipped LLM | below threshold |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| 26 | jev | 0.95 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=0 & called:update_reservation_flights=0 & called:get_flight_status=0` | 49 | 1 | 41 |
| 31 | jev | 0.80 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=1 & called:calculate=0 & called:cancel_reservation=0` | 46 | 7 | 20 |
| 19 | jev | 0.70 | `n_tool_calls=2 & user_confirms=0 & prev_role=tool` | 44 | 1 | 14 |
| 4 | jev | 0.50 | `n_tool_calls=0 & have:user_id=0 & prev_role=user` | 33 | 0 | 0 |
| 9 | jev | 0.95 | `n_tool_calls=0 & have:user_id=1 & have:reservation_id=0 & user_short=0` | 30 | 13 | 17 |
| 35 | llm | 1.00 | `n_tool_calls=3+ & user_confirms=1 & called:calculate=0` | 26 | 0 | 0 |
| 15 | llm | 1.00 | `n_tool_calls=1 & called:get_user_details=1 & prev_role=tool` | 25 | 0 | 0 |
| 12 | jev | 0.90 | `n_tool_calls=1 & called:get_user_details=0 & prev_role=tool` | 24 | 0 | 19 |
| 13 | jev | 0.70 | `n_tool_calls=1 & called:get_user_details=0 & prev_role=user` | 23 | 7 | 10 |
| 16 | jev | 0.50 | `n_tool_calls=1 & called:get_user_details=1 & prev_role=user` | 21 | 7 | 0 |
| 6 | llm | 1.00 | `n_tool_calls=0 & have:user_id=1 & have:reservation_id=1` | 19 | 0 | 0 |
| 28 | jev | 0.90 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=0 & called:update_reservation_flights=1` | 15 | 1 | 13 |
| 21 | jev | 0.80 | `n_tool_calls=2 & user_confirms=1` | 11 | 6 | 3 |
| 20 | jev | 0.70 | `n_tool_calls=2 & user_confirms=0 & prev_role=user` | 11 | 2 | 5 |
| 27 | llm | 1.00 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=0 & called:update_reservation_flights=0 & called:get_flight_status=1` | 9 | 0 | 0 |
| 8 | jev | 0.50 | `n_tool_calls=0 & have:user_id=1 & have:reservation_id=0 & user_short=1` | 4 | 2 | 0 |
| 32 | jev | 0.60 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=1 & called:calculate=0 & called:cancel_reservation=1` | 4 | 0 | 1 |
| 33 | jev | 0.90 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=1 & called:calculate=1` | 3 | 0 | 3 |
| 36 | jev | 0.90 | `n_tool_calls=3+ & user_confirms=1 & called:calculate=1` | 1 | 0 | 1 |

## Per task

| task | trial | original reward | tiered reward | original cost | tiered cost (incl. Jev) | tiered LLM steps / steps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0 | 1.0 | 1.0 | $0.0053 | $0.0039 | 3 / 3 |
| 1 | 0 | 1.0 | 1.0 | $0.0092 | $0.0085 | 6 / 7 |
| 10 | 0 | 1.0 | 1.0 | $0.0219 | $0.0096 | 8 / 10 |
| 11 | 0 | 0.0 | 0.0 | $0.0073 | $0.0103 | 6 / 10 |
| 12 | 0 | 0.0 | 0.0 | $0.0055 | $0.0138 | 7 / 7 |
| 13 | 0 | 1.0 | 1.0 | $0.0055 | $0.0191 | 11 / 11 |
| 14 | 0 | 0.0 | 0.0 | $0.0417 | $0.0208 | 9 / 10 |
| 15 | 0 | 0.0 | 0.0 | $0.0320 | $0.0441 | 18 / 22 |
| 16 | 0 | 0.0 | 0.0 | $0.0185 | $0.0168 | 9 / 12 |
| 17 | 0 | 0.0 | 0.0 | $0.0208 | $0.0246 | 11 / 12 |
| 18 | 0 | 0.0 | 0.0 | $0.0268 | $0.0399 | 17 / 20 |
| 19 | 0 | 0.0 | 0.0 | $0.0161 | $0.0074 | 6 / 7 |
| 2 | 0 | 1.0 | 1.0 | $0.0139 | $0.0192 | 9 / 9 |
| 20 | 0 | 0.0 | 0.0 | $0.0103 | $0.0092 | 8 / 9 |
| 21 | 0 | 0.0 | 0.0 | $0.0378 | $0.0264 | 11 / 13 |
| 22 | 0 | 0.0 | 0.0 | $0.0239 | $0.0146 | 8 / 10 |
| 23 | 0 | 0.0 | 0.0 | $0.0359 | $0.0585 | 8 / 8 |
| 24 | 0 | 0.0 | 0.0 | $0.0053 | $0.0193 | 11 / 11 |
| 25 | 0 | 0.0 | 0.0 | $0.0140 | $0.0041 | 4 / 5 |
| 26 | 0 | 1.0 | 0.0 | $0.0090 | $0.0088 | 5 / 6 |
| 27 | 0 | 0.0 | 0.0 | $0.0130 | $0.0106 | 6 / 7 |
| 28 | 0 | 1.0 | 1.0 | $0.0076 | $0.0052 | 4 / 4 |
| 29 | 0 | 0.0 | 0.0 | $0.0122 | $0.0084 | 4 / 4 |
| 3 | 0 | 1.0 | 1.0 | $0.0074 | $0.0043 | 4 / 5 |
| 30 | 0 | 1.0 | 0.0 | $0.0138 | $0.0095 | 6 / 8 |
| 31 | 0 | 1.0 | 1.0 | $0.0153 | $0.0078 | 5 / 7 |
| 32 | 0 | 0.0 | 1.0 | $0.0208 | $0.0100 | 10 / 12 |
| 33 | 0 | 0.0 | 0.0 | $0.0148 | $0.0160 | 10 / 11 |
| 34 | 0 | 0.0 | 1.0 | $0.0124 | $0.0099 | 6 / 7 |
| 35 | 0 | 0.0 | 0.0 | $0.0208 | $0.0185 | 11 / 12 |
| 36 | 0 | 1.0 | 1.0 | $0.0056 | $0.0051 | 4 / 4 |
| 37 | 0 | 0.0 | 0.0 | $0.0055 | $0.0256 | 5 / 7 |
| 38 | 0 | 1.0 | 1.0 | $0.0155 | $0.0098 | 6 / 7 |
| 39 | 0 | 0.0 | 0.0 | $0.0234 | $0.0096 | 5 / 5 |
| 4 | 0 | 1.0 | 1.0 | $0.0135 | $0.0188 | 9 / 10 |
| 40 | 0 | 1.0 | 1.0 | $0.0074 | $0.0014 | 5 / 5 |
| 41 | 0 | 0.0 | 0.0 | $0.0119 | $0.0098 | 6 / 7 |
| 42 | 0 | 0.0 | 1.0 | $0.0124 | $0.0102 | 6 / 7 |
| 43 | 0 | 1.0 | 1.0 | $0.0092 | $0.0103 | 7 / 7 |
| 44 | 0 | 0.0 | 0.0 | $0.0144 | $0.0098 | 5 / 6 |
| 45 | 0 | 1.0 | 1.0 | $0.0094 | $0.0038 | 4 / 4 |
| 46 | 0 | 1.0 | 1.0 | $0.0017 | $0.0014 | 1 / 1 |
| 47 | 0 | 1.0 | 0.0 | $0.0091 | $0.0039 | 5 / 5 |
| 48 | 0 | 0.0 | 0.0 | $0.0073 | $0.0047 | 4 / 4 |
| 49 | 0 | 1.0 | 1.0 | $0.0094 | $0.0053 | 5 / 5 |
| 5 | 0 | 1.0 | 1.0 | $0.0092 | $0.0061 | 5 / 5 |
| 6 | 0 | 1.0 | 1.0 | $0.0074 | $0.0059 | 4 / 4 |
| 7 | 0 | 0.0 | 0.0 | $0.0196 | $0.0133 | 7 / 9 |
| 8 | 0 | 0.0 | 0.0 | $0.0280 | $0.0242 | 12 / 12 |
| 9 | 0 | 0.0 | 1.0 | $0.0102 | $0.0090 | 5 / 5 |
