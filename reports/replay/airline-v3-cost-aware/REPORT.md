# τ²-bench airline replay v3: cost-aware tier table (min tool coverage 0.16)

50 paired episodes (same tasks, same seed, same user simulator). Costs are OpenRouter prices for the agent LLM plus Jev decision calls; the user simulator is not counted.

| agent | success | mean reward | agent cost / task | of which decision model | assistant steps | steps with LLM call | LLM-step share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| original (LLM every step) | 42.0% | 0.420 | $0.0146 | $0.00000 | 349 | 349 | 100.0% |
| tiered (code / Jev / LLM) | 40.0% | 0.400 | $0.0144 | $0.00020 | 370 | 346 | 93.5% |

Cost change: **-0.9%** (saving); success change: **-2.0 points**.

## Paired outcome

| both succeed | only original | only tiered | neither |
| ---: | ---: | ---: | ---: |
| 18 | 3 | 2 | 27 |

## Tiered agent: where each step was decided

| tier that produced the step | steps |
| --- | ---: |
| jev | 31 |
| llm | 339 |

| fallback reason (step still went to the LLM) | steps |
| --- | ---: |
| jev: below threshold | 31 |
| jev: open argument | 9 |
| message text needs LLM | 7 |

In-loop shadow check on fallback steps (cheap tier proposed an action, LLM then decided): same action 25 / 47 (53.2%).

| disagreement (proposed -> LLM did) | steps |
| --- | ---: |
| tool:get_reservation_details -> message | 4 |
| tool:get_reservation_details -> tool:get_user_details | 2 |
| tool:get_user_details -> message | 2 |
| message -> tool:search_direct_flight | 2 |
| message -> tool:get_reservation_details | 2 |
| message -> tool:cancel_reservation | 2 |
| tool:get_reservation_details -> tool:update_reservation_flights | 1 |
| tool:search_onestop_flight -> message | 1 |
| tool:search_onestop_flight -> tool:update_reservation_flights | 1 |
| tool:get_reservation_details -> tool:update_reservation_baggages | 1 |
| message -> tool:get_user_details | 1 |
| tool:search_onestop_flight -> tool:calculate | 1 |
| message -> tool:update_reservation_flights | 1 |
| tool:get_reservation_details -> tool:search_direct_flight | 1 |

## Per situation

| leaf | tier | τ | rule | steps | skipped LLM | below threshold |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| 26 | llm | 1.00 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=0 & called:update_reservation_flights=0 & called:get_flight_status=0` | 62 | 0 | 0 |
| 4 | llm | 1.00 | `n_tool_calls=0 & have:user_id=0 & prev_role=user` | 37 | 0 | 0 |
| 19 | llm | 1.00 | `n_tool_calls=2 & user_confirms=0 & prev_role=tool` | 37 | 0 | 0 |
| 31 | llm | 1.00 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=1 & called:calculate=0 & called:cancel_reservation=0` | 33 | 0 | 0 |
| 9 | jev | 0.95 | `n_tool_calls=0 & have:user_id=1 & have:reservation_id=0 & user_short=0` | 30 | 12 | 18 |
| 13 | llm | 1.00 | `n_tool_calls=1 & called:get_user_details=0 & prev_role=user` | 27 | 0 | 0 |
| 12 | llm | 1.00 | `n_tool_calls=1 & called:get_user_details=0 & prev_role=tool` | 26 | 0 | 0 |
| 35 | llm | 1.00 | `n_tool_calls=3+ & user_confirms=1 & called:calculate=0` | 24 | 0 | 0 |
| 15 | llm | 1.00 | `n_tool_calls=1 & called:get_user_details=1 & prev_role=tool` | 22 | 0 | 0 |
| 6 | llm | 1.00 | `n_tool_calls=0 & have:user_id=1 & have:reservation_id=1` | 17 | 0 | 0 |
| 16 | jev | 0.50 | `n_tool_calls=1 & called:get_user_details=1 & prev_role=user` | 16 | 7 | 0 |
| 20 | jev | 0.70 | `n_tool_calls=2 & user_confirms=0 & prev_role=user` | 16 | 4 | 9 |
| 28 | llm | 1.00 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=0 & called:update_reservation_flights=1` | 11 | 0 | 0 |
| 21 | jev | 0.80 | `n_tool_calls=2 & user_confirms=1` | 9 | 1 | 4 |
| 32 | llm | 1.00 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=1 & called:calculate=0 & called:cancel_reservation=1` | 3 | 0 | 0 |

## Per task

