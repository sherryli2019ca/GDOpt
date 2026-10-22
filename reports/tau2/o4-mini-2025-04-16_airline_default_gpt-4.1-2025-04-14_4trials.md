# GDOpt profile: o4-mini-2025-04-16_airline_default_gpt-4.1-2025-04-14_4trials (agent o4-mini-2025-04-16, user gpt-4.1-2025-04-14)

- trajectories: 100 train / 100 test; test steps: 1062; action options: 14
- agent cost on test trajectories: $4.65 (LLM ≈ $1.03/M prompt tokens; Jev/LLM price ratio 0.041)
- steps that are tool calls with all arguments already in context: 20.9%
- upper bound on cost saved if every such step skipped the LLM: 21.1%

## Actions on test steps

| action | steps | share |
| --- | ---: | ---: |
| message | 574 | 54.0% |
| tool:get_reservation_details | 183 | 17.2% |
| tool:search_direct_flight | 79 | 7.4% |
| tool:get_user_details | 63 | 5.9% |
| tool:transfer_to_human_agents | 54 | 5.1% |
| tool:update_reservation_flights | 28 | 2.6% |
| tool:search_onestop_flight | 21 | 2.0% |
| tool:cancel_reservation | 19 | 1.8% |
| tool:book_reservation | 17 | 1.6% |
| tool:update_reservation_baggages | 11 | 1.0% |
| tool:get_flight_status | 5 | 0.5% |
| tool:update_reservation_passengers | 5 | 0.5% |
| tool:send_certificate | 3 | 0.3% |

## Candidate tiers (stage 2, before any decision-model call)

| tier | situations | test steps | share of steps |
| --- | ---: | ---: | ---: |
| code | 0 | 0 | 0.0% |
| jev | 17 | 1062 | 100.0% |
| llm | 0 | 0 | 0.0% |

## Situations (sorted by potential saving)

| # | rule | n test | majority action | maj. acc | norm. entropy | closed tool | latest-rule acc | cost share | max saving | candidate |
| ---: | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 27 | `n_tool_calls=3+ & called:search_direct_flight=1 & user_confirms=0 & called:update_reservation_flights=0 & prev_role=tool & called:search_onestop_flight=0` | 74 | tool:search_direct_flight | 0.28 | 0.48 | 45.9% | 35.3% | 10.8% | 5.1% | jev |
| 5 | `n_tool_calls=0 & have:user_id=1 & have:reservation_id=0` | 55 | tool:get_user_details | 0.91 | 0.14 | 90.9% | 100.0% | 2.8% | 2.3% | jev |
| 4 | `n_tool_calls=0 & have:user_id=1 & have:reservation_id=1` | 49 | tool:get_reservation_details | 0.73 | 0.32 | 77.6% | 86.8% | 3.3% | 2.1% | jev |
| 20 | `n_tool_calls=3+ & called:search_direct_flight=0 & prev_role=tool` | 159 | tool:get_reservation_details | 0.39 | 0.53 | 9.4% | 13.3% | 18.0% | 2.0% | jev |
| 28 | `n_tool_calls=3+ & called:search_direct_flight=1 & user_confirms=0 & called:update_reservation_flights=0 & prev_role=tool & called:search_onestop_flight=1` | 37 | message | 0.54 | 0.45 | 35.1% | 38.5% | 6.3% | 1.8% | jev |
| 16 | `n_tool_calls=2 & called:transfer_to_human_agents=0 & prev_role=tool` | 78 | message | 0.44 | 0.52 | 17.9% | 7.1% | 8.1% | 1.4% | jev |
| 17 | `n_tool_calls=2 & called:transfer_to_human_agents=0 & prev_role=user` | 49 | message | 0.39 | 0.75 | 26.5% | 53.8% | 5.0% | 1.4% | jev |
| 21 | `n_tool_calls=3+ & called:search_direct_flight=0 & prev_role=user` | 61 | message | 0.51 | 0.59 | 14.8% | 33.3% | 7.7% | 1.1% | jev |
| 8 | `n_tool_calls=1 & called:get_user_details=0 & prev_role=tool` | 49 | message | 0.57 | 0.51 | 26.5% | 53.8% | 3.9% | 1.1% | jev |
| 9 | `n_tool_calls=1 & called:get_user_details=0 & prev_role=user` | 42 | message | 0.57 | 0.47 | 16.7% | 42.9% | 3.7% | 0.8% | jev |
| 30 | `n_tool_calls=3+ & called:search_direct_flight=1 & user_confirms=1` | 38 | tool:update_reservation_flights | 0.39 | 0.57 | 13.2% | 60.0% | 6.6% | 0.7% | jev |
| 24 | `n_tool_calls=3+ & called:search_direct_flight=1 & user_confirms=0 & called:update_reservation_flights=1` | 35 | message | 0.71 | 0.33 | 14.3% | 0.0% | 5.2% | 0.6% | jev |
| 29 | `n_tool_calls=3+ & called:search_direct_flight=1 & user_confirms=0 & called:update_reservation_flights=0 & prev_role=user` | 27 | message | 0.70 | 0.35 | 11.1% | 33.3% | 4.3% | 0.3% | jev |
| 12 | `n_tool_calls=1 & called:get_user_details=1 & prev_role=user` | 26 | tool:get_reservation_details | 0.69 | 0.28 | 7.7% | 50.0% | 2.5% | 0.2% | jev |
| 2 | `n_tool_calls=0 & have:user_id=0` | 209 | message | 0.96 | 0.07 | 0.5% | 100.0% | 6.0% | 0.1% | jev |
| 11 | `n_tool_calls=1 & called:get_user_details=1 & prev_role=tool` | 51 | tool:get_reservation_details | 0.63 | 0.25 | 0.0% | 0.0% | 4.2% | 0.0% | jev |
| 14 | `n_tool_calls=2 & called:transfer_to_human_agents=1` | 23 | message | 0.91 | 0.11 | 0.0% | 0.0% | 1.4% | 0.0% | jev |
