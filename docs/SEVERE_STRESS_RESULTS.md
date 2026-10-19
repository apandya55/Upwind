# Severe stress results

Model **plume-weather-0.5.0**, protocols **UW-STRESS-2026-04/04C**. Synthetic evidence only; no measured field accuracy or certification follows. Production source/configuration was unchanged throughout. The evaluated source and both protocols are retained with hashes. All preflight failures/refusals and every scheduled case remain visible.

The model did not meet all predeclared nominal accuracy targets. The main mismatch campaign retained **17 accepted geographic errors**. Software checks and the request-boundary repair are reported separately from those scientific failures.

## Larger nominal confirmation: precision and reliability assessed separately

480 fixed fresh characterized-nominal worlds, with independent reference weather. Fitted/refused/crash: {'fitted': 480}. Accepted 82/480; accepted geographic errors 0/82, Wilson95% interval 0.0–4.5%. Conditional region coverage 477/480, interval 98.2–99.8%.

MAP median/p90/max 117.3/333.6/498.9m. No-data source-domain-centroid median 163.4m. Accepted MAP median/p90 35.2/107.7m. Mean conditional region area all/accepted 63.0/18.5% domain. A covered region can still have a distant point estimate.

| Predeclared nominal target | Outcome |
|---|---|
|Median source-point error ≤50 m|FAIL / not established|
|Conditional region coverage ≥90%|PASS|
|No observed accepted-region misses|PASS|
|Accepted-error Wilson95% upper bound ≤5%|PASS|

Passing a conditional error bound does not establish fine spatial precision or real-world accuracy. The full target set must be considered together. This cohort has favorable explicitly independent weather assumptions; hidden common bias and unsupported physics are challenged separately below.

## Main stress matrix

960 scheduled cases:48 fresh seed blocks×20conditions, continuously randomized monitor layouts and wind regimes. Seeds repeat across conditions; they are not960independent campaigns. Explicit refusals stay in generated denominators. All point/area statistics below describe fitted cases. Background-only has no geographic source truth.

| Condition | Fit/refused/crash | Accepted | Wrong geography/accepted | Coverage/fitted source | MAP median/p90/max m | Area all/accepted % | Unwarned misses |
|---|---|---|---|---|---|---|---|
|characterized_nominal|48/0/0|12/48|0/12|48/48|85.5/263.5/446.4|58.1/17.0|0/48|
|unknown_nominal|48/0/0|9/48|0/9|45/48|128.3/382.4/426.3|72.2/30.7|3/48|
|direction_unknown|48/0/0|7/48|0/7|45/48|216.8/391.4/451.1|73.0/25.8|3/48|
|direction_characterized|48/0/0|13/48|0/13|48/48|108.5/343.1/469.0|57.1/15.0|0/48|
|speed_bias|48/0/0|8/48|0/8|45/48|132.4/375.3/416.3|72.0/27.2|3/48|
|clock_lag|48/0/0|3/48|0/3|47/48|134.6/372.2/491.9|75.7/30.1|1/48|
|distant_station|0/48/0|0/48|0/0 (undefined)|0/0 (undefined)|—/—/—|—/—|0/0 (undefined)|
|spatial_winds|48/0/0|6/48|0/6|43/48|168.2/337.3/491.9|73.6/23.3|4/48|
|variable_weather|0/48/0|0/48|0/0 (undefined)|0/0 (undefined)|—/—/—|—/—|0/0 (undefined)|
|weak|48/0/0|0/48|0/0 (undefined)|36/48|298.9/416.3/490.6|84.7/—|12/48|
|correlated|48/0/0|4/48|1/4|33/48|221.2/368.7/508.0|57.1/24.9|4/48|
|two_sources|48/0/0|9/48|1/9|43/48|146.5/329.5/426.3|67.7/29.2|4/48|
|background|48/0/0|0/48|0/0 (undefined)|0/0 (undefined)|—/—/—|84.8/—|0/0 (undefined)|
|independent_transport|48/0/0|17/48|4/17|44/48|133.9/322.3/446.4|50.0/13.3|4/48|
|sensor_dropout|48/0/0|5/48|0/5|48/48|144.8/340.9/478.8|71.1/18.3|0/48|
|sensor_bias|48/0/0|0/48|0/0 (undefined)|30/48|216.5/367.9/441.1|34.6/—|0/48|
|shared_reference_bias|48/0/0|6/48|6/6|31/48|280.1/433.5/479.1|62.7/10.4|14/48|
|source_outside_domain|48/0/0|4/48|4/4|0/48|315.5/441.9/643.7|71.6/20.8|42/48|
|extreme_readings|48/0/0|10/48|0/10|48/48|94.7/282.0/461.4|60.7/15.0|0/48|
|shared_lineage|48/0/0|8/48|1/8|43/48|213.0/395.5/485.1|72.8/27.6|5/48|

