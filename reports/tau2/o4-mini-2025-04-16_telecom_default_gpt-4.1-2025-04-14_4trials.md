# GDOpt profile: o4-mini-2025-04-16_telecom_default_gpt-4.1-2025-04-14_4trials (agent o4-mini-2025-04-16, user gpt-4.1-2025-04-14)

- trajectories: 228 train / 228 test; test steps: 4264; action options: 14
- agent cost on test trajectories: $21.14 (LLM ≈ $0.67/M prompt tokens; Jev/LLM price ratio 0.063)
- steps that are tool calls with all arguments already in context: 29.9%
- upper bound on cost saved if every such step skipped the LLM: 28.1%

## Actions on test steps

| action | steps | share |
| --- | ---: | ---: |
| message | 2230 | 52.3% |
| tool:get_details_by_id | 938 | 22.0% |
| tool:get_customer_by_phone | 395 | 9.3% |
| tool:send_payment_request | 177 | 4.2% |
| tool:transfer_to_human_agents | 171 | 4.0% |
| tool:get_data_usage | 71 | 1.7% |
| tool:enable_roaming | 58 | 1.4% |
| tool:refuel_data | 54 | 1.3% |
| tool:resume_line | 45 | 1.1% |
| tool:disable_roaming | 40 | 0.9% |
| tool:get_bills_for_customer | 39 | 0.9% |
| tool:get_customer_by_id | 37 | 0.9% |
| tool:get_customer_by_name | 5 | 0.1% |
| tool:suspend_line | 4 | 0.1% |

## Candidate tiers (stage 2, before any decision-model call)

| tier | situations | test steps | share of steps |
| --- | ---: | ---: | ---: |
| code | 1 | 223 | 5.2% |
| jev | 22 | 4041 | 94.8% |
| llm | 0 | 0 | 0.0% |

## Situations (sorted by potential saving)