| task | trial | original reward | tiered reward | original cost | tiered cost (incl. Jev) | tiered LLM steps / steps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0 | 1.0 | 1.0 | $0.0053 | $0.0054 | 3 / 3 |
| 1 | 0 | 1.0 | 0.0 | $0.0092 | $0.0183 | 8 / 8 |
| 10 | 0 | 1.0 | 1.0 | $0.0219 | $0.0201 | 10 / 10 |
| 11 | 0 | 0.0 | 0.0 | $0.0073 | $0.0018 | 1 / 1 |
| 12 | 0 | 0.0 | 0.0 | $0.0055 | $0.0096 | 5 / 5 |
| 13 | 0 | 1.0 | 1.0 | $0.0055 | $0.0055 | 3 / 3 |
| 14 | 0 | 0.0 | 0.0 | $0.0417 | $0.0373 | 16 / 16 |
| 15 | 0 | 0.0 | 0.0 | $0.0320 | $0.0242 | 12 / 13 |
| 16 | 0 | 0.0 | 0.0 | $0.0185 | $0.0123 | 6 / 8 |
| 17 | 0 | 0.0 | 0.0 | $0.0208 | $0.0232 | 11 / 11 |
| 18 | 0 | 0.0 | 0.0 | $0.0268 | $0.0303 | 13 / 13 |
| 19 | 0 | 0.0 | 0.0 | $0.0161 | $0.0081 | 4 / 6 |
| 2 | 0 | 1.0 | 1.0 | $0.0139 | $0.0147 | 7 / 8 |
| 20 | 0 | 0.0 | 0.0 | $0.0103 | $0.0172 | 6 / 6 |
| 21 | 0 | 0.0 | 0.0 | $0.0378 | $0.0347 | 14 / 15 |
| 22 | 0 | 0.0 | 0.0 | $0.0239 | $0.0157 | 8 / 11 |
| 23 | 0 | 0.0 | 0.0 | $0.0359 | $0.0174 | 7 / 8 |
| 24 | 0 | 0.0 | 0.0 | $0.0053 | $0.0148 | 7 / 8 |
| 25 | 0 | 0.0 | 0.0 | $0.0140 | $0.0106 | 6 / 6 |
| 26 | 0 | 1.0 | 1.0 | $0.0090 | $0.0105 | 6 / 6 |
| 27 | 0 | 0.0 | 1.0 | $0.0130 | $0.0073 | 4 / 4 |
| 28 | 0 | 1.0 | 1.0 | $0.0076 | $0.0061 | 4 / 4 |
| 29 | 0 | 0.0 | 0.0 | $0.0122 | $0.0128 | 6 / 6 |
| 3 | 0 | 1.0 | 0.0 | $0.0074 | $0.0054 | 3 / 3 |
| 30 | 0 | 1.0 | 1.0 | $0.0138 | $0.0100 | 6 / 6 |
| 31 | 0 | 1.0 | 1.0 | $0.0153 | $0.0079 | 4 / 4 |
| 32 | 0 | 0.0 | 0.0 | $0.0208 | $0.0280 | 12 / 13 |
| 33 | 0 | 0.0 | 0.0 | $0.0148 | $0.0289 | 15 / 16 |
| 34 | 0 | 0.0 | 1.0 | $0.0124 | $0.0101 | 5 / 5 |
| 35 | 0 | 0.0 | 0.0 | $0.0208 | $0.0164 | 9 / 11 |
| 36 | 0 | 1.0 | 1.0 | $0.0056 | $0.0073 | 4 / 4 |
| 37 | 0 | 0.0 | 0.0 | $0.0055 | $0.0127 | 6 / 6 |
| 38 | 0 | 1.0 | 1.0 | $0.0155 | $0.0112 | 6 / 7 |
| 39 | 0 | 0.0 | 0.0 | $0.0234 | $0.0513 | 22 / 22 |
| 4 | 0 | 1.0 | 1.0 | $0.0135 | $0.0102 | 5 / 7 |
| 40 | 0 | 1.0 | 1.0 | $0.0074 | $0.0079 | 5 / 5 |
| 41 | 0 | 0.0 | 0.0 | $0.0119 | $0.0124 | 5 / 5 |
| 42 | 0 | 0.0 | 0.0 | $0.0124 | $0.0173 | 9 / 10 |
| 43 | 0 | 1.0 | 1.0 | $0.0092 | $0.0197 | 9 / 12 |
| 44 | 0 | 0.0 | 0.0 | $0.0144 | $0.0208 | 9 / 10 |
| 45 | 0 | 1.0 | 1.0 | $0.0094 | $0.0080 | 5 / 5 |
| 46 | 0 | 1.0 | 1.0 | $0.0017 | $0.0018 | 1 / 1 |
| 47 | 0 | 1.0 | 1.0 | $0.0091 | $0.0072 | 4 / 4 |
| 48 | 0 | 0.0 | 0.0 | $0.0073 | $0.0053 | 3 / 3 |
| 49 | 0 | 1.0 | 0.0 | $0.0094 | $0.0074 | 4 / 4 |
| 5 | 0 | 1.0 | 1.0 | $0.0092 | $0.0073 | 4 / 4 |
| 6 | 0 | 1.0 | 1.0 | $0.0074 | $0.0074 | 4 / 4 |
| 7 | 0 | 0.0 | 0.0 | $0.0196 | $0.0204 | 9 / 9 |
| 8 | 0 | 0.0 | 0.0 | $0.0280 | $0.0101 | 5 / 5 |
| 9 | 0 | 0.0 | 0.0 | $0.0102 | $0.0119 | 6 / 6 |
