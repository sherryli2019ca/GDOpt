# GDOpt profile: claude-3-7-sonnet-20250219_telecom_default_gpt-4.1-2025-04-14_4trials (agent claude-3-7-sonnet-20250219, user gpt-4.1-2025-04-14)

- trajectories: 228 train / 228 test; test steps: 4237; action options: 19
- agent cost on test trajectories: $130.92 (LLM ≈ $3.22/M prompt tokens; Jev/LLM price ratio 0.013)
- steps that are tool calls with all arguments already in context: 20.0%
- upper bound on cost saved if every such step skipped the LLM: 19.4%

## Actions on test steps

| action | steps | share |
| --- | ---: | ---: |
| message | 2719 | 64.2% |
| tool:get_details_by_id | 709 | 16.7% |
| tool:get_customer_by_phone | 229 | 5.4% |
| tool:transfer_to_human_agents | 129 | 3.0% |
| tool:get_data_usage | 110 | 2.6% |
| tool:refuel_data | 92 | 2.2% |
| tool:get_bills_for_customer | 55 | 1.3% |
| tool:send_payment_request | 42 | 1.0% |
| tool:resume_line | 42 | 1.0% |
| tool:enable_roaming | 39 | 0.9% |
| tool:can_send_mms | 28 | 0.7% |
| tool:check_network_status | 22 | 0.5% |
| tool:check_apn_settings | 4 | 0.1% |
| tool:set_network_mode_preference | 4 | 0.1% |
| tool:check_status_bar | 3 | 0.1% |
| tool:reset_apn_settings | 2 | 0.0% |
| tool:toggle_data | 2 | 0.0% |
| tool:reseat_sim_card | 2 | 0.0% |
| tool:reboot_device | 2 | 0.0% |
| tool:run_speed_test | 1 | 0.0% |
| tool:toggle_data_saver_mode | 1 | 0.0% |

## Candidate tiers (stage 2, before any decision-model call)

| tier | situations | test steps | share of steps |
| --- | ---: | ---: | ---: |
| code | 2 | 228 | 5.4% |
| jev | 31 | 4009 | 94.6% |
| llm | 0 | 0 | 0.0% |

## Situations (sorted by potential saving)

