# Weather-bias repair results

Model **plume-weather-0.5.0**, protocol **UW-WEATHER-2026-03**. Synthetic research evidence only. The repair changes the error/usefulness tradeoff; it does not establish field reliability or universal weather-error detection.

## Original failures: development-used regression

| Seed | Old accepted/covered | New accepted/covered | MAP error old→new (m) | Region area old→new (% domain) |
|---|---|---|---|---|
|910001|True/False|True/True|150.7→17.6|2.5→6.2|
|910002|True/False|True/True|143.2→29.1|13.3→35.2|
|910003|True/False|False/True|240.3→198.1|22.4→62.5|
|910004|True/False|True/True|143.1→41.0|2.1→6.9|
|910005|True/False|True/True|299.9→328.5|9.6→32.7|
|910006|True/False|True/True|174.7→53.9|2.7→24.3|
|910008|True/False|True/True|123.0→16.9|1.1→5.5|
|910009|True/False|True/True|104.3→104.3|0.7→22.4|
|910021|True/False|False/True|207.2→85.9|16.9→52.6|
|910022|True/False|True/True|161.1→75.3|5.5→19.0|
|910024|True/False|True/True|155.8→140.5|2.7→35.5|
|910026|True/False|True/True|87.5→58.0|1.8→3.9|
|910027|True/False|True/True|142.1→17.3|3.4→7.8|
|910028|True/False|True/True|152.4→23.5|2.3→26.3|
|910029|True/False|True/True|209.9→182.9|1.8→15.1|
|910033|True/False|True/True|161.6→129.7|9.4→31.1|
|910034|True/False|True/True|137.2→8.9|4.1→7.1|
|910035|True/False|True/True|116.7→70.9|0.5→14.9|

All40 original biased cases: 40/40 fitted; accepted 17, wrong 0/17 (0.0%) of accepted and 0/40 (0.0%) of generated; coverage 38/40. MAP median/p90 108.1/328.6m; mean region area 46.3% domain.

Previously supported40 campaigns: 40/40 fitted; accepted 19, wrong 0/19 (0.0%) of accepted and 0/40 (0.0%) of generated; coverage 40/40. MAP median/p90 49.7/307.3m; mean region area 47.4% domain.

## Calibration and frozen decision

224 condition-worlds across16 seed blocks, 448 old/new outcomes. No numerical prior, threshold or acceptance transform was fitted. The predeclared conditional support rule was retained. Calibration already showed unresolved clock, spatial-wind, correlated-error and transport failures; final evaluation is a challenge of that frozen rule, not a claim these mechanisms were solved.

| Condition | Old accepted / wrong | New accepted / wrong | New coverage (fitted) |
|---|---|---|---|
|characterized_nominal|6 / 0|6 / 0|16/16|
|unknown_nominal|6 / 0|4 / 0|16/16|
|direction_unknown|1 / 1|4 / 1|14/16|
|direction_characterized|1 / 1|5 / 0|16/16|
|speed_bias|5 / 1|5 / 1|15/16|
|clock_lag|3 / 2|1 / 1|13/16|
|distant_station|0 / 0|0 / 0|0/0|
|spatial_winds|6 / 6|4 / 3|12/16|
|variable_weather|0 / 0|0 / 0|0/0|
|weak|0 / 0|0 / 0|12/16|
|correlated|1 / 0|2 / 1|9/16|
|two_sources|8 / 3|7 / 3|12/16|
|background|0 / 0|0 / 0|0/0|
|independent_transport|10 / 0|10 / 2|14/16|

After calibration, output-only changes list the actual comparison source/upstream/time/provenance used and correct generic mismatch wording to include weather checks. Two fixed calibration cases (with/without references) reproduce all numeric metrics and diagnostic checks exactly. No inference, planner, covariance, prior or rule changed. Exact identifiers are in [final-source-freeze.json](../evaluations/weather-bias/final-source-freeze.json); SHA256 source/configuration manifests identify the exact evaluated scientific source independently of later reporting and Git publication.

## Fresh final holdout

448 condition-worlds across32 paired seed blocks; 896 old/new outcomes, 360 actual follow-up refits. Each condition has32 generated worlds. Conditions reuse seeds; do not pool them as independent campaigns. Final layouts, bias magnitude bands/signs, clock-lag range and nonlinear spatial/time weather mismatch differ from development/calibration. All frozen hashes match before/after every final shard. Refusals remain in generated denominators.

