# GDOpt profile: gpt-4.1-2025-04-14_retail_default_gpt-4.1-2025-04-14_4trials (agent gpt-4.1-2025-04-14, user gpt-4.1-2025-04-14)

- trajectories: 228 train / 228 test; test steps: 2787; action options: 16
- agent cost on test trajectories: $13.27 (LLM ≈ $1.01/M prompt tokens; Jev/LLM price ratio 0.042)
- steps that are tool calls with all arguments already in context: 13.1%
- upper bound on cost saved if every such step skipped the LLM: 11.8%

## Actions on test steps

| action | steps | share |
| --- | ---: | ---: |
| message | 1541 | 55.3% |
| tool:get_order_details | 288 | 10.3% |
| tool:get_user_details | 230 | 8.3% |
| tool:find_user_id_by_name_zip | 185 | 6.6% |
| tool:get_product_details | 160 | 5.7% |
| tool:modify_pending_order_items | 77 | 2.8% |
| tool:return_delivered_order_items | 67 | 2.4% |
| tool:find_user_id_by_email | 60 | 2.2% |
| tool:exchange_delivered_order_items | 60 | 2.2% |
| tool:cancel_pending_order | 34 | 1.2% |
| tool:calculate | 25 | 0.9% |
| tool:modify_pending_order_address | 20 | 0.7% |
| tool:modify_user_address | 17 | 0.6% |
| tool:list_all_product_types | 13 | 0.5% |
| tool:transfer_to_human_agents | 8 | 0.3% |
| tool:modify_pending_order_payment | 2 | 0.1% |

## Candidate tiers (stage 2, before any decision-model call)

| tier | situations | test steps | share of steps |
| --- | ---: | ---: | ---: |
| code | 0 | 0 | 0.0% |
| jev | 25 | 2684 | 96.3% |
| llm | 1 | 103 | 3.7% |

## Situations (sorted by potential saving)

