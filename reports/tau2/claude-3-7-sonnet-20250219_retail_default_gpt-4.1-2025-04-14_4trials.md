# GDOpt profile: claude-3-7-sonnet-20250219_retail_default_gpt-4.1-2025-04-14_4trials (agent claude-3-7-sonnet-20250219, user gpt-4.1-2025-04-14)

- trajectories: 228 train / 228 test; test steps: 3376; action options: 16
- agent cost on test trajectories: $76.49 (LLM ≈ $3.25/M prompt tokens; Jev/LLM price ratio 0.013)
- steps that are tool calls with all arguments already in context: 16.1%
- upper bound on cost saved if every such step skipped the LLM: 17.2%

## Actions on test steps

| action | steps | share |
| --- | ---: | ---: |
| message | 1579 | 46.8% |
| tool:get_order_details | 657 | 19.5% |
| tool:get_product_details | 258 | 7.6% |
| tool:get_user_details | 223 | 6.6% |
| tool:find_user_id_by_name_zip | 191 | 5.7% |
| tool:return_delivered_order_items | 92 | 2.7% |
| tool:modify_pending_order_items | 84 | 2.5% |
| tool:exchange_delivered_order_items | 76 | 2.3% |
| tool:find_user_id_by_email | 62 | 1.8% |
| tool:cancel_pending_order | 58 | 1.7% |
| tool:modify_pending_order_address | 45 | 1.3% |
| tool:modify_user_address | 19 | 0.6% |
| tool:list_all_product_types | 16 | 0.5% |
| tool:transfer_to_human_agents | 9 | 0.3% |
| tool:calculate | 5 | 0.1% |
| tool:modify_pending_order_payment | 2 | 0.1% |

## Candidate tiers (stage 2, before any decision-model call)

| tier | situations | test steps | share of steps |
| --- | ---: | ---: | ---: |
| code | 0 | 0 | 0.0% |
| jev | 30 | 3376 | 100.0% |
| llm | 0 | 0 | 0.0% |

## Situations (sorted by potential saving)

