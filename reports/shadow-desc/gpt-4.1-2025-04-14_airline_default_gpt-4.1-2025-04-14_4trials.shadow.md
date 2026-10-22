# GDOpt local verification: gpt-4.1-2025-04-14_airline_default_gpt-4.1-2025-04-14_4trials with typesafe/jev-1.14

- shadow calls: 400; decision-model cost $0.0733
- agreement with the LLM: 78.8% (on successful trajectories: 83.3%); ECE 0.045
- disagreement verdicts against reference actions: {'agree': 315, 'undecidable': 74, 'llm_right': 11}

## Coverage curve (all steps)

| tau | agreement among kept | steps kept |
| ---: | ---: | ---: |
| 0.5 | 80.6% | 96.5% |
| 0.6 | 84.5% | 87.2% |
| 0.7 | 88.3% | 76.8% |
| 0.8 | 91.0% | 66.5% |
| 0.9 | 95.5% | 49.8% |
| 0.95 | 97.9% | 35.0% |

## Per situation

| # | rule | n | agreement | on success | ECE | agree@0.9 / kept | verdicts |
| ---: | --- | ---: | ---: | ---: | ---: | --- | --- |
| 4 | `n_tool_calls=0 & have:user_id=0 & prev_role=user` | 42 | 95.2% | 96.0% (25) | 0.04 | 100.0% / 81.0% | {'agree': 40, 'undecidable': 2} |
| 3 | `n_tool_calls=0 & have:user_id=0 & prev_role=start` | 40 | 100.0% | 100.0% (22) | 0.00 | 100.0% / 100.0% | {'agree': 40} |
| 19 | `n_tool_calls=2 & user_confirms=0 & prev_role=tool` | 38 | 73.7% | 83.3% (18) | 0.18 | 100.0% / 42.1% | {'undecidable': 9, 'agree': 28, 'llm_right': 1} |
| 33 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=1 & called:calculate=1` | 37 | 75.7% | 81.2% (16) | 0.14 | 100.0% / 54.1% | {'undecidable': 9, 'agree': 28} |
| 31 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=1 & called:calculate=0 & called:cancel_reservation=0` | 32 | 78.1% | 71.4% (21) | 0.15 | 100.0% / 40.6% | {'agree': 25, 'undecidable': 7} |
| 27 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=0 & called:update_reservation_flights=0 & called:get_flight_status=1` | 27 | 70.4% | 90.9% (11) | 0.15 | 50.0% / 14.8% | {'undecidable': 8, 'agree': 19} |
| 15 | `n_tool_calls=1 & called:get_user_details=1 & prev_role=tool` | 24 | 70.8% | 100.0% (10) | 0.15 | 75.0% / 16.7% | {'undecidable': 7, 'agree': 17} |
| 26 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=0 & called:update_reservation_flights=0 & called:get_flight_status=0` | 23 | 82.6% | 81.2% (16) | 0.20 | 76.5% / 73.9% | {'agree': 19, 'undecidable': 4} |
| 20 | `n_tool_calls=2 & user_confirms=0 & prev_role=user` | 18 | 66.7% | 66.7% (9) | 0.15 | 100.0% / 44.4% | {'agree': 12, 'undecidable': 6} |
| 13 | `n_tool_calls=1 & called:get_user_details=0 & prev_role=user` | 17 | 82.4% | 85.7% (14) | 0.19 | 100.0% / 29.4% | {'agree': 14, 'llm_right': 1, 'undecidable': 2} |
| 6 | `n_tool_calls=0 & have:user_id=1 & user_short=1` | 15 | 86.7% | 80.0% (5) | 0.10 | 100.0% / 66.7% | {'agree': 13, 'llm_right': 2} |
| 9 | `n_tool_calls=0 & have:user_id=1 & user_short=0 & user_confirms=0` | 14 | 57.1% | 50.0% (6) | 0.26 | 100.0% / 14.3% | {'agree': 8, 'llm_right': 2, 'undecidable': 4} |
| 21 | `n_tool_calls=2 & user_confirms=1` | 14 | 64.3% | 40.0% (5) | 0.17 | 100.0% / 28.6% | {'agree': 9, 'undecidable': 4, 'llm_right': 1} |
| 8 | `n_tool_calls=0 & have:user_id=1 & user_short=0 & user_confirms=1` | 13 | 61.5% | 70.0% (10) | 0.30 | 66.7% / 46.2% | {'agree': 8, 'llm_right': 3, 'undecidable': 2} |
| 16 | `n_tool_calls=1 & called:get_user_details=1 & prev_role=user` | 13 | 84.6% | 100.0% (6) | 0.13 | 100.0% / 61.5% | {'undecidable': 1, 'agree': 11, 'llm_right': 1} |
| 12 | `n_tool_calls=1 & called:get_user_details=0 & prev_role=tool` | 10 | 60.0% | 83.3% (6) | 0.23 | 100.0% / 20.0% | {'agree': 6, 'undecidable': 4} |
| 36 | `n_tool_calls=3+ & user_confirms=1 & called:calculate=1` | 9 | 77.8% | 83.3% (6) | 0.34 | 100.0% / 11.1% | {'undecidable': 2, 'agree': 7} |
| 28 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=0 & called:update_reservation_flights=1` | 8 | 87.5% | 66.7% (3) | 0.22 | 100.0% / 62.5% | {'agree': 7, 'undecidable': 1} |
| 32 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=1 & called:calculate=0 & called:cancel_reservation=1` | 6 | 66.7% | 0.0% (0) | 0.27 | 0.0% / 0.0% | {'undecidable': 2, 'agree': 4} |
