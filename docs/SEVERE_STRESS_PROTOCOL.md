# Severe stress protocol UW-STRESS-2026-04

Declared before running this campaign. Model under test: **plume-weather-0.5.0**, published source at Git`66ca6709a3acdb4896373b98dfae6b2e34e3b208`. This is a challenge of the unchanged model, not model selection. A numerical/software pass cannot establish field accuracy. Previously inspected evaluations remain historical evidence, not new held-out cases.

## Scientific campaign

48new paired seed blocks6100000–6100047,20conditions each: **960inference attempts**. Two development/preflight seeds6101000–6101001 are disjoint. All generated cases, explicit refusals and crashes stay in the denominator. Reused seeds across conditions are paired, not960independent campaigns. No production parameter, uncertainty, threshold or support rule may be selected using these outcomes. Source/evaluator/protocol hashes are frozen before the challenge and checked afterward. Any subsequent scientific repair needs a new identifier, hypothesis and untouched evaluation.

The existing independently documented weather evaluator supplies synthetic physics, scalar/reference kernels, correlated fields and raw observations. The new harness deterministically replaces its final-layout table in memory with six continuously randomized monitor coordinates (x10–900m,y±215m), adds±10m jitter, and uses independently randomized four wind regimes about[202,246,294,338]° with±10° offsets. These generator changes are inputs, not production changes. Full raw Investigation and private evaluator truth are retained separately for every case. Existing source domain remains[-450,-80]×[-220,220]m, source strength18,000–36,000µg/s except weak/background families. Thus sources remain subgrid and new geometries/wind combinations differ from prior fixed tables. These are synthetic scenarios, not realistic-dataset substitutes.

The first14conditions are characterized_nominal, unknown_nominal, direction_unknown, direction_characterized, speed_bias, clock_lag, distant_station, spatial_winds, variable_weather, weak, correlated, two_sources, background, independent_transport. Their mechanisms/units/support are those documented in UW-WEATHER-2026-03; fresh seeds and continuously randomized layouts are used here. Existing final bias bands, clock-lag ranges and diffusion mismatch remain deliberately reproducible mechanism controls, not newly discovered physical regimes. Variable-weather is an85°recorded outlier, not a transient-puff simulator.

Six additional conditions clone the characterized control before mutation:

- **sensor_dropout:** remove M00/M02/M04 readings; three sensors remain across every period. No fabricated replacements.
- **sensor_bias:** add a seed-fixed15–35µg/m³ bias to M00 in every period. Other data/truth unchanged.
- **shared_reference_bias:** add the same seed-fixed32–55° error to primary and allegedly independent reference directions. This challenges an unverified independence/accuracy assertion; internal agreement cannot observe a shared hidden bias.
- **source_outside_domain:** replace source-domain anchors with the fixed rectangle[-680,-500]×[-220,220]m, outside the simulated source. Measurements remain unchanged. Evaluate whether a constrained model accepts a wrong location; no domain is chosen to enclose truth.
- **extreme_readings:** replace M00 concentrations with650µg/m³. Raw values/origins stay retained and current review/exclusion behavior is counted, not disabled.
- **shared_lineage:** give the reference the primary upstream ID and shift primary directions25–40°. Shared processing cannot count as independent calibration.

For the first12seeds per condition (240scheduled passive prediction evaluations), evaluate12unseen independent instruments at the final recorded timestamp using existing evaluator target outcomes. Targets are never fitted or used to select plans. Refusals remain unavailable, not assigned favorable errors. Record RMSE, exact-mixture log density,2048-Sobol90% interval coverage/width and no-data source-domain-centroid errors. No new acquisition/planner superiority claim is tested; previous planning intervals remain applicable. Per-condition sample sizes are48 for inference, at most12worlds for predictions;12target points within a world are not independent campaigns.

## Predeclared accuracy assessment

For characterized nominal controls, inspect conditional90% region coverage, acceptance, accepted geographic error, MAP median/p90/max, area and passive concentration predictions together. A useful research target is medianMAP≤50m, region coverage≥90%, and no accepted wrong regions. Report the source-location no-data centroid comparator, abstentions and broad regions; do not equate a broad covered region with precise localization. For broader reliability, require the one-sided/interval evidence to constrain accepted error: report two-sided Wilson95% upper bounds and whether they are≤5%. With few accepted cases even zero observed errors cannot support that bound. Do not declare extreme accuracy when this criterion is inconclusive or fails.

For every mismatch family, report accepted errors, warning-free geographic misses, source false alarms/misses and refusals with explicit denominators/Wilson95% intervals. Zero crashes is a separate engineering goal. A failed scientific criterion stays failed; raising rejection thresholds or dropping difficult cases is not a repair. No prespecified gate is licensed to infer real-world certification from synthetic data.

## Engineering stress

-100,000scalar kernel cases plus translations, rotations, strength/speed scaling, symmetry, support edges and independent information-oracle checks. Existing deterministic arithmetic seeds are reproduction/property checks, not fresh empirical campaigns; larger counts extend the prior sequence.
-200geographic placement instances (100small/100large), independent exhaustive tiny-case optimum and all-plan cost/equipment/permission constraints. No geographic utility optimum is evidence of source localization or field benefit.
-5,000seeded adversarial CSV cases with actual raw-preservation/count checks; retain unexpected exceptions and exact failed input. Explicit schema/parser refusals are valid outcomes, not crash-free accuracy evidence.
-Four isolated API overload/rollback/recovery rounds:64writes/32clients each, preserve every acknowledged write, reject malformed/oversized input. Rate-limited429responses are explicit refusals, not acknowledged writes. The existing500CSV fixtures repeat inside those rounds; report500unique repeated fixtures, not2,000unique cases.
-Resource probes reuse the declared10,000-reading/10,000-weather/100site/25anchor shapes under60s and2GiB per child, at128/512fit limits. Run after the scientific workers to avoid confounding CPU-saturated wall times. Loaded rows are not inverted rows. Keep all refusals, timeouts, memory failures and actual resource measurements.
-Run the full backend suite, production frontend build/typecheck and all Chromium workflows on isolated ports/storage. Test passes and warning counts remain separate from scientific outcomes.

All original files/private investigations stay preserved. Generated rows are explicitly synthetic. No measured tracer validation, deployment or outreach is included. Official-source network publication remains an independent pending prerequisite and is not assumed completed by this stress request.
