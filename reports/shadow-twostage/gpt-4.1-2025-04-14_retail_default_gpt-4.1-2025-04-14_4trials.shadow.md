# GDOpt local verification: gpt-4.1-2025-04-14_retail_default_gpt-4.1-2025-04-14_4trials with typesafe/jev-1.14

- shadow calls: 400; decision-model cost $0.1466
- agreement with the LLM: 75.2% (on successful trajectories: 76.5%); ECE 0.127
- disagreement verdicts against reference actions: {'agree': 301, 'llm_right': 40, 'undecidable': 59}

## Coverage curve (all steps)

| tau | agreement among kept | steps kept |
| ---: | ---: | ---: |
| 0.5 | 76.0% | 99.0% |
| 0.6 | 77.8% | 91.2% |
| 0.7 | 82.5% | 81.5% |
| 0.8 | 92.9% | 63.7% |
| 0.9 | 100.0% | 9.2% |
| 0.95 | 100.0% | 0.2% |

## Per situation

| # | rule | n | agreement | on success | ECE | agree@0.9 / kept | verdicts |
| ---: | --- | ---: | ---: | ---: | ---: | --- | --- |
| 3 | `n_tool_calls=0 & have:zip=0 & have:email=0` | 77 | 100.0% | 100.0% (60) | 0.14 | 100.0% / 14.3% | {'agree': 77} |
| 22 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=0 & prev_role=tool & called:return_delivered_order_items=0 & called:get_order_details=1` | 54 | 59.3% | 63.2% (38) | 0.23 | 100.0% / 13.0% | {'undecidable': 12, 'agree': 32, 'llm_right': 10} |
| 33 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=1 & prev_role=tool & called:return_delivered_order_items=0 & called:exchange_delivered_order_items=0` | 38 | 86.8% | 81.8% (22) | 0.12 | 0.0% / 0.0% | {'agree': 33, 'undecidable': 4, 'llm_right': 1} |
| 14 | `n_tool_calls=2 & called:get_user_details=1 & prev_role=tool` | 36 | 55.6% | 56.0% (25) | 0.26 | 0.0% / 0.0% | {'agree': 20, 'undecidable': 12, 'llm_right': 4} |
| 46 | `n_tool_calls=3+ & user_confirms=1 & called:get_product_details=1 & called:find_user_id_by_email=0` | 26 | 76.9% | 86.7% (15) | 0.12 | 100.0% / 3.8% | {'undecidable': 4, 'agree': 20, 'llm_right': 2} |
| 10 | `n_tool_calls=1 & prev_tool=find_user_id_by_name_zip` | 22 | 13.6% | 14.3% (14) | 0.59 | 0.0% / 0.0% | {'llm_right': 9, 'undecidable': 10, 'agree': 3} |
| 6 | `n_tool_calls=0 & have:zip=1 & user_confirms=1` | 21 | 100.0% | 100.0% (18) | 0.13 | 100.0% / 14.3% | {'agree': 21} |
| 27 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=0 & prev_role=user & user_short=0 & called:find_user_id_by_name_zip=1` | 20 | 60.0% | 60.0% (15) | 0.27 | 100.0% / 15.0% | {'agree': 12, 'undecidable': 4, 'llm_right': 4} |
| 24 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=0 & prev_role=tool & called:return_delivered_order_items=1` | 15 | 86.7% | 84.6% (13) | 0.09 | 100.0% / 6.7% | {'agree': 13, 'llm_right': 1, 'undecidable': 1} |
| 15 | `n_tool_calls=2 & called:get_user_details=1 & prev_role=user` | 13 | 46.2% | 50.0% (12) | 0.22 | 0.0% / 0.0% | {'llm_right': 5, 'agree': 6, 'undecidable': 2} |
| 34 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=1 & prev_role=tool & called:return_delivered_order_items=0 & called:exchange_delivered_order_items=1` | 10 | 100.0% | 100.0% (7) | 0.16 | 100.0% / 10.0% | {'agree': 10} |
| 7 | `n_tool_calls=0 & have:zip=1 & user_confirms=0` | 9 | 100.0% | 100.0% (6) | 0.12 | 100.0% / 22.2% | {'agree': 9} |
| 38 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=1 & prev_role=user & called:exchange_delivered_order_items=0 & called:modify_pending_order_items=0` | 9 | 77.8% | 71.4% (7) | 0.26 | 0.0% / 0.0% | {'agree': 7, 'undecidable': 2} |
| 35 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=1 & prev_role=tool & called:return_delivered_order_items=1` | 8 | 100.0% | 100.0% (4) | 0.18 | 0.0% / 0.0% | {'agree': 8} |
| 9 | `n_tool_calls=1 & prev_tool=find_user_id_by_email` | 7 | 42.9% | 50.0% (6) | 0.35 | 0.0% / 0.0% | {'undecidable': 4, 'agree': 3} |
| 40 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=1 & prev_role=user & called:exchange_delivered_order_items=1` | 6 | 66.7% | 75.0% (4) | 0.27 | 100.0% / 16.7% | {'llm_right': 1, 'agree': 4, 'undecidable': 1} |
| 43 | `n_tool_calls=3+ & user_confirms=1 & called:get_product_details=0 & called:find_user_id_by_name_zip=0` | 6 | 100.0% | 100.0% (6) | 0.19 | 0.0% / 0.0% | {'agree': 6} |
| 4 | `n_tool_calls=0 & have:zip=0 & have:email=1` | 5 | 100.0% | 100.0% (5) | 0.09 | 100.0% / 80.0% | {'agree': 5} |
| 47 | `n_tool_calls=3+ & user_confirms=1 & called:get_product_details=1 & called:find_user_id_by_email=1` | 5 | 100.0% | 100.0% (3) | 0.14 | 100.0% / 20.0% | {'agree': 5} |
| 28 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=0 & prev_role=user & user_short=0 & called:find_user_id_by_name_zip=0` | 4 | 50.0% | 50.0% (4) | 0.28 | 0.0% / 0.0% | {'undecidable': 1, 'agree': 2, 'llm_right': 1} |
| 11 | `n_tool_calls=1 & prev_tool=-` | 3 | 33.3% | 33.3% (3) | 0.22 | 0.0% / 0.0% | {'undecidable': 1, 'agree': 1, 'llm_right': 1} |
| 16 | `n_tool_calls=2 & called:get_user_details=0` | 3 | 33.3% | 33.3% (3) | 0.66 | 0.0% / 0.0% | {'undecidable': 1, 'agree': 1, 'llm_right': 1} |
| 39 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=1 & prev_role=user & called:exchange_delivered_order_items=0 & called:modify_pending_order_items=1` | 2 | 100.0% | 100.0% (2) | 0.10 | 100.0% / 50.0% | {'agree': 2} |
| 29 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=0 & prev_role=user & user_short=1` | 1 | 100.0% | 100.0% (1) | 0.05 | 100.0% / 100.0% | {'agree': 1} |
