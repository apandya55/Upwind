# Engine 0.6 — comparative stress results

Frozen protocol [UW-ENGINE-2026-06](ENGINE_V06_PROTOCOL.md); [implementation and equations](ENGINE_V06_IMPLEMENTATION.md). Both engines received identical observable inputs. **Synthetic evidence only; no measured field accuracy or organizational attribution readiness is established.**

Exact source/configuration: [49-file freeze](../evaluations/engine-v06/freeze.json), [archived source](../evaluations/engine-v06/frozen-source), [baseline manifest](../evaluations/engine-v06/baseline-manifest.json). The stage named calibration was an assessment; no probability calibration transform or revised threshold was fitted.

## Fresh final comparison

480 condition-worlds across 24 paired seed blocks and 20 conditions; 960 source-fit attempts. Refusals and crashes remain in the attempt denominators. Conditional geographic coverage, point error, region area and acceptance answer different questions. The table reports medians of the posterior-mean and density-mode Euclidean errors, including fitted source-present worlds.

| Condition | Engine | Fit / attempts | Accepted | Wrong / accepted | Covered / source fits | Median mean / mode error (m) | Mean region % |
|---|---|---:|---:|---:|---:|---:|---:|
| characterized_nominal | 0.5.0 | 24/24 | 2 | 0/2 | 24/24 | 137.2 / 166.6 | 74.7 |
| characterized_nominal | 0.6.0 | 24/24 | 2 | 0/2 | 24/24 | 141.1 / 179.9 | 78.2 |
| unknown_nominal | 0.5.0 | 24/24 | 0 | 0/0 | 23/24 | 157.7 / 185.7 | 84.8 |
| unknown_nominal | 0.6.0 | 24/24 | 0 | 0/0 | 23/24 | 157.7 / 191.3 | 84.8 |
| direction_unknown | 0.5.0 | 24/24 | 1 | 0/1 | 20/24 | 156.3 / 271.0 | 83.4 |
| direction_unknown | 0.6.0 | 24/24 | 1 | 0/1 | 20/24 | 156.2 / 276.7 | 83.4 |
| direction_characterized | 0.5.0 | 24/24 | 1 | 0/1 | 24/24 | 148.7 / 121.8 | 73.4 |
| direction_characterized | 0.6.0 | 24/24 | 1 | 0/1 | 24/24 | 149.5 / 159.7 | 77.3 |
| speed_bias | 0.5.0 | 24/24 | 0 | 0/0 | 22/24 | 152.2 / 217.0 | 84.3 |
| speed_bias | 0.6.0 | 24/24 | 0 | 0/0 | 22/24 | 152.2 / 223.8 | 84.3 |
| clock_lag | 0.5.0 | 24/24 | 0 | 0/0 | 23/24 | 163.0 / 237.6 | 84.2 |
| clock_lag | 0.6.0 | 24/24 | 0 | 0/0 | 23/24 | 163.0 / 241.3 | 84.2 |
| distant_station | 0.5.0 | 0/24 | 0 | 0/0 | — | — | — |
| distant_station | 0.6.0 | 0/24 | 0 | 0/0 | — | — | — |
| spatial_winds | 0.5.0 | 24/24 | 3 | 1/3 | 19/24 | 154.1 / 172.6 | 74.1 |
| spatial_winds | 0.6.0 | 24/24 | 3 | 1/3 | 19/24 | 154.1 / 172.2 | 74.0 |
| variable_weather | 0.5.0 | 0/24 | 0 | 0/0 | — | — | — |
| variable_weather | 0.6.0 | 0/24 | 0 | 0/0 | — | — | — |
| weak | 0.5.0 | 24/24 | 0 | 0/0 | 23/24 | 173.2 / 255.1 | 86.4 |
| weak | 0.6.0 | 24/24 | 0 | 0/0 | 23/24 | 173.3 / 288.5 | 86.4 |
| correlated | 0.5.0 | 24/24 | 0 | 0/0 | 17/24 | 165.1 / 230.3 | 67.8 |
| correlated | 0.6.0 | 24/24 | 0 | 0/0 | 17/24 | 165.0 / 223.3 | 67.8 |
| two_sources | 0.5.0 | 24/24 | 1 | 1/1 | 23/24 | 158.8 / 171.3 | 78.8 |
| two_sources | 0.6.0 | 24/24 | 0 | 0/0 | 23/24 | 158.8 / 177.4 | 78.8 |
| background | 0.5.0 | 24/24 | 0 | 0/0 | 0/0 | — / — | 86.3 |
| background | 0.6.0 | 24/24 | 0 | 0/0 | 0/0 | — / — | 86.3 |
| independent_transport | 0.5.0 | 24/24 | 6 | 0/6 | 24/24 | 135.0 / 212.1 | 64.3 |
| independent_transport | 0.6.0 | 24/24 | 5 | 0/5 | 24/24 | 131.2 / 226.6 | 69.6 |
| sensor_dropout | 0.5.0 | 24/24 | 0 | 0/0 | 22/24 | 159.8 / 250.6 | 84.6 |
| sensor_dropout | 0.6.0 | 24/24 | 0 | 0/0 | 24/24 | 160.8 / 240.1 | 85.8 |
| sensor_bias | 0.5.0 | 24/24 | 0 | 0/0 | 10/24 | 183.6 / 227.4 | 34.9 |
| sensor_bias | 0.6.0 | 24/24 | 0 | 0/0 | 12/24 | 186.2 / 218.5 | 41.3 |
| shared_reference_bias | 0.5.0 | 24/24 | 0 | 0/0 | 17/24 | 179.7 / 278.2 | 73.0 |
| shared_reference_bias | 0.6.0 | 24/24 | 0 | 0/0 | 17/24 | 175.5 / 281.1 | 78.5 |
| source_outside_domain | 0.5.0 | 24/24 | 1 | 1/1 | 0/24 | 365.8 / 317.4 | 84.6 |
| source_outside_domain | 0.6.0 | 24/24 | 0 | 0/0 | 0/24 | 366.9 / 383.8 | 86.0 |
| extreme_readings | 0.5.0 | 24/24 | 0 | 0/0 | 24/24 | 151.6 / 227.4 | 79.1 |
| extreme_readings | 0.6.0 | 24/24 | 0 | 0/0 | 24/24 | 154.1 / 207.7 | 81.7 |
| shared_lineage | 0.5.0 | 24/24 | 0 | 0/0 | 17/24 | 180.8 / 306.6 | 83.5 |
| shared_lineage | 0.6.0 | 24/24 | 0 | 0/0 | 17/24 | 180.8 / 312.4 | 83.5 |

