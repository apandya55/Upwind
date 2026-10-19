# Development-only covariance and quadrature sensitivity

**No production parameters were changed. No calibration or final worlds were accessed.** These are 72 development condition/seed worlds revisited under four declared configurations (288 fits), with the same observations paired across configurations. Old scalar-family cases use fresh development seeds 410000–410011; independent challenge cases use the declared development split with those same seeds. Seeds are reused across conditions, so neither the 72 condition/seed worlds nor the 288 fits represent that many independent campaigns. Neither dataset is untouched evaluation.

The factorial compares temporal model-error correlation scales of 600 seconds and 10¹² seconds (effectively persistent over the steady window), crossed with midpoint-cell targets of 20 m and 10 m. The 24-cell-per-axis cap stays fixed. Therefore a target of 10 m does **not** guarantee 10 m resolution; actual cell side lengths and retained cells are reported. The old generator has persistent spatial errors. The independent development generator has a decaying spatial/temporal field, heteroscedastic noise and a different transport family. This contrast investigates sensitivity rather than selecting a universally correct covariance.

| Generator / condition | Time scale s / target m | Fits | Region coverage | 95% Wilson interval | Median mean error m | Median region area m² (% domain) | Median source weight | Wrong sharp | Alarms | Target RMSE µg/m³ |
|---|---|---|---|---|---|---|---|---|---|---|
| old_scalar_family / strong_signal | 600 / 20 | 12/12 | 9/12 | 0.47–0.91 | 40.5 | 5943 (8.7%) | 1.000 | 3 | 0 | — |
| old_scalar_family / strong_signal | 600 / 10 | 12/12 | 11/12 | 0.65–0.99 | 37.8 | 4487 (6.6%) | 1.000 | 1 | 0 | — |
| old_scalar_family / strong_signal | 1e+12 / 20 | 12/12 | 9/12 | 0.47–0.91 | 40.0 | 6871 (10.1%) | 1.000 | 3 | 0 | — |
| old_scalar_family / strong_signal | 1e+12 / 10 | 12/12 | 11/12 | 0.65–0.99 | 38.6 | 4992 (7.3%) | 1.000 | 1 | 0 | — |
| old_scalar_family / two_sources | 600 / 20 | 12/12 | 2/12 | 0.05–0.45 | 60.1 | 2600 (3.8%) | 1.000 | 10 | 0 | — |
| old_scalar_family / two_sources | 600 / 10 | 12/12 | 0/12 | 0.00–0.24 | 61.2 | 2275 (3.3%) | 1.000 | 12 | 0 | — |
| old_scalar_family / two_sources | 1e+12 / 20 | 12/12 | 2/12 | 0.05–0.45 | 59.8 | 2600 (3.8%) | 1.000 | 10 | 0 | — |
| old_scalar_family / two_sources | 1e+12 / 10 | 12/12 | 0/12 | 0.00–0.24 | 60.8 | 2401 (3.5%) | 1.000 | 12 | 0 | — |
| old_scalar_family / direction_bias | 600 / 20 | 12/12 | 11/12 | 0.65–0.99 | 70.4 | 57943 (85.2%) | 0.407 | 0 | 0 | — |
| old_scalar_family / direction_bias | 600 / 10 | 12/12 | 11/12 | 0.65–0.99 | 70.4 | 58076 (85.4%) | 0.408 | 0 | 0 | — |
| old_scalar_family / direction_bias | 1e+12 / 20 | 12/12 | 11/12 | 0.65–0.99 | 70.5 | 57943 (85.2%) | 0.408 | 0 | 0 | — |
| old_scalar_family / direction_bias | 1e+12 / 10 | 12/12 | 11/12 | 0.65–0.99 | 70.5 | 58139 (85.5%) | 0.408 | 0 | 0 | — |
| independent_development / strong_signal | 600 / 20 | 12/12 | 12/12 | 0.76–1.00 | 74.7 | 124442 (76.4%) | 0.591 | 0 | 0 | 1.27 |
| independent_development / strong_signal | 600 / 10 | 12/12 | 11/12 | 0.65–0.99 | 74.4 | 124516 (76.5%) | 0.591 | 1 | 0 | 1.27 |
| independent_development / strong_signal | 1e+12 / 20 | 12/12 | 12/12 | 0.76–1.00 | 72.4 | 130403 (80.1%) | 0.524 | 0 | 0 | 1.19 |
| independent_development / strong_signal | 1e+12 / 10 | 12/12 | 12/12 | 0.76–1.00 | 72.3 | 130452 (80.1%) | 0.523 | 0 | 0 | 1.18 |
| independent_development / correlated_errors | 600 / 20 | 12/12 | 12/12 | 0.76–1.00 | 69.2 | 95381 (58.6%) | 0.745 | 0 | 0 | 2.16 |
| independent_development / correlated_errors | 600 / 10 | 12/12 | 12/12 | 0.76–1.00 | 69.5 | 94836 (58.2%) | 0.746 | 0 | 0 | 2.15 |
| independent_development / correlated_errors | 1e+12 / 20 | 12/12 | 12/12 | 0.76–1.00 | 71.7 | 114010 (70.0%) | 0.649 | 0 | 1 | 2.40 |
| independent_development / correlated_errors | 1e+12 / 10 | 12/12 | 12/12 | 0.76–1.00 | 71.3 | 113774 (69.9%) | 0.649 | 0 | 1 | 2.38 |
| independent_development / weak_signal | 600 / 20 | 12/12 | 9/12 | 0.47–0.91 | 80.7 | 134688 (82.7%) | 0.382 | 0 | 0 | 1.36 |
| independent_development / weak_signal | 600 / 10 | 12/12 | 9/12 | 0.47–0.91 | 80.8 | 134833 (82.8%) | 0.382 | 0 | 0 | 1.36 |
| independent_development / weak_signal | 1e+12 / 20 | 12/12 | 10/12 | 0.55–0.95 | 82.1 | 135433 (83.2%) | 0.383 | 0 | 0 | 1.38 |
| independent_development / weak_signal | 1e+12 / 10 | 12/12 | 9/12 | 0.47–0.91 | 82.1 | 135399 (83.2%) | 0.384 | 0 | 0 | 1.38 |

