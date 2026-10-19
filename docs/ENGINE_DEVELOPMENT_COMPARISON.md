# Old-case development comparison

Baseline `plume-ensemble-0.2.1` versus `plume-mixture-0.3.0` on the original 16 × 40 stress inputs. **All cases are development-used. This is not untouched evaluation.** The original generator is loaded from the immutable baseline snapshot, with hidden truth confined to this evaluator. No planner is executed in this comparison; realized planning belongs to the independent challenge experiment.

The baseline output is the exactly reproduced earlier run. New inputs are the original JSON validated into the current schema, receiving its documented new defaults. Source-domain anchors now define a continuous rectangle with unsupported cells explicitly removed. The estimands differ: old MAP selects a declared point; the new primary estimate is the conditional source-cell mean, with MAP-center error also shown. Neither is a probability of responsibility.

| Condition | Old/new fits | Old MAP median / p90 m | New mean median / p90 m | New MAP median m | New region coverage | Median area m² / domain % | Old/new alarms |
|---|---|---|---|---|---|---|---|
| weak_signal | 40/40 | 128.1 / 254.6 | 64.7 / 70.7 | 119.0 | 32/40 | 65000.0 / 89.3 | 0/0 |
| strong_signal | 40/40 | 0.0 / 0.0 | 44.4 / 64.9 | 64.5 | 26/40 | 4828.6 / 7.1 | 0/0 |
| ambiguous | 40/40 | — / — | 64.0 / 64.0 | — | 40/40 | 65742.9 / 90.3 | 0/2 |
| high_noise | 40/40 | 0.0 / 0.0 | 40.8 / 45.0 | 64.5 | 36/40 | 14114.3 / 20.8 | 0/0 |
| background_shift | 40/40 | 0.0 / 0.0 | 44.8 / 65.0 | 64.5 | 26/40 | 4828.6 / 7.1 | 0/0 |
| changing_background | 40/40 | 0.0 / 0.0 | 44.8 / 65.0 | 64.5 | 26/40 | 4828.6 / 7.1 | 40/0 |
| two_sources | 40/40 | 0.0 / 0.0 | 58.2 / 87.4 | 96.1 | 7/40 | 2785.7 / 4.1 | 0/0 |
| off_grid | 40/40 | 80.6 / 176.9 | 70.4 / 75.9 | 101.5 | 35/40 | 56085.7 / 82.5 | 0/0 |
| direction_bias | 40/40 | 128.1 / 254.6 | 69.1 / 74.5 | 170.4 | 36/40 | 57942.9 / 85.2 | 0/0 |
| speed_bias | 40/40 | 0.0 / 0.0 | 45.5 / 50.2 | 73.4 | 28/40 | 13742.9 / 20.2 | 0/0 |
| clustered | 40/40 | 0.0 / 0.0 | 65.0 / 65.6 | 73.4 | 25/40 | 61285.7 / 88.2 | 0/1 |
| missing_sensor | 40/40 | 0.0 / 0.0 | 36.1 / 38.7 | 50.1 | 40/40 | 17828.6 / 26.2 | 0/0 |
| calm | 0/0 | — / — | — / — | — | — | — / — | 0/0 |
| variable | 0/0 | — / — | — / — | — | — | — / — | 0/0 |
| missing_weather | 0/0 | — / — | — / — | — | — | — / — | 0/0 |
| insufficient_sensors | 0/0 | — / — | — / — | — | — | — / — | 0/0 |

Retained 480/640 worlds; 160 explicit refusals; 0 crashes. Unsupported conditions remain in this denominator. Alarms are different tests: old in-sample residual screen versus new leave-one-sensor-out predictive screen. An absence of alarms is not proof of adequacy; missing diagnostic blocks are recorded in raw outcomes.

| Condition | Median source-model weight | New narrow region misses | New wrong sharp regions | Truth outside supported cells |
|---|---|---|---|---|
| weak_signal | 0.483 | 0/40 | 0/40 | 0/40 |
| strong_signal | 1.000 | 14/40 | 14/40 | 0/40 |
| ambiguous | 0.500 | 0/40 | 0/40 | 0/40 |
| high_noise | 1.000 | 3/40 | 3/40 | 0/40 |
| background_shift | 1.000 | 14/40 | 14/40 | 0/40 |
| changing_background | 1.000 | 14/40 | 14/40 | 0/40 |
| two_sources | 1.000 | 33/40 | 33/40 | 0/40 |
| off_grid | 0.475 | 1/40 | 1/40 | 0/40 |
| direction_bias | 0.414 | 0/40 | 0/40 | 0/40 |
| speed_bias | 1.000 | 7/40 | 7/40 | 0/40 |
| clustered | 0.493 | 0/40 | 0/40 | 0/40 |
| missing_sensor | 1.000 | 0/40 | 0/40 | 0/40 |

A narrow miss means the conditional 90% region occupies <25% of supported domain area and misses the actual continuous primary source. A wrong sharp region also has source-model weight >0.9. Two-source truth refers to the designated primary source; its coverage under a one-source model is descriptive. Old 90% grid-set coverage is saved separately and has no geographic area meaning. Ambiguous old MAP ties receive no fabricated unique-error summary.

## Reproduction and integrity

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m upwind.validation.overhaul_regression \
  --out evaluations/overhaul/development-regression --report docs/ENGINE_DEVELOPMENT_COMPARISON.md
```

Relevant production source hashes stayed unchanged during this run: **True**. Exact before/after hashes, configuration, generator and evaluator hashes, environment, every seed's input hash, loaded/excluded/fitted counts, diagnostics, source weights and numerical outcomes are saved beside this report in `evaluations/overhaul/development-regression`. If the source changed during the run, this mixed-version run must not be treated as a frozen comparison.

Measured-data source validation remains absent. These old inputs use the same scalar Gaussian transport family as the original model, with controlled mismatches; improvements here do not establish generalization. Read the separately frozen overhaul protocol and independent challenge results for that evidence. Regressions remain in this table and raw outputs.