| # | rule | n test | majority action | maj. acc | norm. entropy | closed tool | latest-rule acc | cost share | max saving | candidate |
| ---: | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 39 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=1 & called:list_all_product_types=0 & called:exchange_delivered_order_items=0 & called:modify_pending_order_address=0` | 421 | message | 0.63 | 0.45 | 27.8% | 9.4% | 17.1% | 4.4% | jev |
| 28 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=0 & called:return_delivered_order_items=0 & prev_role=tool & called:cancel_pending_order=0` | 635 | tool:get_order_details | 0.56 | 0.39 | 16.9% | 33.6% | 18.6% | 3.3% | jev |
| 40 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=1 & called:list_all_product_types=0 & called:exchange_delivered_order_items=0 & called:modify_pending_order_address=1` | 94 | message | 0.64 | 0.44 | 26.6% | 24.0% | 4.3% | 1.1% | jev |
| 6 | `n_tool_calls=0 & have:zip=0 & have:email=1` | 46 | tool:find_user_id_by_email | 1.00 | 0.00 | 95.7% | 100.0% | 1.0% | 1.0% | jev |
| 31 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=0 & called:return_delivered_order_items=0 & prev_role=user & called:find_user_id_by_email=0` | 104 | message | 0.53 | 0.52 | 27.9% | 34.5% | 3.4% | 0.9% | jev |
| 48 | `n_tool_calls=3+ & user_confirms=1 & called:get_product_details=0 & user_short=0 & called:find_user_id_by_email=0` | 76 | message | 0.34 | 0.68 | 26.3% | 45.0% | 2.6% | 0.6% | jev |
| 8 | `n_tool_calls=0 & have:zip=1 & user_short=1` | 87 | tool:find_user_id_by_name_zip | 1.00 | 0.00 | 31.0% | 0.0% | 2.0% | 0.6% | jev |
| 53 | `n_tool_calls=3+ & user_confirms=1 & called:get_product_details=1 & called:find_user_id_by_email=0 & user_short=0` | 147 | message | 0.41 | 0.57 | 10.2% | 20.0% | 6.1% | 0.6% | jev |
| 11 | `n_tool_calls=0 & have:zip=1 & user_short=0 & user_confirms=0` | 49 | tool:find_user_id_by_name_zip | 0.98 | 0.04 | 49.0% | 0.0% | 1.1% | 0.6% | jev |
| 10 | `n_tool_calls=0 & have:zip=1 & user_short=0 & user_confirms=1` | 41 | tool:find_user_id_by_name_zip | 0.95 | 0.07 | 51.2% | 0.0% | 1.0% | 0.5% | jev |
| 21 | `n_tool_calls=2 & called:get_user_details=0 & called:get_order_details=1` | 33 | tool:get_product_details | 0.36 | 0.47 | 54.5% | 55.6% | 0.9% | 0.5% | jev |
| 49 | `n_tool_calls=3+ & user_confirms=1 & called:get_product_details=0 & user_short=0 & called:find_user_id_by_email=1` | 38 | tool:return_delivered_order_items | 0.39 | 0.59 | 36.8% | 0.0% | 1.3% | 0.5% | jev |
| 44 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=1 & called:list_all_product_types=1` | 88 | message | 0.48 | 0.42 | 8.0% | 57.1% | 3.4% | 0.3% | jev |
| 50 | `n_tool_calls=3+ & user_confirms=1 & called:get_product_details=0 & user_short=1` | 38 | tool:return_delivered_order_items | 0.45 | 0.57 | 21.1% | 25.0% | 1.4% | 0.3% | jev |
| 32 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=0 & called:return_delivered_order_items=0 & prev_role=user & called:find_user_id_by_email=1` | 36 | message | 0.58 | 0.44 | 22.2% | 12.5% | 1.2% | 0.3% | jev |
| 29 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=0 & called:return_delivered_order_items=0 & prev_role=tool & called:cancel_pending_order=1` | 46 | message | 0.74 | 0.32 | 13.0% | 0.0% | 1.7% | 0.2% | jev |
| 22 | `n_tool_calls=2 & called:get_user_details=0 & called:get_order_details=0` | 27 | tool:get_user_details | 0.41 | 0.51 | 33.3% | 100.0% | 0.6% | 0.2% | jev |
| 34 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=0 & called:return_delivered_order_items=1 & called:find_user_id_by_email=1` | 50 | message | 0.62 | 0.41 | 8.0% | 25.0% | 1.9% | 0.2% | jev |
| 13 | `n_tool_calls=1 & prev_tool=find_user_id_by_name_zip` | 174 | tool:get_user_details | 0.82 | 0.23 | 4.6% | 100.0% | 4.1% | 0.2% | jev |
| 55 | `n_tool_calls=3+ & user_confirms=1 & called:get_product_details=1 & called:find_user_id_by_email=1` | 44 | tool:modify_pending_order_items | 0.39 | 0.60 | 9.1% | 0.0% | 1.8% | 0.2% | jev |
| 19 | `n_tool_calls=2 & called:get_user_details=1 & prev_role=user` | 33 | tool:get_order_details | 0.76 | 0.26 | 18.2% | 66.7% | 0.8% | 0.1% | jev |
| 18 | `n_tool_calls=2 & called:get_user_details=1 & prev_role=tool` | 184 | tool:get_order_details | 0.81 | 0.21 | 3.3% | 100.0% | 4.5% | 0.1% | jev |
| 14 | `n_tool_calls=1 & prev_tool=-` | 23 | tool:find_user_id_by_name_zip | 0.65 | 0.39 | 26.1% | 83.3% | 0.5% | 0.1% | jev |
| 43 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=1 & called:list_all_product_types=0 & called:exchange_delivered_order_items=1 & prev_role=user` | 27 | message | 0.81 | 0.24 | 11.1% | 0.0% | 1.1% | 0.1% | jev |
| 42 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=1 & called:list_all_product_types=0 & called:exchange_delivered_order_items=1 & prev_role=tool` | 95 | message | 0.79 | 0.28 | 3.2% | 100.0% | 4.3% | 0.1% | jev |
| 35 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=0 & called:return_delivered_order_items=1 & called:find_user_id_by_email=0` | 56 | message | 0.80 | 0.27 | 3.6% | 0.0% | 2.2% | 0.1% | jev |
| 54 | `n_tool_calls=3+ & user_confirms=1 & called:get_product_details=1 & called:find_user_id_by_email=0 & user_short=1` | 46 | tool:exchange_delivered_order_items | 0.48 | 0.47 | 2.2% | 100.0% | 1.9% | 0.1% | jev |
| 15 | `n_tool_calls=1 & prev_tool=find_user_id_by_email` | 54 | tool:get_user_details | 0.72 | 0.28 | 3.7% | 0.0% | 1.2% | 0.0% | jev |
| 4 | `n_tool_calls=0 & have:zip=0 & have:email=0 & user_short=0` | 554 | message | 1.00 | 0.00 | 0.0% | 0.0% | 7.1% | 0.0% | jev |
| 5 | `n_tool_calls=0 & have:zip=0 & have:email=0 & user_short=1` | 30 | message | 0.73 | 0.21 | 0.0% | 0.0% | 0.6% | 0.0% | jev |