### Warnings, presence errors and intervals

| Condition | Accepted geography error95% interval | Coverage95% interval | Predictive / weather warnings | Missed sources | Background family false alarms / accepted false alarms |
|---|---|---|---|---|---|
|characterized_nominal|0.0–24.3%|92.6–100.0%|0/48 / 0/48|24/48|0/0 (undefined) / 0/0 (undefined)|
|unknown_nominal|0.0–29.9%|83.2–97.9%|0/48 / 0/48|28/48|0/0 (undefined) / 0/0 (undefined)|
|direction_unknown|0.0–35.4%|83.2–97.9%|0/48 / 0/48|32/48|0/0 (undefined) / 0/0 (undefined)|
|direction_characterized|0.0–22.8%|92.6–100.0%|0/48 / 0/48|28/48|0/0 (undefined) / 0/0 (undefined)|
|speed_bias|0.0–32.4%|83.2–97.9%|0/48 / 0/48|31/48|0/0 (undefined) / 0/0 (undefined)|
|clock_lag|0.0–56.2%|89.1–99.6%|2/48 / 0/48|28/48|0/0 (undefined) / 0/0 (undefined)|
|distant_station|undefined|undefined|0/0 (undefined) / 0/0 (undefined)|0/0 (undefined)|0/0 (undefined) / 0/0 (undefined)|
|spatial_winds|0.0–39.0%|77.8–95.5%|1/48 / 0/48|29/48|0/0 (undefined) / 0/0 (undefined)|
|variable_weather|undefined|undefined|0/0 (undefined) / 0/0 (undefined)|0/0 (undefined)|0/0 (undefined) / 0/0 (undefined)|
|weak|undefined|61.2–85.1%|0/48 / 0/48|47/48|0/0 (undefined) / 0/0 (undefined)|
|correlated|4.6–69.9%|54.7–80.1%|26/48 / 0/48|5/48|0/0 (undefined) / 0/0 (undefined)|
|two_sources|2.0–43.5%|77.8–95.5%|2/48 / 0/48|25/48|0/0 (undefined) / 0/0 (undefined)|
|background|undefined|undefined|0/48 / 0/48|0/0 (undefined)|0/48 / 0/48|
|independent_transport|9.6–47.3%|80.4–96.7%|1/48 / 0/48|23/48|0/0 (undefined) / 0/0 (undefined)|
|sensor_dropout|0.0–43.4%|92.6–100.0%|0/48 / 0/48|27/48|0/0 (undefined) / 0/0 (undefined)|
|sensor_bias|undefined|48.4–74.8%|48/48 / 0/48|12/48|0/0 (undefined) / 0/0 (undefined)|
|shared_reference_bias|61.0–100.0%|50.4–76.6%|3/48 / 0/48|36/48|0/0 (undefined) / 0/0 (undefined)|
|source_outside_domain|51.0–100.0%|0.0–7.4%|6/48 / 0/48|23/48|0/0 (undefined) / 0/0 (undefined)|
|extreme_readings|0.0–27.8%|92.6–100.0%|0/48 / 0/48|27/48|0/0 (undefined) / 0/0 (undefined)|
|shared_lineage|2.2–47.1%|77.8–95.5%|0/48 / 0/48|27/48|0/0 (undefined) / 0/0 (undefined)|

A warning-free fit is not a physical adequacy certificate. Hidden reference/primary bias deliberately violates an unverified independence claim; internal agreement cannot detect every shared error. The outside-domain case challenges a restricted source hypothesis family. Extreme-reading exclusion is recorded as a capability limit, not taken as evidence that a severe real event is impossible. Full distributions (including conditional mass, area, Brier, runtime and all denominators) are in [summary.json](../evaluations/severe-stress/summary.json). Every accepted error and software failure is retained in [failures.json](../evaluations/severe-stress/failures.json).

