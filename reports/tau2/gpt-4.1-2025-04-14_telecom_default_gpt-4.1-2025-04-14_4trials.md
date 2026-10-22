# GDOpt profile: gpt-4.1-2025-04-14_telecom_default_gpt-4.1-2025-04-14_4trials (agent gpt-4.1-2025-04-14, user gpt-4.1-2025-04-14)

- trajectories: 228 train / 228 test; test steps: 4118; action options: 11
- agent cost on test trajectories: $24.71 (LLM ≈ $0.80/M prompt tokens; Jev/LLM price ratio 0.052)
- steps that are tool calls with all arguments already in context: 24.0%
- upper bound on cost saved if every such step skipped the LLM: 25.5%

## Actions on test steps

| action | steps | share |
| --- | ---: | ---: |
| message | 2574 | 62.5% |
| tool:get_details_by_id | 894 | 21.7% |
| tool:get_customer_by_phone | 228 | 5.5% |
| tool:transfer_to_human_agents | 131 | 3.2% |
| tool:get_data_usage | 69 | 1.7% |
| tool:refuel_data | 66 | 1.6% |
| tool:get_bills_for_customer | 47 | 1.1% |
| tool:send_payment_request | 46 | 1.1% |
| tool:resume_line | 43 | 1.0% |
| tool:enable_roaming | 17 | 0.4% |
| tool:get_customer_by_id | 3 | 0.1% |

## Candidate tiers (stage 2, before any decision-model call)

| tier | situations | test steps | share of steps |
| --- | ---: | ---: | ---: |
| code | 1 | 228 | 5.5% |
| jev | 20 | 3890 | 94.5% |
| llm | 0 | 0 | 0.0% |

## Situations (sorted by potential saving)

| # | rule | n test | majority action | maj. acc | norm. entropy | closed tool | latest-rule acc | cost share | max saving | candidate |
| ---: | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 15 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=0 & called:transfer_to_human_agents=0 & have:gb_amount=0 & called:get_data_usage=0` | 498 | tool:get_details_by_id | 0.57 | 0.50 | 73.3% | 96.7% | 15.6% | 11.6% | jev |
| 3 | `n_tool_calls=0 & have:phone_number=1` | 228 | tool:get_customer_by_phone | 1.00 | 0.00 | 100.0% | 100.0% | 3.4% | 3.2% | code |
| 25 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=1 & called:send_payment_request=1 & called:resume_line=1` | 127 | message | 0.57 | 0.38 | 39.4% | 16.0% | 4.3% | 1.7% | jev |
| 30 | `n_tool_calls=3+ & prev_role=user & called:get_bills_for_customer=0 & called:refuel_data=0 & called:get_data_usage=0 & user_confirms=0` | 462 | message | 0.80 | 0.33 | 12.1% | 87.5% | 12.4% | 1.4% | jev |
| 22 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=1 & called:send_payment_request=0` | 55 | tool:send_payment_request | 0.76 | 0.30 | 89.1% | 85.7% | 1.6% | 1.3% | jev |
| 24 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=1 & called:send_payment_request=1 & called:resume_line=0` | 100 | message | 0.50 | 0.41 | 49.0% | 89.8% | 2.9% | 1.3% | jev |
| 37 | `n_tool_calls=3+ & prev_role=user & called:get_bills_for_customer=1 & called:resume_line=0` | 52 | tool:get_details_by_id | 0.85 | 0.26 | 92.3% | 93.8% | 1.5% | 1.2% | jev |
| 19 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=0 & called:transfer_to_human_agents=0 & have:gb_amount=1 & called:get_data_usage=1` | 96 | message | 0.53 | 0.49 | 33.3% | 46.9% | 2.9% | 1.0% | jev |
| 35 | `n_tool_calls=3+ & prev_role=user & called:get_bills_for_customer=0 & called:refuel_data=1` | 205 | message | 0.75 | 0.35 | 13.2% | 96.3% | 6.1% | 0.7% | jev |
| 18 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=0 & called:transfer_to_human_agents=0 & have:gb_amount=1 & called:get_data_usage=0` | 61 | message | 0.64 | 0.44 | 32.8% | 90.0% | 1.7% | 0.5% | jev |
| 16 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=0 & called:transfer_to_human_agents=0 & have:gb_amount=0 & called:get_data_usage=1` | 76 | message | 0.68 | 0.41 | 23.7% | 77.8% | 2.3% | 0.5% | jev |
| 38 | `n_tool_calls=3+ & prev_role=user & called:get_bills_for_customer=1 & called:resume_line=1` | 157 | message | 0.81 | 0.26 | 7.0% | 72.7% | 5.0% | 0.3% | jev |
| 8 | `n_tool_calls=2 & prev_role=tool` | 217 | tool:get_details_by_id | 0.83 | 0.22 | 6.9% | 80.0% | 4.7% | 0.3% | jev |
| 33 | `n_tool_calls=3+ & prev_role=user & called:get_bills_for_customer=0 & called:refuel_data=0 & called:get_data_usage=1 & user_confirms=0` | 34 | message | 0.41 | 0.42 | 20.6% | 85.7% | 0.9% | 0.2% | jev |
| 34 | `n_tool_calls=3+ & prev_role=user & called:get_bills_for_customer=0 & called:refuel_data=0 & called:get_data_usage=1 & user_confirms=1` | 31 | tool:refuel_data | 0.74 | 0.34 | 19.4% | 16.7% | 0.9% | 0.2% | jev |
| 9 | `n_tool_calls=2 & prev_role=user` | 63 | message | 0.81 | 0.26 | 7.9% | 80.0% | 1.9% | 0.1% | jev |
| 31 | `n_tool_calls=3+ & prev_role=user & called:get_bills_for_customer=0 & called:refuel_data=0 & called:get_data_usage=0 & user_confirms=1` | 64 | message | 0.83 | 0.26 | 1.6% | 100.0% | 1.7% | 0.0% | jev |
| 2 | `n_tool_calls=0 & have:phone_number=0` | 456 | message | 1.00 | 0.00 | 0.0% | 0.0% | 3.6% | 0.0% | jev |
| 5 | `n_tool_calls=1 & prev_role=tool` | 228 | message | 0.68 | 0.26 | 0.0% | 0.0% | 4.1% | 0.0% | jev |
| 6 | `n_tool_calls=1 & prev_role=user` | 824 | message | 0.83 | 0.22 | 0.0% | 0.0% | 20.0% | 0.0% | jev |
| 20 | `n_tool_calls=3+ & prev_role=tool & called:get_bills_for_customer=0 & called:transfer_to_human_agents=1` | 84 | message | 1.00 | 0.00 | 0.0% | 0.0% | 2.5% | 0.0% | jev |
