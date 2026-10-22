# GDOpt local verification: gpt-4.1-2025-04-14_retail_default_gpt-4.1-2025-04-14_4trials with typesafe/jev-1.14

- shadow calls: 400; decision-model cost $0.0801
- agreement with the LLM: 86.2% (on successful trajectories: 88.4%); ECE 0.054
- disagreement verdicts against reference actions: {'agree': 345, 'undecidable': 40, 'llm_right': 15}

## Coverage curve (all steps)

| tau | agreement among kept | steps kept |
| ---: | ---: | ---: |
| 0.5 | 87.9% | 97.5% |
| 0.6 | 91.7% | 87.8% |
| 0.7 | 94.3% | 75.0% |
| 0.8 | 98.0% | 63.5% |
| 0.9 | 98.9% | 45.8% |
| 0.95 | 99.2% | 30.0% |

## Per situation

| # | rule | n | agreement | on success | ECE | agree@0.9 / kept | verdicts |
| ---: | --- | ---: | ---: | ---: | ---: | --- | --- |
| 3 | `n_tool_calls=0 & have:zip=0 & have:email=0` | 77 | 98.7% | 98.3% (60) | 0.14 | 100.0% / 46.8% | {'agree': 76, 'undecidable': 1} |
| 22 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=0 & prev_role=tool & called:return_delivered_order_items=0 & called:get_order_details=1` | 54 | 81.5% | 84.2% (38) | 0.12 | 100.0% / 42.6% | {'undecidable': 6, 'agree': 44, 'llm_right': 4} |
| 33 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=1 & prev_role=tool & called:return_delivered_order_items=0 & called:exchange_delivered_order_items=0` | 38 | 92.1% | 90.9% (22) | 0.08 | 100.0% / 39.5% | {'agree': 35, 'undecidable': 2, 'llm_right': 1} |
| 14 | `n_tool_calls=2 & called:get_user_details=1 & prev_role=tool` | 36 | 55.6% | 60.0% (25) | 0.16 | 100.0% / 5.6% | {'agree': 20, 'undecidable': 13, 'llm_right': 3} |
| 46 | `n_tool_calls=3+ & user_confirms=1 & called:get_product_details=1 & called:find_user_id_by_email=0` | 26 | 76.9% | 86.7% (15) | 0.13 | 91.7% / 46.2% | {'undecidable': 4, 'agree': 20, 'llm_right': 2} |
| 10 | `n_tool_calls=1 & prev_tool=find_user_id_by_name_zip` | 22 | 86.4% | 92.9% (14) | 0.16 | 100.0% / 9.1% | {'undecidable': 2, 'agree': 19, 'llm_right': 1} |
| 6 | `n_tool_calls=0 & have:zip=1 & user_confirms=1` | 21 | 100.0% | 100.0% (18) | 0.00 | 100.0% / 100.0% | {'agree': 21} |
| 27 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=0 & prev_role=user & user_short=0 & called:find_user_id_by_name_zip=1` | 20 | 70.0% | 73.3% (15) | 0.09 | 100.0% / 25.0% | {'agree': 14, 'undecidable': 5, 'llm_right': 1} |
| 24 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=0 & prev_role=tool & called:return_delivered_order_items=1` | 15 | 86.7% | 84.6% (13) | 0.12 | 91.7% / 80.0% | {'agree': 13, 'llm_right': 1, 'undecidable': 1} |
| 15 | `n_tool_calls=2 & called:get_user_details=1 & prev_role=user` | 13 | 76.9% | 83.3% (12) | 0.12 | 100.0% / 69.2% | {'llm_right': 2, 'agree': 10, 'undecidable': 1} |
| 34 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=1 & prev_role=tool & called:return_delivered_order_items=0 & called:exchange_delivered_order_items=1` | 10 | 100.0% | 100.0% (7) | 0.02 | 100.0% / 90.0% | {'agree': 10} |
| 7 | `n_tool_calls=0 & have:zip=1 & user_confirms=0` | 9 | 100.0% | 100.0% (6) | 0.00 | 100.0% / 100.0% | {'agree': 9} |
| 38 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=1 & prev_role=user & called:exchange_delivered_order_items=0 & called:modify_pending_order_items=0` | 9 | 77.8% | 71.4% (7) | 0.28 | 100.0% / 22.2% | {'agree': 7, 'undecidable': 2} |
| 35 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=1 & prev_role=tool & called:return_delivered_order_items=1` | 8 | 100.0% | 100.0% (4) | 0.08 | 100.0% / 75.0% | {'agree': 8} |
| 9 | `n_tool_calls=1 & prev_tool=find_user_id_by_email` | 7 | 100.0% | 100.0% (6) | 0.29 | 0.0% / 0.0% | {'agree': 7} |
| 40 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=1 & prev_role=user & called:exchange_delivered_order_items=1` | 6 | 66.7% | 75.0% (4) | 0.21 | 100.0% / 50.0% | {'agree': 4, 'undecidable': 2} |
| 43 | `n_tool_calls=3+ & user_confirms=1 & called:get_product_details=0 & called:find_user_id_by_name_zip=0` | 6 | 100.0% | 100.0% (6) | 0.14 | 100.0% / 50.0% | {'agree': 6} |
| 4 | `n_tool_calls=0 & have:zip=0 & have:email=1` | 5 | 100.0% | 100.0% (5) | 0.00 | 100.0% / 100.0% | {'agree': 5} |
| 47 | `n_tool_calls=3+ & user_confirms=1 & called:get_product_details=1 & called:find_user_id_by_email=1` | 5 | 100.0% | 100.0% (3) | 0.05 | 100.0% / 80.0% | {'agree': 5} |
| 28 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=0 & prev_role=user & user_short=0 & called:find_user_id_by_name_zip=0` | 4 | 100.0% | 100.0% (4) | 0.31 | 0.0% / 0.0% | {'agree': 4} |
| 11 | `n_tool_calls=1 & prev_tool=-` | 3 | 100.0% | 100.0% (3) | 0.09 | 100.0% / 66.7% | {'agree': 3} |
| 16 | `n_tool_calls=2 & called:get_user_details=0` | 3 | 66.7% | 66.7% (3) | 0.37 | 0.0% / 0.0% | {'undecidable': 1, 'agree': 2} |
| 39 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=1 & prev_role=user & called:exchange_delivered_order_items=0 & called:modify_pending_order_items=1` | 2 | 100.0% | 100.0% (2) | 0.01 | 100.0% / 100.0% | {'agree': 2} |
| 29 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=0 & prev_role=user & user_short=1` | 1 | 100.0% | 100.0% (1) | 0.01 | 100.0% / 100.0% | {'agree': 1} |