All per-condition Wilson95% intervals and accepted-only error/area distributions are in [summary.json](../evaluations/engine-v06/summary.json). `Wrong` counts accepted source-present regions missing truth plus any accepted background-only false source alarms; geographic misses and false alarms are also stored separately. These contrived conditions are not an operational mixture; do not turn the pooled fraction into an accuracy claim.

## Predeclared targets and paired losses

- Characterized nominal overall median density-mode error ≤50m: **FAIL** (179.9m).
- Characterized nominal overall median posterior-mean error ≤50m: **FAIL** (141.1m).
- Fewer accepted shared-reference-bias errors: **FAIL**. Useful nominal acceptance must be considered alongside this count.
- paired_absolute_map: candidate minus baseline 7.015; seed-block bootstrap95% [2.813, 11.195], 24 blocks/408 paired worlds. Negative favours candidate. Squared location units are m², absolute location m, passive RMSE µg/m³.
- paired_absolute_mean: candidate minus baseline 0.357; seed-block bootstrap95% [-1.089, 1.845], 24 blocks/408 paired worlds. Negative favours candidate. Squared location units are m², absolute location m, passive RMSE µg/m³.
- paired_squared_mean: candidate minus baseline 89.891; seed-block bootstrap95% [-543.192, 716.112], 24 blocks/408 paired worlds. Negative favours candidate. Squared location units are m², absolute location m, passive RMSE µg/m³.
- paired_passive_rmse: candidate minus baseline -0.001; seed-block bootstrap95% [-0.002, 0.001], 4 blocks/72 paired worlds. Negative favours candidate. Squared location units are m², absolute location m, passive RMSE µg/m³.

## Passive concentration prediction

| Engine | Scored / scheduled | Mean world RMSE µg/m³ | Mean NLPD | Mean interval coverage | Mean interval width µg/m³ |
|---|---:|---:|---:|---:|---:|
| plume-weather-0.5.0 | 72/80 | 2.059 | 2.198 | 0.900 | 6.633 |
| plume-robust-0.6.0 | 72/80 | 2.059 | 2.198 | 0.900 | 6.630 |

Each world has12 correlated target outcomes. Unavailable weather fits remain in the80 scheduled cases per engine. Predictions are retrospective at the last observed timestamp, not forecasts.

## Equal-budget downstream planning

12 paired worlds (four seeds in each of three conditions), four locked methods and48 actual downstream candidate fits. All policies receive identical initial pollution/weather records and permissible candidates. All updates use the candidate engine. Maximum250 cost units/two instruments; actual spending is stored. Choices were saved and hashed before outcomes were revealed. Weather hardware/time is not free or included.