| # | rule | n test | majority action | maj. acc | norm. entropy | closed tool | latest-rule acc | cost share | max saving | candidate |
| ---: | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 21 | `n_tool_calls=3+ & called:transfer_to_human_agents=0 & have:limit=0 & called:get_details_by_id=1 & prev_role=tool & called:send_payment_request=0` | 578 | message | 0.43 | 0.64 | 43.3% | 95.2% | 14.5% | 5.4% | jev |
| 24 | `n_tool_calls=3+ & called:transfer_to_human_agents=0 & have:limit=0 & called:get_details_by_id=1 & prev_role=user & called:enable_roaming=0` | 609 | message | 0.56 | 0.57 | 27.6% | 91.7% | 16.9% | 4.0% | jev |
| 32 | `n_tool_calls=3+ & called:transfer_to_human_agents=0 & have:limit=1 & have:gb_amount=0 & user_confirms=0 & called:get_bills_for_customer=0` | 437 | message | 0.54 | 0.59 | 33.9% | 91.2% | 11.8% | 3.5% | jev |
| 22 | `n_tool_calls=3+ & called:transfer_to_human_agents=0 & have:limit=0 & called:get_details_by_id=1 & prev_role=tool & called:send_payment_request=1` | 329 | message | 0.55 | 0.54 | 41.0% | 87.4% | 9.4% | 3.3% | jev |
| 3 | `n_tool_calls=0 & have:phone_number=1` | 223 | tool:get_customer_by_phone | 0.99 | 0.02 | 98.7% | 100.0% | 3.5% | 3.2% | code |
| 33 | `n_tool_calls=3+ & called:transfer_to_human_agents=0 & have:limit=1 & have:gb_amount=0 & user_confirms=0 & called:get_bills_for_customer=1` | 248 | message | 0.45 | 0.62 | 46.0% | 86.0% | 7.2% | 2.9% | jev |
| 39 | `n_tool_calls=3+ & called:transfer_to_human_agents=0 & have:limit=1 & have:gb_amount=1 & called:disable_roaming=0 & called:enable_roaming=0` | 231 | message | 0.59 | 0.52 | 30.3% | 82.9% | 6.7% | 1.7% | jev |
| 25 | `n_tool_calls=3+ & called:transfer_to_human_agents=0 & have:limit=0 & called:get_details_by_id=1 & prev_role=user & called:enable_roaming=1` | 158 | message | 0.58 | 0.57 | 27.2% | 97.7% | 4.5% | 1.1% | jev |
| 35 | `n_tool_calls=3+ & called:transfer_to_human_agents=0 & have:limit=1 & have:gb_amount=0 & user_confirms=1 & have:bill_id=0` | 40 | tool:refuel_data | 0.47 | 0.45 | 60.0% | 87.5% | 1.0% | 0.5% | jev |
| 27 | `n_tool_calls=3+ & called:transfer_to_human_agents=0 & have:limit=0 & called:get_details_by_id=0 & have:line_id=1` | 51 | message | 0.45 | 0.66 | 41.2% | 95.2% | 1.3% | 0.5% | jev |
| 40 | `n_tool_calls=3+ & called:transfer_to_human_agents=0 & have:limit=1 & have:gb_amount=1 & called:disable_roaming=0 & called:enable_roaming=1` | 47 | message | 0.66 | 0.43 | 29.8% | 71.4% | 1.6% | 0.5% | jev |
| 36 | `n_tool_calls=3+ & called:transfer_to_human_agents=0 & have:limit=1 & have:gb_amount=0 & user_confirms=1 & have:bill_id=1` | 19 | message | 0.21 | 0.52 | 78.9% | 86.7% | 0.5% | 0.4% | jev |
| 41 | `n_tool_calls=3+ & called:transfer_to_human_agents=0 & have:limit=1 & have:gb_amount=1 & called:disable_roaming=1` | 29 | message | 0.48 | 0.62 | 34.5% | 100.0% | 0.9% | 0.3% | jev |
| 6 | `n_tool_calls=1 & prev_role=user` | 73 | message | 0.52 | 0.59 | 16.4% | 100.0% | 1.8% | 0.2% | jev |
| 28 | `n_tool_calls=3+ & called:transfer_to_human_agents=0 & have:limit=0 & called:get_details_by_id=0 & have:line_id=0` | 20 | message | 0.45 | 0.44 | 35.0% | 100.0% | 0.5% | 0.1% | jev |
| 13 | `n_tool_calls=2 & prev_role=user & have:line_id=1 & have:limit=0` | 29 | message | 0.72 | 0.40 | 20.7% | 83.3% | 0.6% | 0.1% | jev |
| 14 | `n_tool_calls=2 & prev_role=user & have:line_id=1 & have:limit=1` | 5 | message | 0.40 | 0.40 | 40.0% | 100.0% | 0.2% | 0.1% | jev |
| 9 | `n_tool_calls=2 & prev_role=tool & called:get_details_by_id=1` | 186 | tool:get_details_by_id | 0.95 | 0.09 | 2.2% | 50.0% | 3.5% | 0.1% | jev |
| 10 | `n_tool_calls=2 & prev_role=tool & called:get_details_by_id=0` | 41 | message | 0.68 | 0.43 | 9.8% | 100.0% | 0.8% | 0.1% | jev |
| 5 | `n_tool_calls=1 & prev_role=tool` | 228 | tool:get_details_by_id | 0.80 | 0.26 | 1.8% | 100.0% | 4.3% | 0.1% | jev |
| 42 | `n_tool_calls=3+ & called:transfer_to_human_agents=1` | 172 | message | 0.98 | 0.04 | 1.2% | 100.0% | 3.8% | 0.0% | jev |
| 15 | `n_tool_calls=2 & prev_role=user & have:line_id=0` | 50 | message | 0.66 | 0.48 | 4.0% | 100.0% | 1.2% | 0.0% | jev |
| 2 | `n_tool_calls=0 & have:phone_number=0` | 461 | message | 0.99 | 0.03 | 0.0% | 0.0% | 3.4% | 0.0% | jev |