| Condition | Model | Fit/refused/crash | Accepted | Wrong/accepted | Wrong/generated | Coverage (fitted) | MAP median/p90/max m | Area all/accepted % |
|---|---|---|---|---|---|---|---|---|
|characterized_nominal|0.4|32/0/0|11|0/11 (0.0%)|0/32 (0.0%)|32/32|37.2/196.6/415.1|43.6/11.8|
|characterized_nominal|0.5|32/0/0|11|0/11 (0.0%)|0/32 (0.0%)|32/32|51.3/207.1/415.1|45.1/13.4|
|unknown_nominal|0.4|32/0/0|11|0/11 (0.0%)|0/32 (0.0%)|32/32|37.2/196.6/415.1|43.6/11.8|
|unknown_nominal|0.5|32/0/0|8|0/8 (0.0%)|0/32 (0.0%)|32/32|58.9/257.5/518.9|64.0/23.3|
|direction_unknown|0.4|32/0/0|7|7/7 (100.0%)|7/32 (21.9%)|10/32|228.3/386.4/518.9|47.4/8.9|
|direction_unknown|0.5|32/0/0|9|0/9 (0.0%)|0/32 (0.0%)|30/32|172.8/367.0/443.5|63.3/28.2|
|direction_characterized|0.4|32/0/0|7|7/7 (100.0%)|7/32 (21.9%)|10/32|228.3/386.4/518.9|47.4/8.9|
|direction_characterized|0.5|32/0/0|10|0/10 (0.0%)|0/32 (0.0%)|31/32|37.9/126.0/351.9|43.6/15.2|
|speed_bias|0.4|32/0/0|10|0/10 (0.0%)|0/32 (0.0%)|32/32|43.2/126.0/371.0|41.6/12.9|
|speed_bias|0.5|32/0/0|6|0/6 (0.0%)|0/32 (0.0%)|32/32|68.7/249.2/423.4|63.1/23.3|
|clock_lag|0.4|32/0/0|4|2/4 (50.0%)|2/32 (6.2%)|24/32|102.8/220.1/245.9|41.0/10.6|
|clock_lag|0.5|32/0/0|3|0/3 (0.0%)|0/32 (0.0%)|32/32|84.2/241.6/439.6|60.1/24.5|
|distant_station|0.4|0/32/0|0|0/0 (undefined)|0/32 (0.0%)|0/0|—/—/—|—/—|
|distant_station|0.5|0/32/0|0|0/0 (undefined)|0/32 (0.0%)|0/0|—/—/—|—/—|
|spatial_winds|0.4|32/0/0|11|10/11 (90.9%)|10/32 (31.2%)|16/32|196.7/338.3/447.8|41.1/11.9|
|spatial_winds|0.5|32/0/0|10|4/10 (40.0%)|4/32 (12.5%)|27/32|162.6/341.4/518.9|60.9/31.9|
|variable_weather|0.4|0/32/0|0|0/0 (undefined)|0/32 (0.0%)|0/0|—/—/—|—/—|
|variable_weather|0.5|0/32/0|0|0/0 (undefined)|0/32 (0.0%)|0/0|—/—/—|—/—|
|weak|0.4|32/0/0|0|0/0 (undefined)|0/32 (0.0%)|25/32|213.1/384.3/488.1|71.1/—|
|weak|0.5|32/0/0|0|0/0 (undefined)|0/32 (0.0%)|27/32|324.7/438.4/518.9|83.0/—|
|correlated|0.4|32/0/0|5|2/5 (40.0%)|2/32 (6.2%)|22/32|118.1/317.6/457.2|27.2/13.1|
|correlated|0.5|32/0/0|5|1/5 (20.0%)|1/32 (3.1%)|22/32|193.7/343.2/480.9|45.2/30.4|
|two_sources|0.4|32/0/0|16|5/16 (31.2%)|5/32 (15.6%)|25/32|95.0/250.2/383.0|28.1/11.6|
|two_sources|0.5|32/0/0|13|4/13 (30.8%)|4/32 (12.5%)|26/32|100.3/240.9/365.4|51.2/31.1|
|background|0.4|32/0/0|0|0/0 (undefined)|0/32 (0.0%)|0/0|—/—/—|69.9/—|
|background|0.5|32/0/0|0|0/0 (undefined)|0/32 (0.0%)|0/0|—/—/—|82.9/—|
|independent_transport|0.4|32/0/0|13|4/13 (30.8%)|4/32 (12.5%)|28/32|57.6/259.1/357.1|35.3/6.2|
|independent_transport|0.5|32/0/0|13|3/13 (23.1%)|3/32 (9.4%)|29/32|80.0/311.7/473.2|36.8/7.3|

[All/accepted/rejected distributions and confidence intervals](WEATHER_BIAS_ACCEPTANCE.md) include p10/median/p90/max and mean; geographic area in m²/fraction, conditional mass, source Brier, warning/false-alarm/miss counts, Wilson95% intervals and runtime are in [final-summary.json](../evaluations/weather-bias/final-summary.json). A zero observed error rate has a nonzero upper interval bound;0/0 is undefined. Nominal90% conditional regions are not calibrated coverage. Background-only has no location truth; false source alarms are reported separately.