| Condition | Comparator | Paired worlds | Prediction planner losses | Mean RMSE difference | Paired bootstrap95% |
|---|---|---:|---:|---:|
| characterized_nominal | spread | 4 | 2 | -0.003 | [-0.019, 0.013] |
| characterized_nominal | random | 4 | 1 | 0.003 | [-0.211, 0.263] |
| characterized_nominal | wind | 4 | 1 | -0.008 | [-0.037, 0.012] |
| shared_reference_bias | spread | 4 | 2 | -0.034 | [-0.137, 0.026] |
| shared_reference_bias | random | 4 | 2 | -0.015 | [-0.190, 0.169] |
| shared_reference_bias | wind | 4 | 2 | -0.050 | [-0.116, 0.015] |
| independent_transport | spread | 4 | 2 | -0.003 | [-0.019, 0.013] |
| independent_transport | random | 4 | 1 | 0.003 | [-0.211, 0.263] |
| independent_transport | wind | 4 | 1 | -0.008 | [-0.036, 0.012] |

Negative differences favour the prediction planner. Four worlds per condition provide weak evidence about tails; losses remain visible and no general planner superiority follows. Concentration gains do not establish source-attribution accuracy.

## Original 18 failures: inspected regression only

The original0.4 results are retained and reproduced separately. All18 original accepted regions missed truth. Both0.5 and0.6 were rerun on those same observed campaigns; these cases are development-used, not fresh final evidence.

| Seed | 0.4 accepted / covered | 0.5 accepted / covered | 0.6 accepted / covered | 0.6 mean / mode error (m) |
|---|---|---|---|---:|
| 910001 | True / False | True / True | False / True | 81.5 / 24.1 |
| 910002 | True / False | True / True | True / True | 42.9 / 23.6 |
| 910003 | True / False | False / True | False / True | 173.5 / 183.7 |
| 910004 | True / False | True / True | True / True | 23.7 / 34.2 |
| 910005 | True / False | True / True | True / True | 259.4 / 333.5 |
| 910006 | True / False | True / True | True / True | 39.8 / 47.4 |
| 910008 | True / False | True / True | True / True | 16.5 / 15.5 |
| 910009 | True / False | True / True | False / True | 110.4 / 109.3 |
| 910021 | True / False | False / True | False / True | 107.6 / 79.3 |
| 910022 | True / False | True / True | True / True | 104.3 / 68.5 |
| 910024 | True / False | True / True | True / True | 52.6 / 147.3 |
| 910026 | True / False | True / True | True / True | 29.3 / 38.3 |
| 910027 | True / False | True / True | False / True | 8.7 / 16.8 |
| 910028 | True / False | True / True | False / True | 66.7 / 27.8 |
| 910029 | True / False | True / True | True / True | 98.8 / 184.2 |
| 910033 | True / False | True / True | True / True | 107.1 / 136.4 |
| 910034 | True / False | True / True | True / True | 20.7 / 14.2 |
| 910035 | True / False | True / True | False / True | 26.3 / 65.2 |

## Separate development diagnostics

These controls use inspected development seed7100000 only and do not select the candidate or contribute independent final worlds. [Auxiliary declaration](ENGINE_V06_AUXILIARY.md).

| Control | Integral | Parent-mass TV distance to uniform fine | Mean-position distance to uniform fine (m) |
|---|---|---:|---:|
| observed_development_nominal | coarse | 0.005468 | 0.399 |
| observed_development_nominal | adaptive | 0.001190 | 0.048 |
| constructed_noiseless_known_weather | coarse | 0.147413 | 13.760 |
| constructed_noiseless_known_weather | adaptive | 0.065485 | 5.847 |

The fine grid is another finite integral, not physical truth. Closer numerical agreement does not guarantee a smaller true-source point error. A projection-direction error invalidated the first constructed-control preflight; its raw files/source are retained under convergence-preflight with an explicit exclusion marker. The corrected control uses the inverse transformation. No production code or final inputs changed.

