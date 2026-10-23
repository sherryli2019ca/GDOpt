# GDOpt local verification: gpt-4.1-2025-04-14_airline_default_gpt-4.1-2025-04-14_4trials with typesafe/jev-1.14

- shadow calls: 400; decision-model cost $0.0449
- agreement with the LLM: 76.0% (on successful trajectories: 77.5%); ECE 0.060
- disagreement verdicts against reference actions: {'agree': 304, 'undecidable': 89, 'jev_right': 4, 'llm_right': 3}

## Coverage curve (all steps)

| tau | agreement among kept | steps kept |
| ---: | ---: | ---: |
| 0.5 | 79.3% | 91.8% |
| 0.6 | 82.5% | 80.0% |
| 0.7 | 84.6% | 68.0% |
| 0.8 | 87.7% | 54.8% |
| 0.9 | 92.6% | 43.8% |
| 0.95 | 95.7% | 35.2% |

## Per situation

| # | rule | n | agreement | on success | ECE | agree@0.9 / kept | verdicts |
| ---: | --- | ---: | ---: | ---: | ---: | --- | --- |
| 4 | `n_tool_calls=0 & have:user_id=0 & prev_role=user` | 42 | 73.8% | 76.0% (25) | 0.26 | 60.0% / 11.9% | {'agree': 31, 'undecidable': 11} |
| 3 | `n_tool_calls=0 & have:user_id=0 & prev_role=start` | 40 | 100.0% | 100.0% (22) | 0.03 | 100.0% / 100.0% | {'agree': 40} |
| 19 | `n_tool_calls=2 & user_confirms=0 & prev_role=tool` | 38 | 63.2% | 66.7% (18) | 0.15 | 100.0% / 18.4% | {'agree': 24, 'undecidable': 14} |
| 33 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=1 & called:calculate=1` | 37 | 78.4% | 81.2% (16) | 0.11 | 89.5% / 51.4% | {'agree': 29, 'undecidable': 8} |
| 31 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=1 & called:calculate=0 & called:cancel_reservation=0` | 32 | 78.1% | 71.4% (21) | 0.12 | 100.0% / 40.6% | {'agree': 25, 'undecidable': 7} |
| 27 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=0 & called:update_reservation_flights=0 & called:get_flight_status=1` | 27 | 74.1% | 81.8% (11) | 0.24 | 83.3% / 22.2% | {'undecidable': 7, 'agree': 20} |
| 15 | `n_tool_calls=1 & called:get_user_details=1 & prev_role=tool` | 24 | 79.2% | 100.0% (10) | 0.13 | 83.3% / 25.0% | {'undecidable': 5, 'agree': 19} |
| 6 | `n_tool_calls=0 & have:user_id=1 & have:reservation_id=1` | 23 | 56.5% | 68.8% (16) | 0.17 | 83.3% / 26.1% | {'agree': 13, 'jev_right': 3, 'llm_right': 2, 'undecidable': 5} |
| 26 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=0 & called:update_reservation_flights=0 & called:get_flight_status=0` | 23 | 69.6% | 62.5% (16) | 0.17 | 100.0% / 47.8% | {'agree': 16, 'llm_right': 1, 'undecidable': 6} |
| 20 | `n_tool_calls=2 & user_confirms=0 & prev_role=user` | 18 | 66.7% | 66.7% (9) | 0.26 | 85.7% / 38.9% | {'agree': 12, 'undecidable': 6} |
| 13 | `n_tool_calls=1 & called:get_user_details=0 & prev_role=user` | 17 | 88.2% | 92.9% (14) | 0.15 | 100.0% / 29.4% | {'agree': 15, 'undecidable': 2} |
| 21 | `n_tool_calls=2 & user_confirms=1` | 14 | 71.4% | 40.0% (5) | 0.14 | 88.9% / 64.3% | {'agree': 10, 'undecidable': 4} |
| 16 | `n_tool_calls=1 & called:get_user_details=1 & prev_role=user` | 13 | 92.3% | 100.0% (6) | 0.08 | 100.0% / 69.2% | {'undecidable': 1, 'agree': 12} |
| 8 | `n_tool_calls=0 & have:user_id=1 & have:reservation_id=0 & user_short=1` | 11 | 90.9% | 100.0% (2) | 0.09 | 100.0% / 81.8% | {'agree': 10, 'jev_right': 1} |
| 12 | `n_tool_calls=1 & called:get_user_details=0 & prev_role=tool` | 10 | 70.0% | 66.7% (6) | 0.10 | 100.0% / 20.0% | {'undecidable': 3, 'agree': 7} |
| 36 | `n_tool_calls=3+ & user_confirms=1 & called:calculate=1` | 9 | 66.7% | 66.7% (6) | 0.37 | 60.0% / 55.6% | {'undecidable': 3, 'agree': 6} |
| 9 | `n_tool_calls=0 & have:user_id=1 & have:reservation_id=0 & user_short=0` | 8 | 62.5% | 66.7% (3) | 0.23 | 83.3% / 75.0% | {'agree': 5, 'undecidable': 3} |
| 28 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=0 & called:update_reservation_flights=1` | 8 | 87.5% | 66.7% (3) | 0.17 | 100.0% / 75.0% | {'agree': 7, 'undecidable': 1} |
| 32 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=1 & called:calculate=0 & called:cancel_reservation=1` | 6 | 50.0% | 0.0% (0) | 0.39 | 75.0% / 66.7% | {'undecidable': 3, 'agree': 3} |
