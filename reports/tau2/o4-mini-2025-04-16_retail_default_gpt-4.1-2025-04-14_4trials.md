# GDOpt profile: o4-mini-2025-04-16_retail_default_gpt-4.1-2025-04-14_4trials (agent o4-mini-2025-04-16, user gpt-4.1-2025-04-14)

- trajectories: 228 train / 228 test; test steps: 3187; action options: 16
- agent cost on test trajectories: $12.85 (LLM ≈ $0.86/M prompt tokens; Jev/LLM price ratio 0.049)
- steps that are tool calls with all arguments already in context: 14.9%
- upper bound on cost saved if every such step skipped the LLM: 15.6%

## Actions on test steps

| action | steps | share |
| --- | ---: | ---: |
| message | 1627 | 51.1% |
| tool:get_order_details | 551 | 17.3% |
| tool:get_user_details | 201 | 6.3% |
| tool:get_product_details | 200 | 6.3% |
| tool:find_user_id_by_name_zip | 187 | 5.9% |
| tool:return_delivered_order_items | 83 | 2.6% |
| tool:modify_pending_order_items | 75 | 2.4% |
| tool:exchange_delivered_order_items | 71 | 2.2% |
| tool:find_user_id_by_email | 62 | 1.9% |
| tool:cancel_pending_order | 42 | 1.3% |
| tool:modify_pending_order_address | 33 | 1.0% |
| tool:transfer_to_human_agents | 26 | 0.8% |
| tool:modify_user_address | 15 | 0.5% |
| tool:list_all_product_types | 12 | 0.4% |
| tool:modify_pending_order_payment | 2 | 0.1% |

## Candidate tiers (stage 2, before any decision-model call)

| tier | situations | test steps | share of steps |
| --- | ---: | ---: | ---: |
| code | 0 | 0 | 0.0% |
| jev | 31 | 3187 | 100.0% |
| llm | 0 | 0 | 0.0% |

## Situations (sorted by potential saving)