## Planner outcomes

All choices were locked before candidate/target outcomes were revealed. Each plan uses at most two permitted pollution instruments, costs≤250 units, and the same recorded-time weather/data. Ten random policies per world form a seed-paired comparator. All follow-up inversions use0.5 so the0.4 planner comparison isolates site choice. Existing reference readings are already observed inputs; no new weather instrument is given for free.0.4 does not support the new paired-reference conditioning, an explicitly labeled capability difference.

| Condition | Policy | Comparator | RMSE advantage mean [95% bootstrap] µg/m³ | Losses | Worst loss | MAP advantage mean m |
|---|---|---|---|---|---|---|
|direction_characterized|prediction_risk|random_mean|0.027 [-0.062,0.115]|4/8|0.124|8.8|
|direction_characterized|prediction_risk|spread|0.026 [-0.038,0.091]|2/8|0.115|6.5|
|direction_characterized|prediction_risk|wind|0.053 [-0.027,0.139]|4/8|0.108|2.2|
|direction_characterized|prediction_risk|baseline_0.4_planner|0.003 [-0.060,0.065]|4/8|0.124|0.0|
|direction_characterized|information|random_mean|-0.007 [-0.055,0.043]|5/8|0.098|7.1|
|direction_characterized|information|spread|-0.008 [-0.100,0.079]|4/8|0.247|4.8|
|direction_characterized|information|wind|0.019 [-0.012,0.058]|3/8|0.045|0.5|
|direction_characterized|information|baseline_0.4_planner|-0.031 [-0.100,0.024]|4/8|0.212|-1.7|
|direction_unknown|prediction_risk|random_mean|0.118 [-0.058,0.396]|4/8|0.124|20.2|
|direction_unknown|prediction_risk|spread|0.165 [-0.036,0.512]|2/8|0.126|20.7|
|direction_unknown|prediction_risk|wind|0.173 [-0.049,0.489]|4/8|0.128|-0.8|
|direction_unknown|prediction_risk|baseline_0.4_planner|-0.006 [-0.063,0.049]|3/8|0.123|0.5|
|direction_unknown|information|random_mean|0.112 [-0.058,0.389]|5/8|0.152|19.6|
|direction_unknown|information|spread|0.159 [-0.099,0.527]|3/8|0.302|20.2|
|direction_unknown|information|wind|0.168 [-0.064,0.482]|3/8|0.229|-1.4|
|direction_unknown|information|baseline_0.4_planner|-0.012 [-0.068,0.022]|1/8|0.197|0.0|
|unknown_nominal|prediction_risk|random_mean|0.107 [-0.001,0.243]|2/8|0.121|3.5|
|unknown_nominal|prediction_risk|spread|0.071 [-0.059,0.236]|2/8|0.254|2.2|
|unknown_nominal|prediction_risk|wind|0.089 [-0.027,0.240]|3/8|0.123|0.2|
|unknown_nominal|prediction_risk|baseline_0.4_planner|0.072 [0.013,0.139]|2/8|0.021|0.0|
|unknown_nominal|information|random_mean|0.075 [-0.055,0.235]|4/8|0.123|3.5|
|unknown_nominal|information|spread|0.039 [-0.115,0.224]|3/8|0.254|2.2|
|unknown_nominal|information|wind|0.057 [-0.044,0.202]|5/8|0.082|0.2|
|unknown_nominal|information|baseline_0.4_planner|0.040 [-0.012,0.096]|4/8|0.036|0.0|

### Actual resources used

Caps are equal; policies may choose fewer instruments or leave budget unused. This is a policy outcome, not hidden free data. Costs are synthetic units, not real deployment quotes.

| Policy | Plans | Mean cost (min–max) | One / two instruments |
|---|---|---|---|
|prediction_risk|24|198.8 (180–210)|0 / 24|
|information|24|188.3 (90–240)|3 / 21|
|baseline_0.4_planner|24|192.5 (90–220)|2 / 22|
|spread|24|200.0 (200–200)|0 / 24|
|wind|24|197.5 (190–230)|0 / 24|
|random|240|216.0 (190–240)|0 / 240|

### Supplementary control: old model uses observed reference weather

The primary legacy adapter cannot interpret comparison fields and retains primary station data. To separate that capability difference from denying available observations to the old model, an additional control feeds qualified observed reference readings directly into0.4. It was declared after the primary freeze, before inspecting planner outcomes; it changes no production/evaluation rule. It uses noisy observed readings, never true weather. See [supplement protocol](WEATHER_BIAS_REFERENCE_CONTROL.md) and [raw results](../evaluations/weather-bias/reference-control/results.json). Eight worlds; equal250cost/equipment2 caps, actual spending may differ. All downstream fits still use0.5.

