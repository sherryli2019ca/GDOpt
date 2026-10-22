# GDOpt profile: gpt-4.1-2025-04-14_airline_default_gpt-4.1-2025-04-14_4trials (agent gpt-4.1-2025-04-14, user gpt-4.1-2025-04-14)

- trajectories: 100 train / 100 test; test steps: 1107; action options: 15
- agent cost on test trajectories: $5.42 (LLM ≈ $1.08/M prompt tokens; Jev/LLM price ratio 0.039)
- steps that are tool calls with all arguments already in context: 16.6%
- upper bound on cost saved if every such step skipped the LLM: 15.9%

## Actions on test steps

| action | steps | share |
| --- | ---: | ---: |
| message | 638 | 57.6% |
| tool:get_reservation_details | 133 | 12.0% |
| tool:get_user_details | 74 | 6.7% |
| tool:calculate | 62 | 5.6% |
| tool:search_direct_flight | 51 | 4.6% |
| tool:update_reservation_flights | 34 | 3.1% |
| tool:cancel_reservation | 24 | 2.2% |
| tool:get_flight_status | 23 | 2.1% |
| tool:transfer_to_human_agents | 18 | 1.6% |
| tool:search_onestop_flight | 16 | 1.4% |
| tool:book_reservation | 14 | 1.3% |
| tool:update_reservation_baggages | 12 | 1.1% |
| tool:send_certificate | 5 | 0.5% |
| tool:update_reservation_passengers | 3 | 0.3% |

## Candidate tiers (stage 2, before any decision-model call)

| tier | situations | test steps | share of steps |
| --- | ---: | ---: | ---: |
| code | 0 | 0 | 0.0% |
| jev | 19 | 1071 | 96.7% |
| llm | 1 | 36 | 3.3% |

## Situations (sorted by potential saving)

| # | rule | n test | majority action | maj. acc | norm. entropy | closed tool | latest-rule acc | cost share | max saving | candidate |
| ---: | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 31 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=1 & called:calculate=0 & called:cancel_reservation=0` | 85 | message | 0.59 | 0.58 | 23.5% | 30.0% | 12.3% | 2.4% | jev |
| 21 | `n_tool_calls=2 & user_confirms=1` | 36 | message | 0.22 | 0.67 | 44.4% | 37.5% | 3.9% | 1.7% | jev |
| 20 | `n_tool_calls=2 & user_confirms=0 & prev_role=user` | 50 | message | 0.56 | 0.59 | 30.0% | 26.7% | 5.2% | 1.4% | jev |
| 26 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=0 & called:update_reservation_flights=0 & called:get_flight_status=0` | 82 | message | 0.54 | 0.51 | 13.4% | 9.1% | 9.2% | 1.3% | jev |
| 35 | `n_tool_calls=3+ & user_confirms=1 & called:calculate=0` | 36 | tool:update_reservation_flights | 0.31 | 0.77 | 27.8% | 50.0% | 5.0% | 1.2% | llm |
| 6 | `n_tool_calls=0 & have:user_id=1 & user_short=1` | 51 | tool:get_user_details | 0.57 | 0.35 | 56.9% | 100.0% | 2.2% | 1.2% | jev |
| 19 | `n_tool_calls=2 & user_confirms=0 & prev_role=tool` | 88 | message | 0.72 | 0.38 | 12.5% | 9.1% | 8.6% | 1.1% | jev |
| 27 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=0 & called:update_reservation_flights=0 & called:get_flight_status=1` | 65 | message | 0.55 | 0.50 | 18.5% | 16.7% | 7.0% | 1.0% | jev |
| 33 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=1 & called:calculate=1` | 95 | message | 0.60 | 0.41 | 6.3% | 33.3% | 16.5% | 1.0% | jev |
| 9 | `n_tool_calls=0 & have:user_id=1 & user_short=0 & user_confirms=0` | 38 | tool:get_user_details | 0.45 | 0.38 | 44.7% | 100.0% | 1.8% | 0.8% | jev |
| 36 | `n_tool_calls=3+ & user_confirms=1 & called:calculate=1` | 32 | tool:update_reservation_flights | 0.25 | 0.71 | 15.6% | 20.0% | 5.2% | 0.7% | jev |
| 13 | `n_tool_calls=1 & called:get_user_details=0 & prev_role=user` | 47 | message | 0.64 | 0.47 | 19.1% | 22.2% | 3.6% | 0.7% | jev |
| 8 | `n_tool_calls=0 & have:user_id=1 & user_short=0 & user_confirms=1` | 32 | tool:get_user_details | 0.50 | 0.40 | 50.0% | 100.0% | 1.4% | 0.6% | jev |
| 28 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=0 & called:update_reservation_flights=1` | 22 | message | 0.59 | 0.54 | 13.6% | 33.3% | 3.1% | 0.3% | jev |
| 12 | `n_tool_calls=1 & called:get_user_details=0 & prev_role=tool` | 37 | message | 0.78 | 0.25 | 5.4% | 50.0% | 2.4% | 0.1% | jev |
| 32 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=1 & called:calculate=0 & called:cancel_reservation=1` | 16 | message | 0.81 | 0.25 | 6.2% | 0.0% | 2.3% | 0.1% | jev |
| 16 | `n_tool_calls=1 & called:get_user_details=1 & prev_role=user` | 26 | tool:get_reservation_details | 0.92 | 0.12 | 3.8% | 0.0% | 1.6% | 0.1% | jev |
| 3 | `n_tool_calls=0 & have:user_id=0 & prev_role=start` | 100 | message | 1.00 | 0.00 | 0.0% | 0.0% | 0.0% | 0.0% | jev |
| 4 | `n_tool_calls=0 & have:user_id=0 & prev_role=user` | 106 | message | 0.95 | 0.08 | 0.0% | 0.0% | 4.8% | 0.0% | jev |
| 15 | `n_tool_calls=1 & called:get_user_details=1 & prev_role=tool` | 63 | tool:get_reservation_details | 0.51 | 0.36 | 0.0% | 0.0% | 3.9% | 0.0% | jev |
