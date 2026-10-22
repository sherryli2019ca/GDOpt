# GDOpt local verification: gpt-4.1-2025-04-14_airline_default_gpt-4.1-2025-04-14_4trials with typesafe/jev-1.14

- shadow calls: 400; decision-model cost $0.1404
- agreement with the LLM: 74.0% (on successful trajectories: 76.6%); ECE 0.069
- disagreement verdicts against reference actions: {'agree': 296, 'undecidable': 82, 'llm_right': 21, 'jev_right': 1}

## Coverage curve (all steps)

| tau | agreement among kept | steps kept |
| ---: | ---: | ---: |
| 0.5 | 74.8% | 97.2% |
| 0.6 | 78.8% | 87.2% |
| 0.7 | 80.4% | 77.8% |
| 0.8 | 87.8% | 57.2% |
| 0.9 | 98.8% | 20.0% |
| 0.95 | 0.0% | 0.0% |

## Per situation

| # | rule | n | agreement | on success | ECE | agree@0.9 / kept | verdicts |
| ---: | --- | ---: | ---: | ---: | ---: | --- | --- |
| 4 | `n_tool_calls=0 & have:user_id=0 & prev_role=user` | 42 | 95.2% | 96.0% (25) | 0.10 | 100.0% / 76.2% | {'agree': 40, 'undecidable': 2} |
| 3 | `n_tool_calls=0 & have:user_id=0 & prev_role=start` | 40 | 100.0% | 100.0% (22) | 0.06 | 100.0% / 100.0% | {'agree': 40} |
| 19 | `n_tool_calls=2 & user_confirms=0 & prev_role=tool` | 38 | 73.7% | 88.9% (18) | 0.12 | 100.0% / 2.6% | {'agree': 28, 'undecidable': 9, 'llm_right': 1} |
| 33 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=1 & called:calculate=1` | 37 | 73.0% | 81.2% (16) | 0.15 | 0.0% / 0.0% | {'undecidable': 10, 'agree': 27} |
| 31 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=1 & called:calculate=0 & called:cancel_reservation=0` | 32 | 68.8% | 57.1% (21) | 0.14 | 0.0% / 0.0% | {'agree': 22, 'llm_right': 1, 'undecidable': 9} |
| 27 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=0 & called:update_reservation_flights=0 & called:get_flight_status=1` | 27 | 66.7% | 72.7% (11) | 0.07 | 0.0% / 0.0% | {'undecidable': 9, 'agree': 18} |
| 15 | `n_tool_calls=1 & called:get_user_details=1 & prev_role=tool` | 24 | 54.2% | 80.0% (10) | 0.23 | 0.0% / 4.2% | {'undecidable': 9, 'agree': 13, 'llm_right': 2} |
| 26 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=0 & called:update_reservation_flights=0 & called:get_flight_status=0` | 23 | 78.3% | 75.0% (16) | 0.08 | 100.0% / 4.3% | {'agree': 18, 'llm_right': 1, 'undecidable': 4} |
| 20 | `n_tool_calls=2 & user_confirms=0 & prev_role=user` | 18 | 66.7% | 66.7% (9) | 0.23 | 100.0% / 11.1% | {'undecidable': 6, 'agree': 12} |
| 13 | `n_tool_calls=1 & called:get_user_details=0 & prev_role=user` | 17 | 76.5% | 78.6% (14) | 0.23 | 100.0% / 5.9% | {'agree': 13, 'llm_right': 1, 'undecidable': 3} |
| 6 | `n_tool_calls=0 & have:user_id=1 & user_short=1` | 15 | 86.7% | 80.0% (5) | 0.26 | 100.0% / 6.7% | {'agree': 13, 'llm_right': 2} |
| 9 | `n_tool_calls=0 & have:user_id=1 & user_short=0 & user_confirms=0` | 14 | 35.7% | 33.3% (6) | 0.41 | 0.0% / 0.0% | {'agree': 5, 'llm_right': 3, 'undecidable': 6} |
| 21 | `n_tool_calls=2 & user_confirms=1` | 14 | 64.3% | 60.0% (5) | 0.34 | 0.0% / 0.0% | {'agree': 9, 'undecidable': 4, 'llm_right': 1} |
| 8 | `n_tool_calls=0 & have:user_id=1 & user_short=0 & user_confirms=1` | 13 | 23.1% | 10.0% (10) | 0.46 | 0.0% / 0.0% | {'undecidable': 3, 'agree': 3, 'llm_right': 7} |
| 16 | `n_tool_calls=1 & called:get_user_details=1 & prev_role=user` | 13 | 69.2% | 83.3% (6) | 0.27 | 0.0% / 0.0% | {'jev_right': 1, 'agree': 9, 'llm_right': 1, 'undecidable': 2} |
| 12 | `n_tool_calls=1 & called:get_user_details=0 & prev_role=tool` | 10 | 80.0% | 100.0% (6) | 0.09 | 100.0% / 10.0% | {'agree': 8, 'undecidable': 2} |
| 36 | `n_tool_calls=3+ & user_confirms=1 & called:calculate=1` | 9 | 66.7% | 83.3% (6) | 0.14 | 0.0% / 0.0% | {'undecidable': 3, 'agree': 6} |
| 28 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=0 & called:update_reservation_flights=1` | 8 | 75.0% | 66.7% (3) | 0.19 | 0.0% / 0.0% | {'agree': 6, 'undecidable': 1, 'llm_right': 1} |
| 32 | `n_tool_calls=3+ & user_confirms=0 & called:search_direct_flight=1 & called:calculate=0 & called:cancel_reservation=1` | 6 | 100.0% | 0.0% (0) | 0.20 | 0.0% / 0.0% | {'agree': 6} |