| Comparator against0.4 reference-data planner | Mean RMSE advantage µg/m³ | Losses /8 | Mean MAP advantage m |
|---|---|---|---|
|prediction_risk|0.031|3/8|0.0|
|information|-0.003|2/8|-1.7|
|baseline_0.4_planner|0.028|2/8|0.0|
|spread|0.005|4/8|-6.5|
|wind|-0.022|3/8|-2.2|

Reference-only0.4 inference covers 7/8 sources; MAP median 49.5m, mean area 33.2% domain. This small control prevents attributing all comparison-enabled improvements to new inversion logic; it is not an independent field validation.

Intervals resample paired worlds5000times with RNG90311; eight worlds/condition give limited precision. Prediction improvement cannot establish localization improvement. Full per-plan errors, regions, costs, RMSE/density/interval scores and lock hashes remain in each final shard’s planning.jsonl. Paired coverage/area differences are in planner-paired-comparisons.json.

## Sensitivity, engineering and remaining limits

Development profiles and48 perturbation/oracle fits are in [sensitivity](../evaluations/weather-bias/sensitivity). Correct-weather oracles are diagnostic only. Several layouts retain broad or displaced alternatives even with true weather; same-wind repeats mostly leave≥75% area. Prior15° can miss a source retained by20°/30°, demonstrating prior dependence. No prior was tuned against final data.1° angular refinement, a requested10m cell target (the24-per-axis cap gives about15.4×18.3m cells here) and±5° coherent shifts are reported separately; stable arithmetic is not validated physics.

The protocol, root cause, equations, exact compatibility contract and commands are in [WEATHER_BIAS_IMPLEMENTATION.md](WEATHER_BIAS_IMPLEMENTATION.md). Old source and all failed preflight probes remain retained. The first resource probes exposed two temporary-array memory failures; exact bounded column calculation and algebraic reduction repaired them before the freeze. Resource results show retained shape, fitted-row limits, refusals and actual memory/time;10,000 loaded readings do not imply10,000 inverted rows.

Independent reference uncertainty/provenance claims remain user declared. A shared hidden reference/primary bias, wrong clock, spatially unrepresentative wind, unsupported transport, multiple sources, source outside the domain or prior tails can still defeat localization. Unknown weather is explicitly unknown. No universal “weather fixed” or organizational attribution readiness claim follows. Official NOAA measured-tracer requests failed proxy CONNECT403 again; [exact attempts](../evaluations/weather-bias/external-retry.json). Field validation remains unperformed.

### Engineering verification on the frozen release

115 pytest checks and eight Chromium workflows passed; the frontend production build/typecheck passed. Logs: pytest-release.log, playwright-final.log and frontend-build-complete.log under evaluations/weather-bias. These verify software behavior, not physical accuracy. The API stress probe retained all36 acknowledged writes among64 simultaneous requests (28 explicit429 responses), rejected malformed/oversized requests and recovered;500 CSV fuzz cases produced no unhandled error. See api-engineering.json.

Resource children each had60seconds and2GiB limits. Every row loaded10,000 readings plus10,000 weather rows,100sites and25anchors. Time/memory are this machine's observations, not a shared-service guarantee.

| Campaign | Compared weather | Fit limit / fitted | Outcome | Seconds | Peak MiB |
|---|---|---|---|---|---|
|False|False|128 / 128|ok|23.76|954.8|
|False|False|512 / 512|ok|44.46|1790.5|
|True|False|128 / 0|Inference limit 128 cannot retain all 240 sensor/window groups; increase the inference limit or split the investigation|1.40|211.8|
|True|False|512 / 0|Weather uncertainty exceeds the supported numerical workload for this study size. Reduce maximum fitted readings or supply appropriate independent wind comparisons; all raw readings are retained.|1.33|214.0|
|True|True|512 / 512|ok|24.04|1159.6|

The unknown-weather512-row campaign explicitly refuses excessive numerical workload;128-row campaigns cannot retain240sensor/window groups. These are retained capability limits. All child source hashes match the final freeze. Full records: [resources-release](../evaluations/weather-bias/resources-release/results.json).

[Standalone tradeoff figure](../evaluations/weather-bias/figures/weather-tradeoffs.png) ([PDF](../evaluations/weather-bias/figures/weather-tradeoffs.pdf), [SVG](../evaluations/weather-bias/figures/weather-tradeoffs.svg)) shows coverage, acceptance and accepted errors together, with Wilson intervals. Broad regions can restore coverage while reducing usefulness; acceptance alone is not success.