## Passive unseen-sensor predictions

240 scheduled worlds in the first12seed blocks per condition; unsupported-weather refusals remain unavailable. Twelve target readings within a world are correlated. Intervals below resample paired worlds 5,000 times, RNG 90311; positive advantage means comparator RMSE minus model RMSE. These are retrospective predictions at a recorded time, not forecasts or measurement-placement benefits.

| Condition | Scored / scheduled | RMSE mean µg/m³ | Mean90% interval coverage / width | RMSE advantage vs last-period spatial mean [95%] | Losses |
|---|---|---|---|---|---|
|characterized_nominal|12/12|1.6|94.4% / 6.5|0.020 [-0.095,0.116]|4/12|
|unknown_nominal|12/12|1.6|95.1% / 6.5|0.020 [-0.097,0.119]|4/12|
|direction_unknown|12/12|1.6|95.8% / 6.6|0.024 [-0.034,0.086]|5/12|
|direction_characterized|12/12|1.6|95.8% / 6.5|0.023 [-0.034,0.081]|5/12|
|speed_bias|12/12|1.6|95.8% / 6.6|0.023 [-0.035,0.083]|5/12|
|clock_lag|12/12|1.6|95.1% / 6.6|0.024 [-0.066,0.110]|5/12|
|distant_station|0/12|—|—% / —|unavailable|—|
|spatial_winds|12/12|1.6|95.1% / 6.5|0.028 [-0.062,0.105]|3/12|
|variable_weather|0/12|—|—% / —|unavailable|—|
|weak|12/12|1.6|95.8% / 6.6|0.024 [-0.036,0.083]|5/12|
|correlated|12/12|2.5|84.7% / 7.4|0.372 [-0.063,0.822]|3/12|
|two_sources|12/12|1.6|94.4% / 6.5|0.023 [-0.087,0.114]|4/12|
|background|12/12|1.6|94.4% / 6.5|0.018 [-0.102,0.119]|4/12|
|independent_transport|12/12|1.6|94.4% / 6.5|0.020 [-0.098,0.118]|4/12|
|sensor_dropout|12/12|1.6|95.1% / 7.0|-0.013 [-0.163,0.116]|7/12|
|sensor_bias|12/12|4.5|34.7% / 6.7|0.120 [-0.156,0.400]|5/12|
|shared_reference_bias|12/12|1.6|94.4% / 6.5|0.020 [-0.096,0.117]|4/12|
|source_outside_domain|12/12|1.6|94.4% / 6.5|0.023 [-0.093,0.120]|4/12|
|extreme_readings|12/12|1.6|95.1% / 6.6|0.024 [-0.100,0.137]|4/12|
|shared_lineage|12/12|1.6|94.4% / 6.5|0.021 [-0.093,0.120]|4/12|

The comparator uses only quality-reviewed available monitoring measurements in the last study period; it never uses target outcomes to choose its constant. A fixed prior-mean 10 µg/m³ comparator is also retained in JSON. Point-prediction RMSE, geographic accuracy and conditional interval coverage are different capabilities; do not transfer success between them.

## Post-hoc diagnosis: a retained accepted error

The first observed accepted error in the hidden-common-weather-bias condition (seed 6100001) was repeated unchanged, then diagnosed in two separate variants. This is post-hoc explanation, not a held-out improvement experiment or a production repair. Main inputs and source remain unchanged. The oracle variant subtracts only the evaluator-known injected common bias; that truth is unavailable to ordinary users and never enters the main campaign.

| Variant | Accepted | Region covers truth | MAP error m | Region area % domain | Predictive / weather warning |
|---|---|---|---|---|---|
|original|True|False|175.2|14.9|False / False|
|references_removed|True|False|177.6|42.6|False / False|
|oracle_common_bias_removed|True|True|86.5|19.5|False / False|

Removing reference data alone is not guaranteed to recover a displaced source: source/strength/background can compensate for wrong wind, and a finite bias prior can prefer a wrong geographic explanation. Agreement between two instruments cannot reveal every shared hidden error. Even evaluator-corrected weather does not guarantee a precise point estimate. These failures must not be reclassified as solved by a software-test pass or by knowing the injected truth after evaluation.