| # | rule | n test | majority action | maj. acc | norm. entropy | closed tool | latest-rule acc | cost share | max saving | candidate |
| ---: | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 22 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=0 & prev_role=tool & called:return_delivered_order_items=0 & called:get_order_details=1` | 345 | message | 0.63 | 0.37 | 22.9% | 31.6% | 14.5% | 2.8% | jev |
| 27 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=0 & prev_role=user & user_short=0 & called:find_user_id_by_name_zip=1` | 125 | message | 0.52 | 0.50 | 32.0% | 27.5% | 5.4% | 1.7% | jev |
| 44 | `n_tool_calls=3+ & user_confirms=1 & called:get_product_details=0 & called:find_user_id_by_name_zip=1` | 103 | tool:return_delivered_order_items | 0.24 | 0.75 | 31.1% | 15.6% | 4.5% | 1.4% | llm |
| 33 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=1 & prev_role=tool & called:return_delivered_order_items=0 & called:exchange_delivered_order_items=0` | 268 | message | 0.84 | 0.27 | 8.6% | 30.4% | 17.9% | 1.2% | jev |
| 7 | `n_tool_calls=0 & have:zip=1 & user_confirms=0` | 78 | tool:find_user_id_by_name_zip | 0.96 | 0.07 | 50.0% | 0.0% | 1.5% | 0.7% | jev |
| 4 | `n_tool_calls=0 & have:zip=0 & have:email=1` | 45 | tool:find_user_id_by_email | 1.00 | 0.00 | 97.8% | 100.0% | 0.8% | 0.7% | jev |
| 6 | `n_tool_calls=0 & have:zip=1 & user_confirms=1` | 97 | tool:find_user_id_by_name_zip | 1.00 | 0.00 | 33.0% | 0.0% | 1.8% | 0.6% | jev |
| 43 | `n_tool_calls=3+ & user_confirms=1 & called:get_product_details=0 & called:find_user_id_by_name_zip=0` | 30 | tool:return_delivered_order_items | 0.40 | 0.60 | 33.3% | 20.0% | 1.5% | 0.5% | jev |
| 46 | `n_tool_calls=3+ & user_confirms=1 & called:get_product_details=1 & called:find_user_id_by_email=0` | 149 | tool:exchange_delivered_order_items | 0.28 | 0.57 | 5.4% | 62.5% | 9.2% | 0.4% | jev |
| 28 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=0 & prev_role=user & user_short=0 & called:find_user_id_by_name_zip=0` | 30 | message | 0.47 | 0.55 | 30.0% | 11.1% | 1.3% | 0.4% | jev |
| 14 | `n_tool_calls=2 & called:get_user_details=1 & prev_role=tool` | 206 | tool:get_order_details | 0.55 | 0.29 | 4.9% | 100.0% | 4.9% | 0.2% | jev |
| 35 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=1 & prev_role=tool & called:return_delivered_order_items=1` | 38 | message | 0.89 | 0.16 | 7.9% | 0.0% | 2.8% | 0.2% | jev |
| 11 | `n_tool_calls=1 & prev_tool=-` | 29 | tool:get_user_details | 0.31 | 0.51 | 37.9% | 90.9% | 0.5% | 0.2% | jev |
| 15 | `n_tool_calls=2 & called:get_user_details=1 & prev_role=user` | 88 | tool:get_order_details | 0.91 | 0.13 | 8.0% | 85.7% | 2.3% | 0.2% | jev |
| 38 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=1 & prev_role=user & called:exchange_delivered_order_items=0 & called:modify_pending_order_items=0` | 73 | message | 0.78 | 0.33 | 2.7% | 50.0% | 4.5% | 0.1% | jev |
| 16 | `n_tool_calls=2 & called:get_user_details=0` | 33 | tool:get_user_details | 0.42 | 0.44 | 12.1% | 75.0% | 0.8% | 0.1% | jev |
| 23 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=0 & prev_role=tool & called:return_delivered_order_items=0 & called:get_order_details=0` | 23 | tool:get_order_details | 0.57 | 0.41 | 13.0% | 100.0% | 0.6% | 0.1% | jev |
| 47 | `n_tool_calls=3+ & user_confirms=1 & called:get_product_details=1 & called:find_user_id_by_email=1` | 48 | tool:modify_pending_order_items | 0.40 | 0.59 | 4.2% | 50.0% | 3.1% | 0.1% | jev |
| 10 | `n_tool_calls=1 & prev_tool=find_user_id_by_name_zip` | 174 | tool:get_user_details | 0.91 | 0.11 | 1.7% | 100.0% | 3.3% | 0.1% | jev |
| 34 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=1 & prev_role=tool & called:return_delivered_order_items=0 & called:exchange_delivered_order_items=1` | 62 | message | 0.95 | 0.08 | 1.6% | 100.0% | 4.2% | 0.0% | jev |
| 24 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=0 & prev_role=tool & called:return_delivered_order_items=1` | 56 | message | 0.84 | 0.21 | 1.8% | 0.0% | 3.2% | 0.0% | jev |
| 29 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=0 & prev_role=user & user_short=1` | 27 | message | 0.81 | 0.21 | 3.7% | 0.0% | 1.2% | 0.0% | jev |
| 3 | `n_tool_calls=0 & have:zip=0 & have:email=0` | 549 | message | 0.98 | 0.04 | 0.2% | 100.0% | 5.7% | 0.0% | jev |
| 9 | `n_tool_calls=1 & prev_tool=find_user_id_by_email` | 54 | tool:get_user_details | 0.70 | 0.22 | 0.0% | 0.0% | 1.0% | 0.0% | jev |
| 39 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=1 & prev_role=user & called:exchange_delivered_order_items=0 & called:modify_pending_order_items=1` | 21 | message | 0.81 | 0.18 | 0.0% | 0.0% | 1.3% | 0.0% | jev |
| 40 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=1 & prev_role=user & called:exchange_delivered_order_items=1` | 36 | message | 0.94 | 0.09 | 0.0% | 0.0% | 2.4% | 0.0% | jev |
