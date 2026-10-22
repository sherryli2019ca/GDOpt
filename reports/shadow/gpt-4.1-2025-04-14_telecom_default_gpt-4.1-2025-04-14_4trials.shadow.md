# GDOpt local verification: gpt-4.1-2025-04-14_telecom_default_gpt-4.1-2025-04-14_4trials with typesafe/jev-1.14

- shadow calls: 400; decision-model cost $0.0690
- agreement with the LLM: 72.5% (on successful trajectories: 76.2%); ECE 0.085
- disagreement verdicts against reference actions: {'agree': 290, 'undecidable': 107, 'jev_right': 2, 'llm_right': 1}

## Coverage curve (all steps)

| tau | agreement among kept | steps kept |
| ---: | ---: | ---: |
| 0.5 | 80.2% | 78.2% |
| 0.6 | 85.2% | 59.2% |
| 0.7 | 86.9% | 49.5% |
| 0.8 | 88.4% | 41.0% |
| 0.9 | 100.0% | 24.8% |
| 0.95 | 100.0% | 16.0% |

## Per situation

| # | rule | n | agreement | on success | ECE | agree@0.9 / kept | verdicts |
| ---: | --- | ---: | ---: | ---: | ---: | --- | --- |
| 6 | `n_tool_calls=1 & prev_role=user` | 85 | 74.1% | 85.7% (21) | 0.16 | 100.0% / 8.2% | {'agree': 63, 'undecidable': 22} |
| 2 | `n_tool_calls=0 & have:phone_number=0` | 51 | 100.0% | 100.0% (14) | 0.06 | 100.0% / 80.4% | {'agree': 51} |
| 30 | `n_tool_calls=3+ & prev_role=user & called:get_bills_for_customer=0 & called:refuel_data=0 & called:get_data_usage=0 & user_confirms=0` | 48 | 66.7% | 87.5% (8) | 0.13 | 100.0% / 20.8% | {'agree': 32, 'undecidable': 16} |
| 15 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=0 & called:transfer_to_human_agents=0 & have:gb_amount=0 & called:get_data_usage=0` | 47 | 34.0% | 55.6% (9) | 0.39 | 0.0% / 0.0% | {'undecidable': 29, 'jev_right': 2, 'agree': 16} |
| 35 | `n_tool_calls=3+ & prev_role=user & called:get_bills_for_customer=0 & called:refuel_data=1` | 25 | 80.0% | 100.0% (5) | 0.22 | 100.0% / 28.0% | {'agree': 20, 'undecidable': 5} |
| 5 | `n_tool_calls=1 & prev_role=tool` | 23 | 82.6% | 87.5% (8) | 0.30 | 0.0% / 0.0% | {'agree': 19, 'undecidable': 4} |
| 3 | `n_tool_calls=0 & have:phone_number=1` | 19 | 100.0% | 100.0% (6) | 0.03 | 100.0% / 89.5% | {'agree': 19} |
| 38 | `n_tool_calls=3+ & prev_role=user & called:get_bills_for_customer=1 & called:resume_line=1` | 17 | 88.2% | 87.5% (8) | 0.30 | 100.0% / 5.9% | {'undecidable': 2, 'agree': 15} |
| 8 | `n_tool_calls=2 & prev_role=tool` | 16 | 81.2% | 100.0% (3) | 0.24 | 100.0% / 12.5% | {'undecidable': 3, 'agree': 13} |
| 25 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=1 & called:send_payment_request=1 & called:resume_line=1` | 12 | 50.0% | 33.3% (9) | 0.22 | 100.0% / 25.0% | {'undecidable': 6, 'agree': 6} |
| 20 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=0 & called:transfer_to_human_agents=1` | 9 | 100.0% | 0.0% (0) | 0.14 | 100.0% / 11.1% | {'agree': 9} |
| 9 | `n_tool_calls=2 & prev_role=user` | 8 | 87.5% | 0.0% (0) | 0.31 | 100.0% / 25.0% | {'agree': 7, 'undecidable': 1} |
| 37 | `n_tool_calls=3+ & prev_role=user & called:get_bills_for_customer=1 & called:resume_line=0` | 8 | 12.5% | 0.0% (5) | 0.35 | 0.0% / 0.0% | {'undecidable': 7, 'agree': 1} |
| 24 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=1 & called:send_payment_request=1 & called:resume_line=0` | 6 | 83.3% | 100.0% (2) | 0.21 | 100.0% / 16.7% | {'agree': 5, 'undecidable': 1} |
| 19 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=0 & called:transfer_to_human_agents=0 & have:gb_amount=1 & called:get_data_usage=1` | 5 | 40.0% | 0.0% (0) | 0.34 | 100.0% / 40.0% | {'agree': 2, 'undecidable': 3} |
| 31 | `n_tool_calls=3+ & prev_role=user & called:get_bills_for_customer=0 & called:refuel_data=0 & called:get_data_usage=0 & user_confirms=1` | 5 | 100.0% | 100.0% (2) | 0.15 | 100.0% / 40.0% | {'agree': 5} |
| 16 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=0 & called:transfer_to_human_agents=0 & have:gb_amount=0 & called:get_data_usage=1` | 4 | 100.0% | 100.0% (1) | 0.16 | 100.0% / 25.0% | {'agree': 4} |
| 22 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=1 & called:send_payment_request=0` | 4 | 0.0% | 0.0% (2) | 0.50 | 0.0% / 0.0% | {'undecidable': 3, 'llm_right': 1} |
| 33 | `n_tool_calls=3+ & prev_role=user & called:get_bills_for_customer=0 & called:refuel_data=0 & called:get_data_usage=1 & user_confirms=0` | 4 | 0.0% | 0.0% (2) | 0.68 | 0.0% / 0.0% | {'undecidable': 4} |
| 18 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=0 & called:transfer_to_human_agents=0 & have:gb_amount=1 & called:get_data_usage=0` | 2 | 100.0% | 0.0% (0) | 0.09 | 100.0% / 50.0% | {'agree': 2} |
| 34 | `n_tool_calls=3+ & prev_role=user & called:get_bills_for_customer=0 & called:refuel_data=0 & called:get_data_usage=1 & user_confirms=1` | 2 | 50.0% | 0.0% (0) | 0.42 | 100.0% / 50.0% | {'agree': 1, 'undecidable': 1} |