The location estimate and 90% cell union are conditional on the single-source family. Wrong sharp means source-model weight >0.9 plus a region smaller than 25% of supported domain that misses primary truth. Two-source coverage of designated primary truth is descriptive under model misspecification. Region area and error must be considered with coverage; broader regions alone are not useful localization. Twelve worlds per condition give wide intervals, so small differences cannot establish a preferred setting.

Independent-generator target predictions concern three withheld instruments at the final observed timestamp. They use the available historical steady-window wind, with future observations revealed only inside this evaluator. Their outcomes and hidden transport parameters never enter fitting. Raw outputs also include prediction against noiseless transport means, which is a separate task from predicting noisy readings. No planner runs in this sensitivity experiment.

## Paired changes from the production 600 s / 20 m setting

| Generator / condition | Alternative time s / target m | Mean error change m | Net covered worlds change | Mean target RMSE change µg/m³ |
|---|---|---|---|---|
| old_scalar_family / strong_signal | 600 / 10 | -2.38 | +2 | — |
| old_scalar_family / strong_signal | 1e+12 / 20 | -0.07 | +0 | — |
| old_scalar_family / strong_signal | 1e+12 / 10 | -2.11 | +2 | — |
| old_scalar_family / two_sources | 600 / 10 | -2.30 | -2 | — |
| old_scalar_family / two_sources | 1e+12 / 20 | -0.49 | +0 | — |
| old_scalar_family / two_sources | 1e+12 / 10 | -2.44 | -2 | — |
| old_scalar_family / direction_bias | 600 / 10 | -0.03 | +0 | — |
| old_scalar_family / direction_bias | 1e+12 / 20 | -0.29 | +0 | — |
| old_scalar_family / direction_bias | 1e+12 / 10 | -0.31 | +0 | — |
| independent_development / strong_signal | 600 / 10 | +0.38 | -1 | -0.000 |
| independent_development / strong_signal | 1e+12 / 20 | +1.59 | +0 | -0.063 |
| independent_development / strong_signal | 1e+12 / 10 | +1.90 | +0 | -0.064 |
| independent_development / correlated_errors | 600 / 10 | -0.78 | +0 | -0.010 |
| independent_development / correlated_errors | 1e+12 / 20 | +1.01 | +0 | +0.006 |
| independent_development / correlated_errors | 1e+12 / 10 | +0.42 | +0 | +0.002 |
| independent_development / weak_signal | 600 / 10 | +0.02 | +0 | -0.000 |
| independent_development / weak_signal | 1e+12 / 20 | +0.25 | +1 | -0.020 |
| independent_development / weak_signal | 1e+12 / 10 | +0.27 | +0 | -0.020 |

Positive error/RMSE changes are worse. All paired seed-level differences are retained. Covariance and quadrature can both change the answer; this experiment cannot separate every physical cause or validate field calibration. In particular, missing multiple-source physics cannot be repaired by finer quadrature or a different correlation time.

## Reproduction

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/overhaul_covariance_ablation.py \
  --out evaluations/overhaul/covariance-quadrature-sensitivity --report docs/ENGINE_SENSITIVITY.md
```

The process restored CONFIG after every fit and at exit: **True**. Relevant source hashes unchanged during execution: **True**. The numerical source/configuration, generator, evaluator script and protocol hashes, input hashes, every fit and paired difference are saved in `evaluations/overhaul/covariance-quadrature-sensitivity`. Use a fresh output folder to repeat. Production remains the documented 600 s / 20 m configuration; no final-set outcome was used to choose a setting.
