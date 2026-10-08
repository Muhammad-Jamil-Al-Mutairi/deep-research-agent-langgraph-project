# HERMES evaluation missions (live LLM runs)

| id | final_status | expected | met_expectation | design_iterations | verification_trail | loop_events | graph_steps | agent_runs | tokens | cost_usd | model | run_on |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| delivery-robot | VERIFIED | ['VERIFIED'] | True | 2 | FAIL -> PASS | 0 | 18 | 12 | 214712 | 0.014296 | deepseek/deepseek-v4-flash | 2026-10-08 |
| indoor-cart | VERIFIED | ['VERIFIED'] | True | 2 | FAIL -> PASS | 0 | 19 | 13 | 210458 | 0.038933 | deepseek/deepseek-v4-flash | 2026-10-08 |
| infeasible | STAGNATED | ['BUDGET_EXHAUSTED', 'STAGNATED'] | True | 5 | FAIL -> FAIL -> FAIL -> FAIL -> FAIL | 4 | 34 | 19 | 282186 | 0.020065 | deepseek/deepseek-v4-flash | 2026-10-08 |

Total cost of the runs above: $0.0733 USD.
