# GDOpt local verification: gpt-4.1-2025-04-14_telecom_default_gpt-4.1-2025-04-14_4trials with typesafe/jev-1.14

- shadow calls: 400; decision-model cost $0.1403
- agreement with the LLM: 70.5% (on successful trajectories: 67.6%); ECE 0.070
- disagreement verdicts against reference actions: {'agree': 282, 'undecidable': 115, 'jev_right': 2, 'llm_right': 1}

## Coverage curve (all steps)

| tau | agreement among kept | steps kept |
| ---: | ---: | ---: |
| 0.5 | 73.2% | 92.5% |
| 0.6 | 79.0% | 77.2% |
| 0.7 | 87.7% | 55.0% |
| 0.8 | 88.7% | 35.2% |
| 0.9 | 100.0% | 7.2% |
| 0.95 | 0.0% | 0.0% |

## Per situation

| # | rule | n | agreement | on success | ECE | agree@0.9 / kept | verdicts |
| ---: | --- | ---: | ---: | ---: | ---: | --- | --- |
| 6 | `n_tool_calls=1 & prev_role=user` | 85 | 83.5% | 76.2% (21) | 0.16 | 100.0% / 2.4% | {'undecidable': 14, 'agree': 71} |
| 2 | `n_tool_calls=0 & have:phone_number=0` | 51 | 100.0% | 100.0% (14) | 0.11 | 100.0% / 21.6% | {'agree': 51} |
| 30 | `n_tool_calls=3+ & prev_role=user & called:get_bills_for_customer=0 & called:refuel_data=0 & called:get_data_usage=0 & user_confirms=0` | 48 | 75.0% | 100.0% (8) | 0.11 | 100.0% / 6.2% | {'agree': 36, 'undecidable': 12} |
| 15 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=0 & called:transfer_to_human_agents=0 & have:gb_amount=0 & called:get_data_usage=0` | 47 | 38.3% | 44.4% (9) | 0.40 | 0.0% / 0.0% | {'agree': 18, 'jev_right': 2, 'undecidable': 27} |
| 35 | `n_tool_calls=3+ & prev_role=user & called:get_bills_for_customer=0 & called:refuel_data=1` | 25 | 76.0% | 100.0% (5) | 0.17 | 100.0% / 16.0% | {'undecidable': 6, 'agree': 19} |
| 5 | `n_tool_calls=1 & prev_role=tool` | 23 | 60.9% | 50.0% (8) | 0.10 | 0.0% / 0.0% | {'agree': 14, 'undecidable': 9} |
| 3 | `n_tool_calls=0 & have:phone_number=1` | 19 | 63.2% | 66.7% (6) | 0.28 | 100.0% / 42.1% | {'agree': 12, 'undecidable': 7} |
| 38 | `n_tool_calls=3+ & prev_role=user & called:get_bills_for_customer=1 & called:resume_line=1` | 17 | 94.1% | 87.5% (8) | 0.23 | 0.0% / 0.0% | {'agree': 16, 'undecidable': 1} |
| 8 | `n_tool_calls=2 & prev_role=tool` | 16 | 25.0% | 33.3% (3) | 0.44 | 0.0% / 0.0% | {'undecidable': 12, 'agree': 4} |
| 25 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=1 & called:send_payment_request=1 & called:resume_line=1` | 12 | 41.7% | 22.2% (9) | 0.39 | 0.0% / 0.0% | {'undecidable': 7, 'agree': 5} |
| 20 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=0 & called:transfer_to_human_agents=1` | 9 | 100.0% | 0.0% (0) | 0.23 | 0.0% / 0.0% | {'agree': 9} |
| 9 | `n_tool_calls=2 & prev_role=user` | 8 | 87.5% | 0.0% (0) | 0.16 | 0.0% / 0.0% | {'agree': 7, 'undecidable': 1} |
| 37 | `n_tool_calls=3+ & prev_role=user & called:get_bills_for_customer=1 & called:resume_line=0` | 8 | 12.5% | 20.0% (5) | 0.29 | 0.0% / 0.0% | {'agree': 1, 'undecidable': 7} |
| 24 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=1 & called:send_payment_request=1 & called:resume_line=0` | 6 | 83.3% | 100.0% (2) | 0.30 | 0.0% / 0.0% | {'agree': 5, 'undecidable': 1} |
| 19 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=0 & called:transfer_to_human_agents=0 & have:gb_amount=1 & called:get_data_usage=1` | 5 | 40.0% | 0.0% (0) | 0.40 | 0.0% / 0.0% | {'agree': 2, 'undecidable': 3} |
| 31 | `n_tool_calls=3+ & prev_role=user & called:get_bills_for_customer=0 & called:refuel_data=0 & called:get_data_usage=0 & user_confirms=1` | 5 | 100.0% | 100.0% (2) | 0.13 | 100.0% / 20.0% | {'agree': 5} |
| 16 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=0 & called:transfer_to_human_agents=0 & have:gb_amount=0 & called:get_data_usage=1` | 4 | 100.0% | 100.0% (1) | 0.32 | 0.0% / 0.0% | {'agree': 4} |
| 22 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=1 & called:send_payment_request=0` | 4 | 0.0% | 0.0% (2) | 0.62 | 0.0% / 0.0% | {'undecidable': 3, 'llm_right': 1} |
| 33 | `n_tool_calls=3+ & prev_role=user & called:get_bills_for_customer=0 & called:refuel_data=0 & called:get_data_usage=1 & user_confirms=0` | 4 | 0.0% | 0.0% (2) | 0.71 | 0.0% / 0.0% | {'undecidable': 4} |
| 18 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=0 & called:transfer_to_human_agents=0 & have:gb_amount=1 & called:get_data_usage=0` | 2 | 100.0% | 0.0% (0) | 0.27 | 0.0% / 0.0% | {'agree': 2} |
| 34 | `n_tool_calls=3+ & prev_role=user & called:get_bills_for_customer=0 & called:refuel_data=0 & called:get_data_usage=1 & user_confirms=1` | 2 | 50.0% | 0.0% (0) | 0.26 | 0.0% / 0.0% | {'agree': 1, 'undecidable': 1} |