| # | rule | n test | majority action | maj. acc | norm. entropy | closed tool | latest-rule acc | cost share | max saving | candidate |
| ---: | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 25 | `n_tool_calls=3+ & called:get_bills_for_customer=0 & prev_role=tool & called:get_data_usage=0 & called:refuel_data=0 & called:check_network_status=0` | 400 | message | 0.36 | 0.48 | 51.7% | 95.7% | 9.2% | 4.6% | jev |
| 5 | `n_tool_calls=0 & have:phone_number=1` | 204 | tool:get_customer_by_phone | 1.00 | 0.00 | 100.0% | 100.0% | 4.0% | 4.0% | code |
| 42 | `n_tool_calls=3+ & called:get_bills_for_customer=0 & prev_role=user & called:refuel_data=0 & user_confirms=0 & called:get_data_usage=0` | 439 | message | 0.83 | 0.25 | 10.0% | 93.2% | 11.5% | 1.1% | jev |
| 58 | `n_tool_calls=3+ & called:get_bills_for_customer=1 & called:resume_line=0 & called:send_payment_request=1 & prev_role=tool` | 83 | tool:get_details_by_id | 0.00 | 0.24 | 49.4% | 75.6% | 2.1% | 1.0% | jev |
| 59 | `n_tool_calls=3+ & called:get_bills_for_customer=1 & called:resume_line=0 & called:send_payment_request=1 & prev_role=user` | 42 | tool:get_details_by_id | 0.98 | 0.04 | 100.0% | 97.6% | 1.1% | 1.0% | jev |
| 56 | `n_tool_calls=3+ & called:get_bills_for_customer=1 & called:resume_line=0 & called:send_payment_request=0 & user_confirms=1` | 42 | tool:send_payment_request | 0.93 | 0.09 | 92.9% | 100.0% | 1.1% | 0.9% | jev |
| 41 | `n_tool_calls=3+ & called:get_bills_for_customer=0 & prev_role=user & called:refuel_data=0 & user_confirms=0 & called:get_data_usage=1` | 232 | message | 0.76 | 0.32 | 12.9% | 60.0% | 6.4% | 0.8% | jev |
| 33 | `n_tool_calls=3+ & called:get_bills_for_customer=0 & prev_role=tool & called:get_data_usage=1 & called:refuel_data=0 & called:enable_roaming=0` | 152 | message | 0.74 | 0.33 | 17.8% | 96.3% | 3.9% | 0.7% | jev |
| 48 | `n_tool_calls=3+ & called:get_bills_for_customer=0 & prev_role=user & called:refuel_data=1 & called:get_data_usage=1 & called:can_send_mms=0` | 255 | message | 0.84 | 0.25 | 9.0% | 65.2% | 7.3% | 0.6% | jev |
| 45 | `n_tool_calls=3+ & called:get_bills_for_customer=0 & prev_role=user & called:refuel_data=1 & called:get_data_usage=0 & user_confirms=0` | 155 | message | 0.71 | 0.35 | 14.8% | 87.0% | 4.5% | 0.6% | jev |
| 39 | `n_tool_calls=3+ & called:get_bills_for_customer=0 & prev_role=user & called:refuel_data=0 & user_confirms=1 & called:get_data_usage=1` | 84 | message | 0.54 | 0.40 | 27.4% | 100.0% | 2.2% | 0.6% | jev |
| 16 | `n_tool_calls=1 & have:customer_id=0 & prev_role=user` | 24 | tool:get_customer_by_phone | 1.00 | 0.00 | 100.0% | 100.0% | 0.5% | 0.5% | code |
| 26 | `n_tool_calls=3+ & called:get_bills_for_customer=0 & prev_role=tool & called:get_data_usage=0 & called:refuel_data=0 & called:check_network_status=1` | 43 | tool:get_details_by_id | 0.58 | 0.33 | 48.8% | 90.5% | 1.0% | 0.5% | jev |
| 4 | `n_tool_calls=0 & have:phone_number=0 & prev_role=user` | 228 | message | 0.89 | 0.15 | 10.1% | 100.0% | 4.5% | 0.5% | jev |
| 38 | `n_tool_calls=3+ & called:get_bills_for_customer=0 & prev_role=user & called:refuel_data=0 & user_confirms=1 & called:get_data_usage=0` | 122 | message | 0.69 | 0.30 | 16.4% | 95.0% | 3.1% | 0.5% | jev |
| 62 | `n_tool_calls=3+ & called:get_bills_for_customer=1 & called:resume_line=1 & prev_role=user` | 214 | message | 0.83 | 0.20 | 5.1% | 45.5% | 6.4% | 0.3% | jev |
| 54 | `n_tool_calls=3+ & called:get_bills_for_customer=1 & called:resume_line=0 & called:send_payment_request=0 & user_confirms=0 & called:get_data_usage=1` | 49 | message | 0.69 | 0.37 | 20.4% | 80.0% | 1.6% | 0.3% | jev |
| 30 | `n_tool_calls=3+ & called:get_bills_for_customer=0 & prev_role=tool & called:get_data_usage=1 & called:refuel_data=1 & called:check_network_status=0` | 91 | message | 0.88 | 0.19 | 5.5% | 100.0% | 2.5% | 0.1% | jev |
| 8 | `n_tool_calls=1 & have:customer_id=1 & prev_role=tool` | 204 | tool:get_details_by_id | 0.63 | 0.25 | 2.5% | 100.0% | 4.3% | 0.1% | jev |
| 27 | `n_tool_calls=3+ & called:get_bills_for_customer=0 & prev_role=tool & called:get_data_usage=0 & called:refuel_data=1` | 87 | message | 0.93 | 0.12 | 4.6% | 75.0% | 2.3% | 0.1% | jev |
| 55 | `n_tool_calls=3+ & called:get_bills_for_customer=1 & called:resume_line=0 & called:send_payment_request=0 & user_confirms=0 & called:get_data_usage=0` | 60 | message | 0.88 | 0.16 | 6.7% | 100.0% | 1.5% | 0.1% | jev |
| 49 | `n_tool_calls=3+ & called:get_bills_for_customer=0 & prev_role=user & called:refuel_data=1 & called:get_data_usage=1 & called:can_send_mms=1` | 38 | message | 0.79 | 0.26 | 10.5% | 100.0% | 1.1% | 0.1% | jev |
| 31 | `n_tool_calls=3+ & called:get_bills_for_customer=0 & prev_role=tool & called:get_data_usage=1 & called:refuel_data=1 & called:check_network_status=1` | 27 | message | 0.85 | 0.19 | 11.1% | 100.0% | 0.7% | 0.1% | jev |
| 19 | `n_tool_calls=2 & called:get_details_by_id=0` | 46 | tool:get_details_by_id | 0.78 | 0.18 | 6.5% | 100.0% | 1.0% | 0.1% | jev |
| 12 | `n_tool_calls=1 & have:customer_id=1 & prev_role=user & user_short=0 & user_confirms=0` | 270 | message | 0.87 | 0.17 | 0.7% | 100.0% | 6.3% | 0.0% | jev |
| 10 | `n_tool_calls=1 & have:customer_id=1 & prev_role=user & user_short=1` | 39 | tool:get_details_by_id | 0.51 | 0.32 | 5.1% | 100.0% | 0.9% | 0.0% | jev |
| 61 | `n_tool_calls=3+ & called:get_bills_for_customer=1 & called:resume_line=1 & prev_role=tool` | 82 | message | 0.95 | 0.08 | 1.2% | 100.0% | 2.3% | 0.0% | jev |
| 46 | `n_tool_calls=3+ & called:get_bills_for_customer=0 & prev_role=user & called:refuel_data=1 & called:get_data_usage=0 & user_confirms=1` | 29 | message | 0.93 | 0.10 | 3.4% | 0.0% | 0.8% | 0.0% | jev |
| 3 | `n_tool_calls=0 & have:phone_number=0 & prev_role=start` | 228 | message | 1.00 | 0.00 | 0.0% | 0.0% | 0.0% | 0.0% | jev |
| 13 | `n_tool_calls=1 & have:customer_id=1 & prev_role=user & user_short=0 & user_confirms=1` | 37 | message | 0.68 | 0.21 | 0.0% | 0.0% | 0.9% | 0.0% | jev |
| 15 | `n_tool_calls=1 & have:customer_id=0 & prev_role=tool` | 24 | message | 1.00 | 0.00 | 0.0% | 0.0% | 0.5% | 0.0% | jev |
| 18 | `n_tool_calls=2 & called:get_details_by_id=1` | 183 | tool:get_details_by_id | 1.00 | 0.00 | 0.0% | 0.0% | 3.9% | 0.0% | jev |
| 34 | `n_tool_calls=3+ & called:get_bills_for_customer=0 & prev_role=tool & called:get_data_usage=1 & called:refuel_data=0 & called:enable_roaming=1` | 24 | message | 0.71 | 0.21 | 0.0% | 0.0% | 0.7% | 0.0% | jev |
