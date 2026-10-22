# GDOpt profile: claude-3-7-sonnet-20250219_airline_default_gpt-4.1-2025-04-14_4trials (agent claude-3-7-sonnet-20250219, user gpt-4.1-2025-04-14)

- trajectories: 100 train / 100 test; test steps: 1417; action options: 15
- agent cost on test trajectories: $33.79 (LLM ≈ $3.26/M prompt tokens; Jev/LLM price ratio 0.013)
- steps that are tool calls with all arguments already in context: 26.0%
- upper bound on cost saved if every such step skipped the LLM: 27.9%

## Actions on test steps

| action | steps | share |
| --- | ---: | ---: |
| message | 611 | 43.1% |
| tool:get_reservation_details | 288 | 20.3% |
| tool:search_direct_flight | 137 | 9.7% |
| tool:get_user_details | 106 | 7.5% |
| tool:update_reservation_flights | 66 | 4.7% |
| tool:get_flight_status | 55 | 3.9% |
| tool:cancel_reservation | 45 | 3.2% |
| tool:search_onestop_flight | 27 | 1.9% |
| tool:calculate | 24 | 1.7% |
| tool:transfer_to_human_agents | 22 | 1.6% |
| tool:update_reservation_baggages | 11 | 0.8% |
| tool:book_reservation | 11 | 0.8% |
| tool:send_certificate | 7 | 0.5% |
| tool:update_reservation_passengers | 4 | 0.3% |
| tool:list_all_airports | 3 | 0.2% |

## Candidate tiers (stage 2, before any decision-model call)

| tier | situations | test steps | share of steps |
| --- | ---: | ---: | ---: |
| code | 0 | 0 | 0.0% |
| jev | 22 | 1417 | 100.0% |
| llm | 0 | 0 | 0.0% |

## Situations (sorted by potential saving)

| # | rule | n test | majority action | maj. acc | norm. entropy | closed tool | latest-rule acc | cost share | max saving | candidate |
| ---: | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 30 | `n_tool_calls=3+ & called:search_direct_flight=1 & called:calculate=0 & called:update_reservation_flights=0 & prev_role=tool & called:search_onestop_flight=0` | 124 | tool:search_direct_flight | 0.44 | 0.53 | 54.0% | 22.4% | 10.7% | 5.6% | jev |
| 35 | `n_tool_calls=3+ & called:search_direct_flight=1 & called:calculate=0 & called:update_reservation_flights=1` | 120 | message | 0.37 | 0.68 | 34.2% | 22.0% | 13.7% | 4.5% | jev |
| 6 | `n_tool_calls=0 & have:user_id=1 & user_short=0` | 63 | tool:get_user_details | 0.76 | 0.20 | 76.2% | 100.0% | 3.3% | 2.5% | jev |
| 21 | `n_tool_calls=3+ & called:search_direct_flight=0 & prev_role=tool & called:cancel_reservation=0 & called:get_flight_status=1` | 92 | tool:get_flight_status | 0.30 | 0.47 | 34.8% | 3.1% | 6.8% | 2.2% | jev |
| 24 | `n_tool_calls=3+ & called:search_direct_flight=0 & prev_role=user & user_confirms=1` | 42 | message | 0.31 | 0.69 | 50.0% | 38.1% | 3.3% | 1.6% | jev |
| 25 | `n_tool_calls=3+ & called:search_direct_flight=0 & prev_role=user & user_confirms=0` | 61 | message | 0.48 | 0.61 | 29.5% | 16.7% | 4.9% | 1.4% | jev |
| 20 | `n_tool_calls=3+ & called:search_direct_flight=0 & prev_role=tool & called:cancel_reservation=0 & called:get_flight_status=0` | 167 | tool:get_reservation_details | 0.56 | 0.44 | 10.2% | 5.9% | 11.9% | 1.3% | jev |
| 31 | `n_tool_calls=3+ & called:search_direct_flight=1 & called:calculate=0 & called:update_reservation_flights=0 & prev_role=tool & called:search_onestop_flight=1` | 35 | message | 0.60 | 0.44 | 40.0% | 35.7% | 3.4% | 1.3% | jev |
| 22 | `n_tool_calls=3+ & called:search_direct_flight=0 & prev_role=tool & called:cancel_reservation=1` | 43 | message | 0.56 | 0.40 | 30.2% | 0.0% | 3.6% | 1.2% | jev |
| 33 | `n_tool_calls=3+ & called:search_direct_flight=1 & called:calculate=0 & called:update_reservation_flights=0 & prev_role=user & user_confirms=1` | 54 | tool:update_reservation_flights | 0.35 | 0.64 | 22.2% | 41.7% | 5.2% | 1.1% | jev |
| 15 | `n_tool_calls=2 & prev_role=user` | 43 | message | 0.42 | 0.65 | 39.5% | 94.1% | 2.9% | 1.1% | jev |
| 7 | `n_tool_calls=0 & have:user_id=1 & user_short=1` | 31 | tool:get_user_details | 0.58 | 0.32 | 64.5% | 100.0% | 1.6% | 1.0% | jev |
| 14 | `n_tool_calls=2 & prev_role=tool` | 98 | tool:get_reservation_details | 0.49 | 0.44 | 14.3% | 7.1% | 6.1% | 0.9% | jev |
| 11 | `n_tool_calls=1 & called:get_user_details=0 & prev_role=user` | 29 | message | 0.28 | 0.55 | 41.4% | 83.3% | 1.8% | 0.7% | jev |
| 10 | `n_tool_calls=1 & called:get_user_details=0 & prev_role=tool` | 34 | message | 0.68 | 0.29 | 26.5% | 100.0% | 2.0% | 0.5% | jev |
| 38 | `n_tool_calls=3+ & called:search_direct_flight=1 & called:calculate=1 & called:cancel_reservation=0 & called:search_onestop_flight=0` | 47 | message | 0.55 | 0.55 | 12.8% | 33.3% | 4.2% | 0.5% | jev |
| 34 | `n_tool_calls=3+ & called:search_direct_flight=1 & called:calculate=0 & called:update_reservation_flights=0 & prev_role=user & user_confirms=0` | 21 | message | 0.52 | 0.55 | 23.8% | 40.0% | 1.8% | 0.5% | jev |
| 39 | `n_tool_calls=3+ & called:search_direct_flight=1 & called:calculate=1 & called:cancel_reservation=0 & called:search_onestop_flight=1` | 31 | tool:calculate | 0.19 | 0.56 | 9.7% | 33.3% | 3.1% | 0.3% | jev |
| 3 | `n_tool_calls=0 & have:user_id=0 & prev_role=start` | 100 | message | 1.00 | 0.00 | 0.0% | 0.0% | 0.0% | 0.0% | jev |
| 4 | `n_tool_calls=0 & have:user_id=0 & prev_role=user` | 103 | message | 0.94 | 0.10 | 0.0% | 0.0% | 5.2% | 0.0% | jev |
| 12 | `n_tool_calls=1 & called:get_user_details=1` | 79 | tool:get_reservation_details | 0.82 | 0.19 | 0.0% | 0.0% | 4.5% | 0.0% | jev |
| 40 | `n_tool_calls=3+ & called:search_direct_flight=1 & called:calculate=1 & called:cancel_reservation=1` | 0 | tool:calculate | 0.00 | 0.00 | 0.0% | 0.0% | 0.0% | 0.0% | jev |