| Development condition | Common-mode prior | Extra direction SD | Mean source error (m) | Region area fraction | Covers truth |
|---|---:|---:|---:|---:|---|
| characterized_nominal | 0.10 | 20° | 63.5 | 0.169 | True |
| characterized_nominal | 0.25 | 20° | 63.2 | 0.170 | True |
| characterized_nominal | 0.50 | 20° | 62.3 | 0.178 | True |
| characterized_nominal | 0.25 | 15° | 63.1 | 0.171 | True |
| characterized_nominal | 0.25 | 30° | 63.3 | 0.170 | True |
| shared_reference_bias | 0.10 | 20° | 293.6 | 0.186 | False |
| shared_reference_bias | 0.25 | 20° | 259.2 | 0.339 | True |
| shared_reference_bias | 0.50 | 20° | 209.5 | 0.448 | True |
| shared_reference_bias | 0.25 | 15° | 308.7 | 0.164 | False |
| shared_reference_bias | 0.25 | 30° | 167.1 | 0.375 | True |

The hidden-common-bias result depends strongly on the uncalibrated prior. Acceptance is not assessed in these diagnostic fits because predictive refits were disabled. Separately labelled correct-weather oracles are evaluator-only diagnoses, not deployed corrections or field calibration. Baseline0.5 mean errors retain its historical cell-center estimator; candidate0.6 integrates spatial-node positions. Both modes are cell-based finite decisions.


## Engineering, runtime and provenance

The source archive/freeze, calibration, all original regressions and every final shard must match before this report is generated. Initial non-frozen development/prototype timing, source drift and the zero-prior test-adapter mismatch are retained. Unused standard-library imports in frozen evaluation helpers were retained for byte identity; production/tests and non-frozen reporting helpers pass their recorded static checks. The final candidate does not branch on scenario names, IDs or evaluator truth. All final seeds are now inspected and cannot be reused for future model selection.

The separate engineering artifacts repeat701,017 numerical checks,900 placement checks and5,000 seeded CSV cases plus four API overload rounds. These use the existing fixed batteries; they are not that many new independent observations. Acknowledged writes, malformed-input refusals and recovery are checked explicitly. Exact current test/build/browser logs and bounded isolated resource probes are retained alongside the report. Runtime in final rows includes four-worker contention and, for scheduled cases, prediction scoring; it is not an isolated latency benchmark.

Measured tracer validation remains unperformed. Official primary data access was previously denied by the proxy, and the inspected secondary Prairie Grass workbook lacks verified provenance/units/meteorology compatibility. No synthetic outcome removes those blockers. Unknown source count, wind fields/clock errors, sensor error and a source outside the declared rectangle can still defeat this restricted steady-source model. See the failure rows and actual acceptance/coverage denominators before making an operational decision.

## Final application and resource checks

After scientific evaluation, two engineering safeguards bound diagnostic workspaces and target covariance allocation. Original failures and source remain archived; see [hardening](ENGINE_V06_HARDENING.md). Current checks use the separately hashed hardened code, with unchanged configuration and verified AST scope. The separately labelled [observability control](ENGINE_V06_OBSERVABILITY_RESULTS.md) does not replace the primary results.

Post-hardening exact-source release command exit codes: {'pytest': 0, 'frontend_build': 0, 'browser': 0}. Backend209tests, eight Chromium workflows and the frontend build/typecheck logs are retained. Resource children run sequentially after all scientific/planning workers finish, each with a60s/2GiB ceiling.10,000loaded readings are not10,000inverted readings.

| Study | Requested fitted limit | Comparison supplied | Child status | Analysis status | Fitted rows | Seconds | Peak RSS MiB |
|---|---:|---|---|---|---:|---:|---:|
| single window | 128 | False | finished | ok | 128 | 42.75 | 653.0 |
| single window | 512 | False | finished | ok | 512 | 42.66 | 697.7 |
| campaign | 128 | False | finished | insufficient_data | 0 | 1.71 | 211.9 |
| campaign | 512 | False | finished | insufficient_data | 0 | 1.73 | 214.1 |
| campaign | 512 | True | finished | insufficient_data | 0 | 1.82 | 214.2 |

- campaign, limit128, comparisonsFalse: Inference limit 128 cannot retain all 240 sensor/window groups; increase the inference limit or split the investigation
- campaign, limit512, comparisonsFalse: Weather uncertainty exceeds the supported numerical workload for this study size. Reduce maximum fitted readings or supply appropriate independent wind comparisons; all raw readings are retained.
- campaign, limit512, comparisonsTrue: Weather uncertainty exceeds the supported numerical workload for this study size. Reduce maximum fitted readings or supply appropriate independent wind comparisons; all raw readings are retained.

A finished child can explicitly refuse inference. Richer weather alternatives can increase work or refuse a formerly fitted study; this is a capability regression, not a successful localization. These observed timings are not a shared-service SLA. Historical0.5 measurements remain in SEVERE_STRESS_RESULTS.md; different algorithms/circumstances prevent treating their ratio as a universal speedup.