Nominal simulations use the compatible physical kernel with separately specified synthetic noise/strength distributions; they are not an exact full-model prior-predictive calibration or a measured-data validation. Several layouts are weakly informative, so region area and abstention remain essential.

## Engineering and resource stress

Numerical checks: 701,017, failed groups 0. Geographic placement checks: 900, failures 0 across 200 instances,100 independent exhaustive tiny optima and all-method constraints. These reproduce/extend deterministic property sequences; they are not empirical accuracy samples.

Adversarial CSV cases: 5,000; {'explicit_refusal': 2814, 'parsed': 2186, 'accepted_rows': 53, 'invalid_rows': 2133}; unexpected failures 0. Original raw CSV and accepted/invalid accounting are checked. Explicit parser/schema refusals are correct outcomes. Four isolated API rounds total 256 write requests/32 clients per round: 78acknowledged writes, all preserved=True; all round checks passed=True. The existing500 CSV fixtures repeat inside API rounds; they are not 2,000 new unique cases.

Each fresh resource child had 60s/2GiB, after the scientific workers completed. Shapes loaded 10,000 concentrations + 10,000 weather rows, 100 sites and 25 anchors; fit limits are 128/512, not 10,000 inverted rows.

| Campaign / compared weather | Limit / fitted | Status | Seconds | Peak MiB |
|---|---|---|---|---|
|False / False|128 / 128|ok|26.39|966.5|
|False / False|512 / 512|ok|50.52|1796.8|
|True / False|128 / 0|Inference limit 128 cannot retain all 240 sensor/window groups; increase the inference limit or split the investigation|1.42|218.3|
|True / False|512 / 0|Weather uncertainty exceeds the supported numerical workload for this study size. Reduce maximum fitted readings or supply appropriate independent wind comparisons; all raw readings are retained.|1.38|220.5|
|True / True|512 / 512|ok|27.88|1160.3|

### Request-boundary failure found and repaired after the frozen experiment

An additional isolated JSON probe exposed a 500 response for 1200 nested levels and acceptance of nonstandard NaN metadata that was silently serialized as null. These failures were not caught by the earlier CSV/overload battery. Both original probes and the isolated prototype results are retained. After all scientific workers and resource probes completed, only backend/upwind/api.py was hardened: bounded-depth JSON, finite numbers and explicit 422 refusal before persistence. Valid finite JSON and quoted CSV text keep their previous semantics. No likelihood, prior, source-support rule, planner or generated outcome changed.

The frozen-source suite passed 168 tests. The post-repair full suite passed 181 tests, including 13 new request-boundary regressions; eight Chromium workflows exercise the final API. The exact before/after API hashes and completion evidence are in [api-hardening.json](../evaluations/severe-stress/api-hardening.json). Historical weather-source verification uses `scripts/verify_weather_release.py --source evaluations/weather-bias/frozen-source`; the default current-tree check intentionally does not pretend the old API bytes are current.

Actual test/build/browser outcomes are retained in pytest.log, frontend-build.log and playwright.log under evaluations/severe-stress. The automated release verifier checks their completion along with raw case counts, source/configuration hashes and artifacts. Initial workers shared CPU capacity; nominal workers were then paused/resumed to keep four active inversion workers. Their raw case/overall wall clocks include suspension and contention. See [scheduling.json](../evaluations/severe-stress/scheduling.json). Only the fresh unpaused resource children describe isolated timings; none is a shared-service SLA. Scheduling changed no input, model parameter or numerical algorithm.

## Interpretation and reproduction

This campaign can expose software or scientific failures; it cannot guarantee extreme field accuracy. The original organizational-attribution goal remains unvalidated without compatible independent measured data, documented physics and prospective outcomes. Primary data access remains an external prerequisite. No scientific thresholds, priors, warnings or failed-case inclusion were changed in response to these outcomes.

[Main protocol](SEVERE_STRESS_PROTOCOL.md), [nominal supplement](STRESS_NOMINAL_CONFIRMATION.md), [reporting methods](STRESS_REPORTING_METHODS.md), [standalone figure](../evaluations/severe-stress/figures/stress-tradeoffs.png). Run `.venv/bin/python scripts/report_severe_stress.py` only after all runs complete; plot generation refuses existing output. Preserve previous artifacts on reproduction and choose a new run directory. All current seeds are now inspected and cannot serve as untouched tests for a repair.
