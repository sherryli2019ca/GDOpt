# GDOpt local verification: gpt-4.1-2025-04-14_telecom_default_gpt-4.1-2025-04-14_4trials with typesafe/jev-1.14

- shadow calls: 400; decision-model cost $0.0748
- agreement with the LLM: 71.2% (on successful trajectories: 80.0%); ECE 0.088
- disagreement verdicts against reference actions: {'agree': 285, 'undecidable': 113, 'jev_right': 2}

## Coverage curve (all steps)

| tau | agreement among kept | steps kept |
| ---: | ---: | ---: |
| 0.5 | 80.9% | 75.8% |
| 0.6 | 86.3% | 56.5% |
| 0.7 | 88.1% | 44.0% |
| 0.8 | 88.3% | 38.5% |
| 0.9 | 100.0% | 21.0% |
| 0.95 | 100.0% | 16.2% |

## Per situation

| # | rule | n | agreement | on success | ECE | agree@0.9 / kept | verdicts |
| ---: | --- | ---: | ---: | ---: | ---: | --- | --- |
| 6 | `n_tool_calls=1 & prev_role=user` | 85 | 65.9% | 71.4% (21) | 0.09 | 100.0% / 7.1% | {'agree': 56, 'undecidable': 29} |
| 2 | `n_tool_calls=0 & have:phone_number=0` | 51 | 100.0% | 100.0% (14) | 0.09 | 100.0% / 58.8% | {'agree': 51} |
| 30 | `n_tool_calls=3+ & prev_role=user & called:get_bills_for_customer=0 & called:refuel_data=0 & called:get_data_usage=0 & user_confirms=0` | 48 | 66.7% | 87.5% (8) | 0.12 | 100.0% / 16.7% | {'agree': 32, 'undecidable': 16} |
| 15 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=0 & called:transfer_to_human_agents=0 & have:gb_amount=0 & called:get_data_usage=0` | 47 | 36.2% | 77.8% (9) | 0.45 | 0.0% / 0.0% | {'undecidable': 28, 'jev_right': 2, 'agree': 17} |
| 35 | `n_tool_calls=3+ & prev_role=user & called:get_bills_for_customer=0 & called:refuel_data=1` | 25 | 76.0% | 100.0% (5) | 0.14 | 100.0% / 28.0% | {'agree': 19, 'undecidable': 6} |
| 5 | `n_tool_calls=1 & prev_role=tool` | 23 | 69.6% | 75.0% (8) | 0.18 | 0.0% / 0.0% | {'agree': 16, 'undecidable': 7} |
| 3 | `n_tool_calls=0 & have:phone_number=1` | 19 | 100.0% | 100.0% (6) | 0.02 | 100.0% / 100.0% | {'agree': 19} |
| 38 | `n_tool_calls=3+ & prev_role=user & called:get_bills_for_customer=1 & called:resume_line=1` | 17 | 82.4% | 87.5% (8) | 0.28 | 100.0% / 5.9% | {'undecidable': 3, 'agree': 14} |
| 8 | `n_tool_calls=2 & prev_role=tool` | 16 | 62.5% | 100.0% (3) | 0.14 | 0.0% / 0.0% | {'undecidable': 6, 'agree': 10} |
| 25 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=1 & called:send_payment_request=1 & called:resume_line=1` | 12 | 50.0% | 33.3% (9) | 0.21 | 100.0% / 16.7% | {'undecidable': 6, 'agree': 6} |
| 20 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=0 & called:transfer_to_human_agents=1` | 9 | 100.0% | 0.0% (0) | 0.20 | 0.0% / 0.0% | {'agree': 9} |
| 9 | `n_tool_calls=2 & prev_role=user` | 8 | 87.5% | 0.0% (0) | 0.27 | 100.0% / 25.0% | {'agree': 7, 'undecidable': 1} |
| 37 | `n_tool_calls=3+ & prev_role=user & called:get_bills_for_customer=1 & called:resume_line=0` | 8 | 62.5% | 60.0% (5) | 0.21 | 0.0% / 0.0% | {'agree': 5, 'undecidable': 3} |
| 24 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=1 & called:send_payment_request=1 & called:resume_line=0` | 6 | 100.0% | 100.0% (2) | 0.27 | 100.0% / 33.3% | {'agree': 6} |
| 19 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=0 & called:transfer_to_human_agents=0 & have:gb_amount=1 & called:get_data_usage=1` | 5 | 40.0% | 0.0% (0) | 0.36 | 100.0% / 40.0% | {'agree': 2, 'undecidable': 3} |
| 31 | `n_tool_calls=3+ & prev_role=user & called:get_bills_for_customer=0 & called:refuel_data=0 & called:get_data_usage=0 & user_confirms=1` | 5 | 100.0% | 100.0% (2) | 0.14 | 100.0% / 40.0% | {'agree': 5} |
| 16 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=0 & called:transfer_to_human_agents=0 & have:gb_amount=0 & called:get_data_usage=1` | 4 | 100.0% | 100.0% (1) | 0.20 | 100.0% / 25.0% | {'agree': 4} |
| 22 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=1 & called:send_payment_request=0` | 4 | 75.0% | 100.0% (2) | 0.39 | 0.0% / 0.0% | {'undecidable': 1, 'agree': 3} |
| 33 | `n_tool_calls=3+ & prev_role=user & called:get_bills_for_customer=0 & called:refuel_data=0 & called:get_data_usage=1 & user_confirms=0` | 4 | 25.0% | 50.0% (2) | 0.61 | 0.0% / 0.0% | {'undecidable': 3, 'agree': 1} |
| 18 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=0 & called:transfer_to_human_agents=0 & have:gb_amount=1 & called:get_data_usage=0` | 2 | 100.0% | 0.0% (0) | 0.13 | 100.0% / 50.0% | {'agree': 2} |
| 34 | `n_tool_calls=3+ & prev_role=user & called:get_bills_for_customer=0 & called:refuel_data=0 & called:get_data_usage=1 & user_confirms=1` | 2 | 50.0% | 0.0% (0) | 0.38 | 100.0% / 50.0% | {'agree': 1, 'undecidable': 1} |
