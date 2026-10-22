# GDOpt local verification: gpt-4.1-2025-04-14_airline_default_gpt-4.1-2025-04-14_4trials with typesafe/jev-1.14

- shadow calls: 400; decision-model cost $0.0726
- agreement with the LLM: 78.2% (on successful trajectories: 80.9%); ECE 0.031
- disagreement verdicts against reference actions: {'agree': 313, 'undecidable': 75, 'llm_right': 11, 'jev_right': 1}

## Coverage curve (all steps)

| tau | agreement among kept | steps kept |
| ---: | ---: | ---: |
| 0.5 | 81.6% | 93.5% |
| 0.6 | 84.4% | 85.0% |
| 0.7 | 88.6% | 74.5% |
| 0.8 | 92.2% | 61.3% |
| 0.9 | 95.6% | 45.5% |
| 0.95 | 98.4% | 31.8% |

## Per situation

| # | rule | n | agreement | on success | ECE | agree@0.9 / kept | verdicts |
| ---: | --- | ---: | ---: | ---: | ---: | --- | --- |
| 4 | `n_tool_calls=0 & have:user_id=0 & prev_role=user` | 42 | 92.9% | 92.0% (25) | 0.04 | 100.0% / 81.0% | {'agree': 39, 'undecidable': 3} |
| 3 | `n_tool_calls=0 & have:user_id=0 & prev_role=start` | 40 | 100.0% | 100.0% (22) | 0.00 | 100.0% / 100.0% | {'agree': 40} |
| 19 | `n_tool_calls=2 & user_confirms=0 & prev_role=tool` | 38 | 73.7% | 83.3% (18) | 0.10 | 94.1% / 44.7% | {'undecidable': 9, 'agree': 28, 'llm_right': 1} |
| 33 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=1 & called:calculate=1` | 37 | 75.7% | 81.2% (16) | 0.18 | 100.0% / 45.9% | {'undecidable': 9, 'agree': 28} |
| 31 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=1 & called:calculate=0 & called:cancel_reservation=0` | 32 | 75.0% | 61.9% (21) | 0.16 | 92.9% / 43.8% | {'agree': 24, 'llm_right': 1, 'undecidable': 7} |
| 27 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=0 & called:update_reservation_flights=0 & called:get_flight_status=1` | 27 | 70.4% | 90.9% (11) | 0.12 | 66.7% / 11.1% | {'undecidable': 8, 'agree': 19} |
| 15 | `n_tool_calls=1 & called:get_user_details=1 & prev_role=tool` | 24 | 70.8% | 90.0% (10) | 0.23 | 40.0% / 20.8% | {'undecidable': 7, 'agree': 17} |
| 26 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=0 & called:update_reservation_flights=0 & called:get_flight_status=0` | 23 | 82.6% | 81.2% (16) | 0.17 | 91.7% / 52.2% | {'agree': 19, 'undecidable': 4} |
| 20 | `n_tool_calls=2 & user_confirms=0 & prev_role=user` | 18 | 61.1% | 66.7% (9) | 0.24 | 100.0% / 44.4% | {'agree': 11, 'undecidable': 7} |
| 13 | `n_tool_calls=1 & called:get_user_details=0 & prev_role=user` | 17 | 82.4% | 85.7% (14) | 0.13 | 100.0% / 17.6% | {'agree': 14, 'llm_right': 1, 'undecidable': 2} |
| 6 | `n_tool_calls=0 & have:user_id=1 & user_short=1` | 15 | 93.3% | 80.0% (5) | 0.13 | 100.0% / 53.3% | {'agree': 14, 'llm_right': 1} |
| 9 | `n_tool_calls=0 & have:user_id=1 & user_short=0 & user_confirms=0` | 14 | 57.1% | 50.0% (6) | 0.19 | 100.0% / 14.3% | {'agree': 8, 'undecidable': 5, 'llm_right': 1} |
| 21 | `n_tool_calls=2 & user_confirms=1` | 14 | 71.4% | 60.0% (5) | 0.22 | 100.0% / 28.6% | {'agree': 10, 'undecidable': 3, 'llm_right': 1} |
| 8 | `n_tool_calls=0 & have:user_id=1 & user_short=0 & user_confirms=1` | 13 | 61.5% | 70.0% (10) | 0.26 | 100.0% / 7.7% | {'agree': 8, 'llm_right': 3, 'undecidable': 2} |
| 16 | `n_tool_calls=1 & called:get_user_details=1 & prev_role=user` | 13 | 84.6% | 100.0% (6) | 0.14 | 100.0% / 53.8% | {'jev_right': 1, 'agree': 11, 'llm_right': 1} |
| 12 | `n_tool_calls=1 & called:get_user_details=0 & prev_role=tool` | 10 | 60.0% | 83.3% (6) | 0.17 | 100.0% / 20.0% | {'undecidable': 4, 'agree': 6} |
| 36 | `n_tool_calls=3+ & user_confirms=1 & called:calculate=1` | 9 | 66.7% | 66.7% (6) | 0.38 | 100.0% / 11.1% | {'undecidable': 2, 'agree': 6, 'llm_right': 1} |
| 28 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=0 & called:update_reservation_flights=1` | 8 | 75.0% | 33.3% (3) | 0.18 | 75.0% / 50.0% | {'undecidable': 2, 'agree': 6} |
| 32 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=1 & called:calculate=0 & called:cancel_reservation=1` | 6 | 83.3% | 0.0% (0) | 0.15 | 0.0% / 0.0% | {'agree': 5, 'undecidable': 1} |
