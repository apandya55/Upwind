# Supplementary observability control results

Post-primary UW-ENGINE-2026-06-O: 16 paired seeds, two conditions, two engines; **64 attempts**. Unchanged frozen scientific source. This deliberately more observable geometry does not replace the primary comparison or its failed 50m targets. All inputs are synthetic.

| Condition | Model | Fits | Accepted | Accepted wrong | Region coverage | Median mean error m | Mean region/domain |
|---|---|---:|---:|---:|---:|---:|---:|
| near_nominal | plume-weather-0.5.0 | 16/16 | 11/16 | 0/11 | 16/16 | 28.7 | 13.9% |
| near_nominal | plume-robust-0.6.0 | 16/16 | 7/16 | 0/7 | 16/16 | 35.9 | 19.9% |
| near_shared_bias | plume-weather-0.5.0 | 16/16 | 3/16 | 3/3 | 6/16 | 233.9 | 37.6% |
| near_shared_bias | plume-robust-0.6.0 | 16/16 | 5/16 | 1/5 | 13/16 | 98.8 | 35.3% |

Wrong includes accepted region misses or false source alarms. See [raw summary](../evaluations/engine-v06/observability-summary.json) for all distributions and Wilson intervals, and [protocol](ENGINE_V06_OBSERVABILITY_CONTROL.md) for geometry and weather biases. Common-bias failures remain; do not claim general reliability from nominal performance. No parameter or acceptance-rule tuning followed this control.