| # | rule | n test | majority action | maj. acc | norm. entropy | closed tool | latest-rule acc | cost share | max saving | candidate |
| ---: | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 32 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=0 & called:return_delivered_order_items=0 & called:get_user_details=1 & called:modify_pending_order_address=0` | 680 | message | 0.42 | 0.46 | 17.8% | 43.0% | 24.7% | 4.7% | jev |
| 41 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=1 & called:list_all_product_types=0 & called:exchange_delivered_order_items=0 & called:modify_pending_order_address=0` | 330 | message | 0.71 | 0.38 | 19.4% | 4.7% | 18.8% | 3.3% | jev |
| 51 | `n_tool_calls=3+ & user_confirms=1 & called:get_product_details=0 & user_short=0 & called:find_user_id_by_email=0` | 70 | tool:return_delivered_order_items | 0.26 | 0.71 | 30.0% | 76.2% | 2.7% | 0.7% | jev |
| 6 | `n_tool_calls=0 & have:zip=0 & have:email=1` | 46 | tool:find_user_id_by_email | 1.00 | 0.00 | 95.7% | 100.0% | 0.8% | 0.7% | jev |
| 9 | `n_tool_calls=0 & have:zip=1 & user_short=0` | 92 | tool:find_user_id_by_name_zip | 0.96 | 0.07 | 44.6% | 0.0% | 1.7% | 0.7% | jev |
| 55 | `n_tool_calls=3+ & user_confirms=1 & called:get_product_details=1 & called:find_user_id_by_email=0 & user_short=0` | 101 | tool:exchange_delivered_order_items | 0.36 | 0.61 | 11.9% | 33.3% | 5.5% | 0.7% | jev |
| 50 | `n_tool_calls=3+ & user_confirms=1 & called:get_product_details=0 & user_short=0 & called:find_user_id_by_email=1` | 30 | tool:return_delivered_order_items | 0.30 | 0.62 | 46.7% | 50.0% | 1.4% | 0.5% | jev |
| 21 | `n_tool_calls=2 & called:get_user_details=1 & prev_role=user` | 105 | tool:get_order_details | 0.87 | 0.16 | 23.8% | 92.0% | 2.5% | 0.5% | jev |
| 8 | `n_tool_calls=0 & have:zip=1 & user_short=1` | 80 | tool:find_user_id_by_name_zip | 1.00 | 0.00 | 36.2% | 0.0% | 1.4% | 0.5% | jev |
| 42 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=1 & called:list_all_product_types=0 & called:exchange_delivered_order_items=0 & called:modify_pending_order_address=1` | 58 | message | 0.55 | 0.48 | 12.1% | 42.9% | 3.1% | 0.4% | jev |
| 24 | `n_tool_calls=2 & called:get_user_details=0 & have:order_id=1 & have:address1=1` | 25 | tool:get_product_details | 0.56 | 0.43 | 64.0% | 25.0% | 0.6% | 0.4% | jev |
| 57 | `n_tool_calls=3+ & user_confirms=1 & called:get_product_details=1 & called:find_user_id_by_email=1` | 33 | tool:modify_pending_order_items | 0.33 | 0.66 | 18.2% | 50.0% | 1.7% | 0.3% | jev |
| 37 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=0 & called:return_delivered_order_items=1 & called:find_user_id_by_email=1` | 49 | message | 0.61 | 0.38 | 10.2% | 80.0% | 2.1% | 0.3% | jev |
| 26 | `n_tool_calls=2 & called:get_user_details=0 & have:order_id=0` | 43 | tool:get_user_details | 0.30 | 0.55 | 30.2% | 100.0% | 0.9% | 0.3% | jev |
| 12 | `n_tool_calls=1 & prev_tool=find_user_id_by_name_zip` | 174 | tool:get_user_details | 0.49 | 0.40 | 6.9% | 100.0% | 2.7% | 0.2% | jev |
| 33 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=0 & called:return_delivered_order_items=0 & called:get_user_details=1 & called:modify_pending_order_address=1` | 19 | message | 0.68 | 0.30 | 31.6% | 16.7% | 0.7% | 0.2% | jev |
| 52 | `n_tool_calls=3+ & user_confirms=1 & called:get_product_details=0 & user_short=1` | 33 | tool:return_delivered_order_items | 0.39 | 0.62 | 21.2% | 57.1% | 1.2% | 0.2% | jev |
| 45 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=1 & called:list_all_product_types=1 & have:payment_method_id=0` | 34 | message | 0.29 | 0.47 | 11.8% | 100.0% | 1.4% | 0.2% | jev |
| 15 | `n_tool_calls=1 & prev_tool=- & user_confirms=0 & called:find_user_id_by_email=0` | 56 | tool:get_user_details | 0.71 | 0.34 | 12.5% | 100.0% | 1.1% | 0.2% | jev |
| 25 | `n_tool_calls=2 & called:get_user_details=0 & have:order_id=1 & have:address1=0` | 24 | tool:get_order_details | 0.33 | 0.43 | 20.8% | 100.0% | 0.5% | 0.1% | jev |
| 46 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=1 & called:list_all_product_types=1 & have:payment_method_id=1` | 65 | message | 0.51 | 0.36 | 3.1% | 50.0% | 3.6% | 0.1% | jev |
| 34 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=0 & called:return_delivered_order_items=0 & called:get_user_details=0` | 25 | message | 0.48 | 0.43 | 12.0% | 66.7% | 0.6% | 0.1% | jev |
| 17 | `n_tool_calls=1 & prev_tool=- & user_confirms=1` | 13 | tool:get_order_details | 0.46 | 0.50 | 30.8% | 100.0% | 0.3% | 0.1% | jev |
| 56 | `n_tool_calls=3+ & user_confirms=1 & called:get_product_details=1 & called:find_user_id_by_email=0 & user_short=1` | 33 | tool:modify_pending_order_items | 0.48 | 0.49 | 3.0% | 0.0% | 1.5% | 0.1% | jev |
| 36 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=0 & called:return_delivered_order_items=1 & called:find_user_id_by_email=0` | 47 | message | 0.85 | 0.17 | 2.1% | 0.0% | 1.8% | 0.1% | jev |
| 16 | `n_tool_calls=1 & prev_tool=- & user_confirms=0 & called:find_user_id_by_email=1` | 28 | tool:get_user_details | 0.39 | 0.49 | 7.1% | 50.0% | 0.6% | 0.0% | jev |
| 11 | `n_tool_calls=1 & prev_tool=find_user_id_by_email` | 54 | message | 0.48 | 0.39 | 3.7% | 0.0% | 0.8% | 0.0% | jev |
| 20 | `n_tool_calls=2 & called:get_user_details=1 & prev_role=tool` | 161 | message | 0.58 | 0.25 | 0.6% | 100.0% | 3.9% | 0.0% | jev |
| 4 | `n_tool_calls=0 & have:zip=0 & have:email=0 & user_short=0` | 542 | message | 0.98 | 0.04 | 0.2% | 100.0% | 5.6% | 0.0% | jev |
| 5 | `n_tool_calls=0 & have:zip=0 & have:email=0 & user_short=1` | 28 | message | 0.86 | 0.15 | 0.0% | 0.0% | 0.4% | 0.0% | jev |
| 43 | `n_tool_calls=3+ & user_confirms=0 & called:get_product_details=1 & called:list_all_product_types=0 & called:exchange_delivered_order_items=1` | 109 | message | 0.84 | 0.24 | 0.0% | 0.0% | 5.4% | 0.0% | jev |
