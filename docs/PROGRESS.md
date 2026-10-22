# Current handoff — engine 0.9 feasibility repair complete

## Source-strength/location investigation (2026-10-20)

Investigated all six release-prior-sensitive v0.9 ladder cases before making
any additional support change. The diagnosis and per-case evidence are in
[ENGINE_V09_STRENGTH_LOCATION_DIAGNOSIS.md](ENGINE_V09_STRENGTH_LOCATION_DIAGNOSIS.md);
raw inputs/maps/reference outputs are under
`evaluations/engine-v09/strength-location-final2/`. The cases show broad
profile-likelihood ridges, with release/background and weather/sensor mismatch
selecting among plausible locations. An independent off-grid control recovers
truth within3.4m when Q/background are known, while the default marginalized
posterior is34m off because its HalfNormal Q scale is30,000µg/s versus a
500,000µg/s release. Factors[0.1,1,10] multiply that prior scale to3,000,
30,000,300,000µg/s. No production arithmetic defect was demonstrated; no
production inference, prior, support gate or acceptance rule changed.

The diagnostic script corrected two evaluator mistakes: stale source truth
after the ladder replaced the source, and shifted anchors in the ideal control.
Earlier exploratory outputs remain preserved and are not evidence. Findings
are synthetic and do not establish field accuracy.

The Sol brief's remaining reporting gap is now closed without rerunning the
frozen campaigns: `scripts/sol_feasibility_assessment_v09.py` creates the
append-only `evaluations/engine-v09/sol-assessment/assessment.json` with the
v0.8 224/256 metric definition, explicit prior/domain-center comparisons,
source-free/mismatch denominators, scientific call path and Outcome C. The
primary feasibility report now includes those results and the v0.9 off-grid
reference controls. No further production arithmetic defect was demonstrated;
therefore this reporting completion changes no posterior or support policy.
The v0.9 sensitivity regression passes (3 tests), both reporting scripts
compile, and `git diff --check` is clean.

The Sol feasibility brief is implemented as **plume-robust-0.9.0** under
protocol **UW-ENGINE-2026-09**. Single-window and campaign source cells now use
four-node tensor quadrature. Every fit reports a fixed-observation release-scale
sensitivity over `[0.1, 1.0, 10.0]`; a mean shift over 100 m or cell total
variation over 0.25 withholds `source_supported` and is propagated through
`observability`. Focused v0.9 tests cover quadrature, finite/material
sensitivity, the public gate, and cache clearing.

The compact labeled ladder is in `evaluations/engine-v09/ladder/` and is
reproduced by `scripts/feasibility_ladder_v09.py`. It ran 10 synthetic cases
with no fit failures, 0 public source-supported results and 6 prior-sensitivity
blocks. An independent scalar plume calculation matched the production
primitive exactly for its checked point. Strong controls remained ambiguous or
prior-sensitive; the source-free case remained unlocalized; the out-of-domain
case had a 1,396.5 m diagnostic mean error. These are synthetic mechanism
checks, not field validation. The feasibility report selects product outcome
**C** for current practical inputs; any monitoring-design direction requires a
separate equal-budget follow-up study with fresh cases.

Run focused checks with
`PYTHONPATH=backend OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python
-m pytest -q backend/tests/test_strength_prior_sensitivity_v09.py` and run the
full backend suite before release. The current full suite passes **231 tests**
(one existing Starlette/httpx deprecation warning). Do not rerun the frozen
v0.8 campaign or claim measured accuracy, calibration, attribution or
operational readiness.

# Current handoff — engine0.8 implementation and full synthetic evaluation

Candidate **plume-robust-0.8.0**, protocol **UW-ENGINE-2026-08**, adds nested deterministic source-cell/weather quadrature convergence checks and connected-component summaries for the conditional 90% source region. The frozen v0.7.1 workspace baseline and candidate were paired on identical inputs. Development/calibration/final contain128/128/256 worlds per engine (512 paired worlds total); every pair hash matches, with zero crashes or refusals. Candidate convergence passed512/512.

Untouched final256: candidate status was1 source-supported,177 ambiguous,78 model-mismatch; baseline had2/256 source-supported. Candidate median mean/mode errors were91.0m/484.4m, with p90 mean error184.4m and maximum257.2m. The sole supported case had165.2m posterior-mean error (0/1 within50m). Conditional90% regions covered the correct source count in224/256 cases while median area was89.1% of the supported domain; all32 nominal regions covered truth but remained broad. None of32 two-source regions covered both sources. Heavy-tail was model-mismatch32/32; sensor drift24/32. Median held-out concentration RMSE was2.31µg/m³ across768 correlated checks. Candidate median runtime3.49s versus1.66s for v0.7.1. Numerical stabilization did not improve localization; the50m target fails. The families contain only source-present worlds, so background false-alarm rate is unmeasured.

All detailed outcomes and limits are in [v0.8 implementation](ENGINE_V08_IMPLEMENTATION.md), [protocol](ENGINE_V08_PROTOCOL.md), and append-only artifacts under `evaluations/engine-v08/`. Reproduce with the three distinct split commands in `ENGINE_V08_PROTOCOL.md`, using new output directories. Candidate source/configuration hashes are in `source-freeze.json` and split metadata. The full backend suite passes: 228 tests. A regression test now clears the analysis cache around its monkeypatched fit so an earlier identical fixture result cannot bypass the fail-closed path. No measured-data validation, field calibration, source responsibility, regulatory attribution, or operational readiness is established. Later GIS/frontend work should preserve conditional polygons, posterior mean vs density mode, source weight, evidence status, numerical convergence/refusal, weather provenance, and adequacy warnings as distinct outputs.

# Historical handoff — engine0.7 final synthetic evaluation and numerical repair

## Engine 0.7 final evidence and post-final repair

The locked **UW-ENGINE-2026-07A** evaluation is complete on the frozen
`plume-robust-0.7.1` source. Development and calibration each contain 128
synthetic fits; the untouched final split contains 256. The pre-repair final
run had 255 successful serializations and one visible crash (`8310020`,
`sensor_drift`) because the bounded two-source NNLS diagnostic returned
`[nan, inf]`. The posterior itself was not the source of the failure.

The diagnostic now rejects non-finite candidate pair fits, records the count as
`invalid_pair_fits`, marks `diagnostic_unavailable`, and blocks
`source_supported` with a structured warning. The post-final engineering
confirmation over the same 256 locked worlds has **256/256 successful finite
results and zero crashes**. This is a numerical robustness correction after
the scientific final run; the original pre-repair result directory remains
preserved and the post-repair confirmation is not a new independent accuracy
sample.

Final post-repair observable outcomes: 167 ambiguous, 86 model-mismatch and 3
`source_supported` rows. All 32 nominal, 32 humidity-response, 32 changing-
release, 32 two-source and 32 weather-error worlds remained ambiguous. Sensor
drift produced 29 model-mismatch rows and 29 drift/time-varying-release flags;
spatial-background produced 25 model-mismatch rows, 4 ambiguous rows and 3
conditional source-supported rows; all 32 heavy-tail worlds were
model-mismatch. Two sensor-drift rows had non-finite competing-source fits and
were explicitly withheld from source support after the repair. No material
two-source pair was accepted. The three spatial-background source-supported
regions contained the simulated source but had posterior-mean errors of about
172–197 m; this is a retained precision limitation, not field evidence.

These results remain synthetic and conditional. They do not establish field
accuracy, calibration, source responsibility, regulatory attribution or
organizational reliability. See `evaluations/engine-v07/` and the protocol and
implementation documents for exact seeds, hashes and denominators.

The standalone review deliverables are [the code-review findings](engine-code-review.md)
and [the candidate-results report](engine-candidate-results.md). A compact paired
development comparison on two fresh seeds × eight families is retained under
`evaluations/engine-v07/matched-development`: both archived 0.6 and current 0.7
fit 16/16 worlds, 90% regions cover 16/16, and median posterior-mean errors are
97.5 m and 90.8 m respectively. No result was resolved; this small comparison
was not used for tuning and does not establish a general improvement.

## Engine 0.7 candidate and implementation record

The current workspace now contains an unvalidated candidate **plume-robust-0.7.1**
under **UW-ENGINE-2026-07A**. It adds explicit humidity-response covariance,
bounded two-source profiling under a shared persistent weather offset, a
two-half release-variation adequacy profile, and residual checks for drift,
changing release, spatial background and heavy tails. Material alternatives
withhold the `source_supported` label, and an unavailable adequacy diagnostic
is an explicit refusal rather than an implicit pass. This is a new scientific
candidate; its locked synthetic evaluation and post-final numerical
confirmation are recorded above. No field accuracy claim exists. Read [the
protocol](ENGINE_V07_PROTOCOL.md) and [implementation](ENGINE_V07_IMPLEMENTATION.md).
The published 0.6 source, results and negative findings remain intact in their
versioned artifacts.

Everything after the post-release patch heading below describes the completed
0.6 release and is retained as historical handoff context.

## Post-release integrity patch in the current workspace

After the published `356beac` checkpoint, a narrow engineering patch was applied
without changing the scientific configuration or any frozen evaluation input.
Measurement duplicates now disagree when any retained metadata differs (flags,
humidity, temperature, origin or uncertainty), while ignoring the importer's
row-position-only `duplicate` marker. Duplicate weather rows must
agree on all matching, uncertainty, lineage and provenance fields. This prevents
import order from selecting which metadata reaches the fit. Numerical
factorization failures are also returned as structured analysis refusals by the
orchestrator. The original release evidence remains immutable; the four-file
post-release hash record is [here](../evaluations/engine-v06/post-release-integrity.json).
That verifier describes the 0.6 checkpoint and is expected to reject the changed
current 0.7 source; use `evaluations/engine-v07/source-freeze.json` for the current
candidate identity.

The user's final two changes are complete: bounded grouped/chunked nuisance-profile GLS and a quadratic predictive-target allocation guard. They were applied after scientific/supplementary runs, with exact two-file source hashes, AST scope proof and unchanged scientific configuration. Independent constrained-GLS checks and exact frozen/current posterior/prediction comparisons pass. Read [hardening details](ENGINE_V06_HARDENING.md).

Current scientific model **plume-robust-0.6.0**, protocol **UW-ENGINE-2026-06**. Read [primary results](ENGINE_V06_RESULTS.md), [implementation](ENGINE_V06_IMPLEMENTATION.md), [supplementary observability](ENGINE_V06_OBSERVABILITY_RESULTS.md) and [LLM export prompt](UPWIND_LLM_EXPORT_PROMPT.md). All runs are finished; do not resume old watchers or duplicate exclusive output directories. Publication is authorized and the completed release is published to GitHub main; use `git log -1` / `git ls-remote origin refs/heads/main` for the final revision.

Primary960attempts: each engine432fits+48explicit weather refusals, zero inference crashes/numeric failures/unexpected refusals. Accepted/wrong old15/3→new12/1. Nominal mean-point median137.2m→141.1m, mode166.6m→179.9m: **both50m targets fail**. Primary common-bias accepted errors0→0does not demonstrate the strict target gain. Broader regions/lower acceptance are not a precision breakthrough. Supplementary64attempts are separately reported: shared-bias accepted wrong3→1, but a wrong accepted region remains; nominal median mean28.7→35.9m. Preserve negative results and denominators.

Calibration128, original36, planning48 and supplementary64 attempts are retained separately. Existing engineering batteries701,017numerical/900placement/5,000CSV/fourAPI rounds passed. Final209backend tests and8Chromium workflows pass; frontend build/typecheck passes. The final isolated resource outcomes, original memory failure, explicit workload refusals and capability regression remain in ENGINE_V06_HARDENING.md and evaluations/engine-v06. An accidentally concurrent resource preflight was interrupted and excluded, then replaced by the isolated repeat. No field measurements were validated.

Reproduce readiness with `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m pytest -q`, frontend `npm run build` / `npm run test:e2e`. Verify release evidence with `.venv/bin/python scripts/verify_v06.py`; exact hardening scope with `.venv/bin/python scripts/hardening_v06.py`. Use historical source archives for older exact-source identity checks. Source checkpoint82bb5fe preserves scientific candidate; post-campaign-hardening.json records the two subsequent engineering changes. Original scientific49-file freeze remains untouched.

All development7100000–3, calibration7200000–7, final7300000–23, observability7700000–15 and prior retained seeds are inspected: reproduction/development only. Future scientific changes need new protocol/model and untouched locked evaluation. Measured validation remains blocked by primary access/provenance/units compatibility; official access stillCONNECT403. No organizational reliability, field calibration, regulatory attribution, deployment or outreach is claimed. Earlier working notes are retained in evaluations/engine-v06/working-notes-pre-publication.md; the following sections are historical0.5 handoffs.

---

# Current handoff — severe stress complete; overall precision target failed

Completed **UW-STRESS-2026-04/04C**, scientific model **plume-weather-0.5.0**. Read [SEVERE_STRESS_RESULTS.md](SEVERE_STRESS_RESULTS.md), the [main protocol](SEVERE_STRESS_PROTOCOL.md), [nominal supplement](STRESS_NOMINAL_CONFIRMATION.md) and [reporting methods](STRESS_REPORTING_METHODS.md). The user requested extensive stress testing and extreme accuracy. The engineering repair/checks are complete; **extreme accuracy and organizational attribution reliability are not demonstrated**. Failures remain retained, not tuned away.

**1,440 fresh inference attempts**:960main cases across48paired seed blocks×20conditions (864fit/96weather refusals) plus480characterized-nominal confirmation worlds (480fit). **Zero inference/prediction crashes or numeric failures**.216passive unseen-sensor scores out of240scheduled;24unsupported-weather cases remain unavailable. Main seeds6100000–6100047; nominal6400000–6400479; disjoint preflight6101000–1. Source/evaluator/configuration unchanged during every scientific run; exact45-file source archive/freeze retained. All seeds are now inspected; future selection requires new untouched cases.

Nominal:82/480accepted (17.1%), zero accepted region misses (Wilson95% upper4.475%); region coverage477/480 (99.4%) but mean region area63.0%domain. Median MAP117.3m overall versus no-data centroid163.4m; accepted median35.2m/p90107.7m. Overall50mmedian precision target **FAILS**; coverage/error-bound targets pass only under this compatible synthetic control with correct independent-weather assumptions. Do not equate broad-region coverage with precise or field-validated localization.

Main17accepted geographic errors: correlated1/4accepted, independenttransport4/17, sharedlineage1/8, hiddencommonreferencebias6/6, sourceoutsidedomain4/4, twosources1/9. All per-condition denominators/Wilson intervals, warning-free misses, distributions, errors/areas/Brier and passive concentration comparators are retained. First hidden-common-bias error repeats exactly at175.2m/14.9%area with no warnings; removing references still accepts a wrong177.6mpoint. Evaluator-only bias correction covers truth but point remains86.5moff. **Oracle diagnostic is not a production fix or weather calibration**.

Engineering:701,017numerical checks,900placement checks/200instances,5,000new seededCSVcases (2,814explicit refusals,2,186parsed,zero unexpected errors), four64request/32client API rounds (78acked writes all retained). These are software checks, not real accuracy samples. Five fresh60s/2GiB resource children: single12826.39s/966.5MiB; single51250.52s/1796.8MiB; characterized512campaign27.88s/1160.3MiB;128campaign/unknown512campaign explicitly refuse supported workload.10kreadings+10kweather loaded is not10kinverted rows.

A separate probe found deepJSON ->500 and nonstandardNaN metadata ->200/silentnull. **After all scientific/resource runs ended**, only backend/upwind/api.py among frozen paths was repaired to reject excessive nesting/nonfinite JSON with422before persistence, preserving valid raw request bytes and CSV strings. No inference/prior/support/planner change. [API repair](API_REQUEST_HARDENING.md), original failing probes, prototype and before/after SHA/evidence retained. Original suite168pass; final**181backend tests and8Chromium workflows pass**, frontend build/typecheck passes.13new API regressions and fresh post-repair64request overload (17acked/47explicit429, all acked retained) pass. Existing Starlette/httpx deprecation and frontend bundle warnings remain.

`evaluations/severe-stress/verification.json` verifies source snapshots, all counts/raw synthetic inputs, configurations, report/figure manifests and the sole allowed post-campaign API hash difference. PNG/SVG/PDF figure visually inspected. An initial figure-only endpoint-roundoff failure is retained in figure-preflight; only errorbar rendering was corrected, no statistical/data change. Runtime logs include initial contention and explicit worker suspension; only fresh resource children describe isolated timings. Scheduler label mapping was corrected from actual argv, with original/corrected events preserved. All benchmark/controller sessions ended; do not resume old PIDs in [the historical working log](STRESS_RUN_PROGRESS.md).

Commands: `.venv/bin/python scripts/report_severe_stress.py`, `.venv/bin/python scripts/verify_severe_stress.py`. Plot generation refuses existing figures. Historical exact weather source: `.venv/bin/python scripts/verify_weather_release.py --source evaluations/weather-bias/frozen-source`; default current-tree identity intentionally differs after the API repair. Old manifests refer to bytes at their original Git commits; do not rehash history into current claims. The continuation prompt is updated. Final Git publication is authorized; inspect git log/remote for actual published commit.

Measured primary data access remains pending (unchanged network draft/base version at last read); no measured field validation, deployment, outreach or government certification occurred. A new scientific hypothesis/protocol, validated independent observations and untouched evaluation are required for further accuracy claims.

---

# Historical handoffs

# Current handoff — measured-data readiness audit complete; primary access pending

2026-10-18 (America/New_York): user explicitly selected measured-data validation. Inspected four pinned public repositories via permitted GitHub routes and audited a secondary Prairie Grass modelling workbook. Read [MEASURED_READINESS_AUDIT.md](MEASURED_READINESS_AUDIT.md), `evaluations/measured-readiness/access-and-sources.json` and `prairie-candidate.json`. No measured accuracy fit was performed. The workbook contains74purported observation constants plus74modelled constants. Four sheets label53observations in g/m³;40would exceed the current500µg/m³ exclusion/review threshold. The labelled50.9g/s release is≈1697times the30,000µg/s strength-prior scale. Missing primary lineage, full units, wind/time/frame documentation, terms and incompatible scientific scope prevent treating it as a benchmark. Keep experiment21 development-used; never use cached modelled columns as observations. Raw workbook stays ignored locally.

New reproducible auditor: `scripts/audit_prairie_candidate.py --checkout CLONE --out NEW.json`, pinned revision`6fd4a0892481e25171f3c4c6efe3114448bd4674`. It reads Git objects/OOXML without executing upstream code, formulas or external connections, outputs aggregate metadata only and refuses existing audit destinations.11constructed audit tests pass; **full backend162pass** (`evaluations/measured-readiness/pytest-full.log`). RuffF401/F821 and whitespace checks pass. No frontend changes. Frozen0.5 verification still passes; no scientific file, prior, quality rule, threshold, planner or original outcome changed.

**External action required:** live NOAA, Aarhus and HARMO requests remain proxy CONNECT403. The existing saved configuration already listed NOAA/EPA; runtime access remains unestablished. Saved a draft adding`envs.au.dk` and`www.harmo.org` while preserving all eight existing custom domains and platform presets. The configuration tool returned`requires_publish: true`: review/save in environment settings, then publish the environment. The new draft is not applied to the live proxy; do not retry unchanged requests in a loop or claim fresh-task reachability. After publication, inspect actual official links/terms, acquire primary files and assess compatibility before any fit. No token, TLS bypass or alternate IP route is justified. No deployment, outreach or raw observation publication occurred.

The intake artifact manifest belongs to Git commit`7ffa8a4610e802f78869acae525025943203256d`; its documentation paths are historical bytes at that commit, not immutable current documentation. Its README explains reproduction scope. Current export prompt includes this audit and pending prerequisite. Inspect `git log -1` for the latest published continuation commit.

---

# Completed handoff — measured-data intake repair

2026-10-18 (America/New_York): continued from the pasted handoff. Default next target was measured-data validation; NOAA, alternative catalogs/search and EPA archive access remain proxy CONNECT403. Exact attempts are in `evaluations/aqs-intake/external-access.json`. No new observations were acquired; no measured accuracy or authenticity claim follows.

Found and fixed destructive behavior in `scripts/acquire_aqs.py`: the old adapter deleted a destination before validation, appended partial results directly and could erase a good export on CLI failure. `aqs-intake-1.0.0` stages complete conversions, refuses existing archive/CSV/provenance paths, uses exclusive publication, handles competing writers without mixed pairs, rolls back its own sidecar on publication failure and records both archive/output hashes. It strictly checks parameter88101/hourly duration/WGS84/local-condition units, date/time, finite values, supported coordinates, identifiers and exact CSV record widths. Qualifiers, method details, negative/extreme values and UTC/source metadata survive. A crash between two-file publication steps can leave an orphan sidecar; both files plus a matching hash are required. No power-loss durability claim.

**151 backend tests pass**, including36 new contract/fault checks and the updated existing constructed AQS importer round trip (37 focused checks). Full log: `evaluations/aqs-intake/pytest.log`. RuffF401/F821 and diff whitespace checks pass. No frontend changes/build/browser rerun needed. `scripts/verify_weather_release.py` passes: the43 frozen scientific files, source snapshots, original896source/360followup results and report/figure hashes are unchanged. This is an intake repair, not a new scientific model; **plume-weather-0.5.0** and all its known failures remain current.

Read [MEASURED_DATA_VALIDATION.md](MEASURED_DATA_VALIDATION.md) for the exact tested contract, safe commands, completion checks and next external prerequisite. Actual official archive compatibility/terms still require inspection; constructed fixtures are not field observations. The continuation prompt includes this updated state. Git publication remains authorized by the user's prior request and continuation; inspect the current commit/remote rather than relying on historical commit/PID notes below. No deployment, outreach or raw observation publication occurred.

---

# Completed handoff — weather repair

2026-10-18 (America/New_York): completed **plume-weather-0.5.0**, protocol **UW-WEATHER-2026-03**. The user authorized publishing this project to GitHub and requested an LLM export prompt. Read [the standalone continuation prompt](UPWIND_LLM_EXPORT_PROMPT.md), [results](WEATHER_BIAS_RESULTS.md), [acceptance distributions](WEATHER_BIAS_ACCEPTANCE.md) and [implementation](WEATHER_BIAS_IMPLEMENTATION.md). Sections below are chronological historical notes, including obsolete process IDs and earlier statements that work was unpublished.

Final evaluation is complete: **896 old/new source outcomes across448 condition-worlds and32 paired seed blocks**, **360 follow-up fits**, **zero crashes**. All four shards have224 source outcomes/90followups, identical frozen source hashes before/after, and take1260–1265seconds each on this machine. All follow-up plans obey cost≤250/equipment≤2. Source-freeze SHA256: `3058ca0666caa1c6033d078e0740477e73d59a89205b56a33360acc2ef7f8253`. `evaluations/weather-bias/verification.json` verifies43 frozen files,62 baseline snapshot files,43 exact calibration source files,84 final archived files, all report/figure hashes and counts.

Fresh direction-bias coverage improves from10/32 to30/32 (unknown station bias) or31/32 (independent comparisons); new accepted wrong counts are0/9 and0/10 versus old7/7. This is a conditional synthetic improvement, not demonstrated field calibration. Spatial mismatch still yields4wrong among10accepted, correlated error1/5, two sources4/13 and independent transport3/13. Calibration already contains direction/clock errors as well; do not claim they are solved because this final sample had none accepted. Wider unknown-weather regions and lower acceptance/point accuracy on compatible data are reported. All six primary planner-versus-random95% paired intervals cross zero; no general placement superiority. The supplementary observed-reference0.4 control and developmental sensitivity/profiles are complete and retained. No final outcome motivated a scientific change.

Engineering: **115pytest checks,8Chromium workflows and production frontend build/typecheck pass**. Resource children stayed within60s/2GiB; largest successful512-row fit44.46s/1790.5MiB.10,000 loaded rows are not10,000 fitted rows. Unsupported campaigns explicitly refuse. API acknowledged-write preservation, overload recovery and500CSV fuzz checks pass. All earlier failed preflights remain retained. The standalone tradeoff figure was visually inspected; PNG/SVG/PDF plus hashes are retained.

All final seeds are now inspected. New scientific selection requires a fresh protocol/model version and held-out conditions. Official NOAA requests remain CONNECT403; no compatible measured controlled-release validation or operational attribution certification exists. No deployment or outreach occurred. Private investigations/dependencies remain ignored in `.local`, `.env`, `.venv` and node_modules. Normal local API/Vite processes may still exist on8000/5173; verify and restart if needed, never rely on historical PIDs.

Rebuild and verify reports with `.venv/bin/python scripts/report_weather_bias.py` and `.venv/bin/python scripts/verify_weather_release.py`. Figures refuse overwriting their destination. Full commands, architecture, invariants and next work are in the continuation prompt. Git publication is the final step of this task; inspect `git log -1` and `git ls-remote origin refs/heads/main` for the actual published commit rather than treating old unborn-checkout notes as current.

---

# Durable progress — weather-bias repair in progress

2026-10-18: implementing the latest weather-bias attachment under fresh protocol [UW-WEATHER-2026-03](WEATHER_BIAS_PROTOCOL.md). Current candidate **plume-weather-0.5.0**; not yet validated. Preserved exact0.4 source in `evaluations/weather-bias/baseline-source` and reproduced all40 biased-weather outcomes, including all18 accepted wrong regions, exactly. Detailed raw diagnostics are in `evaluations/weather-bias/reproduced`. Baseline99tests pass. New numerical/reference/migration checks:43pass. Repair separates unknown persistent station bias from declared short-period uncertainty, conditions only on explicit independent paired weather readings with non-averaging systematic floors, and propagates the joint source/weather mixture. UI, fresh evaluation, stress limits and final documentation remain in progress. No final0.5 result or organizational readiness claim exists yet. Preserve old results below as historical evidence.

# Historical research0.4 implementation and evaluation

2026-10-18: completed the research-breakthrough implementation, independent comparisons, severe stress probes, documentation and product integration. The requested organizational attribution reliability is **not demonstrated**; the implementation/evaluation is complete with that failed capability claim explicitly reported. Current scientific model **plume-campaign-0.4.0**, protocol **UW-RESEARCH-2026-02**. The model remains research-only: calibration already shows missed confidently wrong weather/transport cases; do not promise operational attribution or field validation.

## Current implementation and verification

- Explicit2–6 independently steady campaign periods, fixed-location/constant-Q assertion, per-window background/trend, persistent instrument bias and absolute-time covariance. Declared met uncertainty/provenance and release/receptor heights. No transition/puff or multi-source inversion.
- Four-node area integration for campaigns; exact Q/speed collapse (unchanged likelihood, fewer solves). Exact positive-strength predictive draws/marginal density; joint held-sensor/period contrasts with budgets/checked counts. Global free-nuisance profile in UI/HTML. Optional deterministic Bayes-linear prediction objective; old information/coverage/baselines preserved.
- Corrected large diagnostic-budget refusal (>24sensors), valid tiny-speed-fraction component-key collisions, target-instrument-ID collision, and historical midpoint metadata text. No physics/threshold change after calibration. Original failed tests/probes/preflight runs preserved.
- **99pytest tests pass**, seven Chromium workflows pass (`playwright-final.log`), frontend build/typecheck and RuffF401/F821 pass. UI has a synthetic campaign, direct Scenarios analysis, explicit period/met/height controls and compact map site IDs/full-name accessible selection.
- Fresh 60s/2GiB children in `resources-final`: single128~10.28s/326MiB, single512~11.01s/591MiB, campaign512~12.51s/1509MiB with48,385components;10,000readings+10,000met/100sites/25anchors loaded,512fitted. Default128 explicitly refuses240sensor×period groups. Not10k-row inversion or shared-deployment SLA.
- Live isolated final API:64writes/32clients,5accepted59explicit429, all5reopened;16campaign analyses4accepted12explicit429; malformed/boolean/>10krows422 and8MB413, recovery200. `api-live-final/server-metadata.json` records actual isolated storage `.local/research-api-final` (probe's storage string is an inherited descriptive label).

## Completed evidence

-0.3 snapshot113files under `evaluations/research/baseline-source`, manifest; exact800inference/864follow-up/108perturbation reproduction excluding timings.
- Corrected Stage1 oracle diagnoses, bounded dense2-source reference at50/25/12.5/6.25m with independent scipy.nnls comparisons; no measured-data claims. Original grid/background auxiliary corrections preserved.
- Development144worlds/288old-new results/400follow-ups, zero crashes; development source drift explicitly retained (formatting/evaluator additions during development).12-seed material ablations, noiseless20/10/5m control,480-row selected64/128/full480 comparison and perturbations complete.
-400original previously inspected development worlds/800old-new outcomes, zero crashes, frozen prior-source hashes. Original single-window source performance essentially unchanged; new capability requires new campaign data.
- Calibration24seeds×12conditions:576old-new outcomes, no planner tuning, zero crashes. Full confirmation after edge/metadata fixes reproduces all576outputs exactly excluding timings and matches final source freeze (`calibration-confirmation/comparison.json`). Fixed acceptance rule retained; no calibration transform fitted.
- Final perturbations complete224records, unchanged frozen hashes. Grid source fits valid; grid plan-overlap was cached under a diagnostic CONFIG mutation. `grid-plan-check` clears caches and supplies corrected fresh plan-overlap across dev/cal/final without production changes; report must use it, not original grid10m overlap.
- Official NOAA DATEM/Sagebrush HTTPS retries CONNECT403; no measured controlled-release validation. Actual inspected references/hash in `inspected-reference.json`; older pinned research audit remains applicable.

## Final results and capability judgment

Frozen final `evaluations/research/final`: **480condition-worlds across40paired seed blocks**,960old/new outcomes (current440fits40weather refusals; prior0.3 fits40single-window cases and refuses440campaign inputs), **1200actual follow-up refits**, **zero crashes**,1129.73seconds. Every final hash before/after matches `final-source-freeze.json` and current production. All follow-up budgets/equipment checks pass. Final perturbations224records; baseline113files preserved. `verification.json` and report/figure manifests verify current artifacts/links.

Supported compatible campaign: medianMAP22.9m, p90159.0m, max354.0m; no-data centroid median164.7m. Conditional region covers38/40, meanarea26.9%domain; rule accepts25/40 and2accepted regions miss. Same-wind repetition medianMAP160.3m/area61.1%. Original single-window medianconditionalmean86.7m almost equals no-data centroid86.6m, area84.9%, accepts0/40: no recovered missing information.

Failures retained: weak27/40coverage and40/40presence misses; two-source23/40primarycoverage/15misses among30accepted, one warning; changing release32/40coverage/7misses among20accepted, one warning; biased met6/40coverage/**all18accepted miss, zero warnings**; correlated26/40coverage/27warnings/3of9accepted miss. Boundary40/40coverage butarea46.9%,6accepted; independent transverse diffusion37/40coverage/3of27accepted miss. These are conditional synthetic outputs, never responsibility findings.

Prediction-risk mean realized RMSE advantage vs20random plans,12paired worlds per condition: original−.011µg/m³95%CI[−.096,.068], weak−.013[−.057,.030], informative+.199[−.050,.637], biased+.231[.019,.593]. Only one interval excludeszero, losses remain2–7/12worlds; no general superiority/localization/field-benefit claim. Source localization, concentration prediction, recordkeeping and deployment have separate readiness judgments.

## Deliverables and commands

- [Research results and capability decision](RESEARCH_RESULTS.md), including all condition/planner tables and standalone plots.
- [Accepted/rejected distributions](RESEARCH_ACCEPTANCE.md), raw reliability/calibration-tradeoff JSON.
- [Root-cause diagnosis](RESEARCH_ROOT_CAUSES.md), including rejected rank-count hypothesis/corrected7-monitor inspection.
- [Equations, changes and owner handover](RESEARCH_IMPLEMENTATION.md), [science meaning](SCIENCE.md), [reproduction](RESEARCH_REPRODUCTION.md).
- `evaluations/research/verification.json`, `implementation-manifest.json`, `report-manifest.json`, `final/figures.json` and raw experiments. Three visually inspected figures each exportedPNG/SVG/PDF.

Reports/figures derive only from retained raw outputs:

```sh
.venv/bin/python scripts/report_research.py
# Figures refuse an existing destination; preserve existing figures on repeat:
MPLCONFIGDIR=.local/mplconfig .venv/bin/python scripts/plot_research.py
```

The final set is now inspected and cannot be an untouched test for new model selection. Preserve every original failure, interrupted preflight, correction and current result. No final result motivated a production change. Further source-prior/physics/threshold/acquisition changes need a fresh protocol and held-out conditions. Field validity remains blocked by missing compatible measured controlled-release data; NOAACONNECT403 is documented. The scientifically justified next work is independent met/transport validation and prospective measurement outcomes, not claiming government readiness from synthetic success.

Normal current-code development service remains session **13186**, API PID **71468**, ports8000/5173, private loopback; health confirms0.4. The isolated API probe on8002 is stopped. Browser tests own8001/5174. No npm ci during live build/tests. No Git commit/push/deploy/outreach: inherited checkout remains untracked/unborn; preserve user investigations and all artifacts. No new subagents spawned. Historical section below is retained0.3 context, not current performance.

## Historical completed 0.3 overhaul

Current scientific model: **plume-mixture-0.3.0**. Application package remains 0.1.0. The uploaded engine-overhaul request was implemented and evaluated. Work remains local and uncommitted; no GitHub push, deployment, data publication or outreach was performed. Preserve `.local` investigations and this existing checkout.

## Read first

- [ENGINE_RESULTS.md](ENGINE_RESULTS.md): implementation, final before/after results, resource limits, failures, product judgment and commands.
- [ENGINE_CHALLENGE_RESULTS.md](ENGINE_CHALLENGE_RESULTS.md): full independent condition tables, uncertainty, planner outcomes and provenance.
- [ENGINE_AUDIT.md](ENGINE_AUDIT.md): exactly reproduced baseline, equations, transformations and ranked causes.
- [SCIENCE.md](SCIENCE.md), [ENGINE_IMPLEMENTATION.md](ENGINE_IMPLEMENTATION.md): actual model, approximations and code review map.
- [ENGINE_EVALUATION_PROTOCOL.md](ENGINE_EVALUATION_PROTOCOL.md): frozen splits, independent transport, metrics and truth separation.

## Implemented

`inference.py` compares background-only with one release, analytically integrates positive strength/background/trend, integrates coherent uncertain wind, uses continuous area-weighted source cells, conditions predictive moments on history, and screens withheld sensor blocks. `design.py` estimates predictive-mixture information about background versus coarse source regions. `engine.py` handles common feasibility, exact/heuristic search, canonical ordering, the timestamp/instrument update contract and research-only status. `legacy.py` preserves the previous model.

Quality selection now has configurable 40–512 row limits (default 128), rare/extreme/time anchors and seeded strata. Loaded, excluded, usable and fitted counts are separate. UI/HTML show domain anchors, conditional regions, ambiguity/mismatch, counts, sampling controls and evidence limits, while handling null/legacy results. No landing-page redesign or new runtime scientific dependency.

## Verified evidence

- Immutable baseline source/manifest under `evaluations/overhaul/baseline-*`; all 640 source and 3,680 follow-up outcomes reproduced exactly excluding timings. Baseline: 72,167 engineering checks and 34 pytest tests.
- Current code: **81 pytest tests**, **six Chromium workflows**, production build/typecheck and Ruff F401/F821 pass. `pytest-final.xml`, `api-current.json` retain results. API 64 writes/32 clients: 13 accepted, 51 explicit 429; every acknowledged write persisted, malformed 422/oversize 413/recovery 200 and 500 CSV combinations pass.
- Final `evaluations/overhaul/new-final`: **400 condition-worlds across 40 paired seed blocks**, 800 old/new inference outcomes, **864 follow-ups**, 108 perturbations, zero crashes. Both models fit 360 and refuse 40 unsupported-weather worlds. Before/after source hashes match, and still match current files. No final truth informed a model change.
- Development/calibration: 12/24 seed blocks, separate layouts/transport/weather; original cases are development-used. Interrupted probes and source-formatting drift are retained and explained. Calibration was diagnostic; no empirical weight calibration was fitted. Final parameters stayed fixed.
- Ablations: 288 covariance/quadrature fits; 18 inference ablations and 19 selected/full-data comparisons; 36 numerical-budget planner choices. Failed probes remain preserved. Default sampling retains only 3/6 rare-episode readings in the single 192-row challenge; full inference retains six.
- Maximum numerical shape: 10,000 readings +10,000 met, 100 sites, 25 anchors, 576 supported cells, **12,097 components**. Fresh children, one BLAS thread, 30s/2GiB address-space ceiling: 128 fitted rows **15.58s/550.72MiB**, 512 **19.94s/1,290.16MiB**; finite plans, no excluded domain. Not a 10,000-row inversion. Exact probe/results in `resources-max-components/`; six smaller children also passed.
- Final PNG/SVG plots, notes and deterministic script/input/output hashes are in `new-final/figures.json`. `scripts/plot_overhaul.py` was visually inspected and checked against raw results.

## Scientific judgment and unresolved failures

**Research prototype; inadequate for reliable source attribution or general measurement recommendations.** Held-sensor prediction improves (higher-release RMSE 2.78→1.43µg/m³), but new regions occupy about 84–87% of the domain. Higher-release source presence is missed in 29/40 cases; weak in 39/40. Two-source, episodic and direction-bias screening misses all 40 cases each. The frozen product rule accepts just 2/400 cases and one accepted region misses truth. Conditional-mean errors near 90m largely reflect a no-data centroid baseline of 89.9m; do not claim learned localization precision. Planner bootstrap intervals cross zero in all three conditions. Old strong development-region coverage is 26/40, two-source 7/40 with 33 wrongly sharp regions. Retain these failures.

Final truth, reliability bins and supplementary prior-centroid/bootstrap/product-rule summaries are evaluator artifacts. Supplementary analyses are labeled post-evaluation; they did not replace predeclared metrics or change production logic. Conditions reuse seeds; do not pool them as independent campaigns.

**No measured-data localization validation.** Official NOAA DATEM/Sagebrush requests remain blocked by proxy CONNECT403. Exact routes, licenses, pinned primary/official documents and failures are in `ENGINE_RESEARCH.md` and `external-access.json`. London 65,533-row inspection lacks verified coordinates/release truth and remains a data audit. No tracer success or neighborhood accuracy is claimed.

## Reproduction and runtime

```sh
OPENBLAS_NUM_THREADS=1 .venv/bin/python -m pytest -q
cd frontend && npm run build && npm run test:e2e
# Return to repository root; every output folder below must be new:
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m upwind.validation.overhaul --split final --out .local/final-recheck
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m upwind.validation.overhaul_regression --out .local/oldcase-recheck --report .local/oldcase-report.md
PYTHONPATH=evaluations/overhaul/baseline-source/backend OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m upwind.validation.run --skip-external --out .local/baseline-recheck
MPLCONFIGDIR=.local/mplconfig .venv/bin/python scripts/plot_overhaul.py --input .local/final-recheck
```

`upwind evaluate` is now a small, explicitly development-used current-model regression on the original examples (24 cases, 15 fits, nine refusals). The old stress runner guards against applying its discrete metrics to the new model; use the baseline PYTHONPATH above. Source/lock/configuration/seed hashes are saved with runs and in the handover manifest.

Normal development services restarted from our prior processes. Current exec session **51263**, API PID **54634**, ports 8000/5173. Health confirms `plume-mixture-0.3.0`; browser tests use isolated 8001/5174. `bash scripts/dev.sh` remains the startup command. Base setup unchanged; optional research dependencies enable reader/figures. Do not run npm ci concurrently with builds/dev tests. Old browser-local results may need regeneration; archives retain their model version and report meaning.

## Next scientific work

Before changing priors, thresholds, covariance, physics or acquisition based on these outcomes, declare a fresh protocol/holdout; these final results are now inspected and cannot serve as a fresh untouched test for tuning. Obtain compatible controlled-release files with verified units, heights, meteorology, source truth and licensing; current fixed 5m/2m heights may require a separate documented model. Investigate independently observable source contrast, model discrepancy, geographic quadrature convergence and sensor-block predictive tails. Seek measured prospective placement outcomes before claiming operational benefit. Preserve every original/final failure and keep source responsibility out of the product.

Handover: [implementation/configuration manifest](../evaluations/overhaul/implementation-manifest.json) and [verification records](../evaluations/overhaul/verification.json).

## Active weather-repair resume (2026-10-19 UTC)

Candidate0.5 implementation is frozen for calibration: `evaluations/weather-bias/calibration-source-freeze.json` matches all current scientific/generator/protocol hashes. Do not change backend/upwind or WEATHER_BIAS_PROTOCOL during calibration/final. Baseline0.4 reproduced all40/18wrong exactly. Regression80fits complete in regression-part0..3: all original18 now covered,16accepted0wrong; all40biased coverage38/40,17accepted0wrong; prior compatible40 coverage40/40,19accepted0wrong, medianMAP49.7m, meanarea47.35% (regression from old22.9m/26.9% must be reported). These are development-used, not fresh validation.

Development224old/new outcomes complete across development-preflight/part1/part2 (source drift during development retained). `development-summary.json` recomputes corrected counts.48sensitivity/oracle fits and six independent profile curves complete: near-optimal source centers separated~412m with six monitors/four winds and~548m in same/far layouts. Prior15 misses one case retained by20/30; do not claim calibrated prior. Planner preflight45actual followups passes (15policies×3conditions),85.66/130.68/28.75seconds including full plan selection under CPU contention. No free met instrumentation.

Eight browser workflows pass in playwright-corrected.log; frontend-build-final.log built.111backend tests passed before three new independence/chunk/rotation cases; latest15weather cases pass. Full114test run is session49140 (`pytest-complete.log`). Resource preflight/chunked failures retained; resources-bounded passes all five children within60s/2GiB: single12821.10s960MiB; single51236.57s1791MiB; campaign128refuses240groups; unknowncampaign512refusesworkload; characterizedcampaign51218.10s1160MiB. No10k inversion claimed.

Calibration4disjoint stride4shards currently sessions85498/65057/14722/16344, folders calibration-part0..3, logs `.local/weather-bias/cal0..3.log`. Need complete448old/new outcomes(16×14×2), inspect, retain fixed rule unless explicitly justified beforefinal; if changing code, cal/finalfreeze must be revised and rerun appropriately. No fresh final0.5 has run yet. After calibration, freeze identical source/config before fresh final, then run4shards `--split final --offset0..3 --stride4 --planning` into final-part0..3. Each gets8seeds and6plannerworlds, total896old/new outcomes+360actualfollowups. All hashes before/after must match. `scripts/report_weather_bias.py` derives final/cal/regression tables and paired losses; `scripts/plot_weather_bias.py` produces standalonePNG/SVG/PDF and refuses overwrite. Inspect actual figures and verify outputs. Results report file is not written yet. Need include calibration interpretation, per-condition CIs/misses/false alarms, resource/test details, final limitations and exact manifests; finalize docs/PROGRESS and plan only after completion.

Normal current-code service restarted session84735 API PID85555 ports8000/5173 private loopback, model0.5. Old API71468 was already defunct; no user service killed. NOAA official retry403 retained. No Git commit/push/deploy/outreach. Do not create subagents. Use one BLAS thread per evaluation process. Existing `.venv`, Node24/Python3.12 setup unchanged. README/SCIENCE/WEATHER_BIAS_IMPLEMENTATION now describe0.5; old reports and snapshots preserved. No organizational or field reliability claim.

### Final0.5 now running — preserve freeze

Calibration complete448outcomes, zero crashes, all original calibration hashes unchanged. Retained the exact predeclared rule; no tuning. Important failures: unknown-direction4accepted1wrong; clock1accepted1wrong; spatial4accepted3wrong; independent transport10accepted2wrong. With direction comparisons5accepted0wrong/16coverage; nominal characterized6accepted0wrong/16coverage. Do not hide these limits.

After calibration only output metadata/rendering changed: used comparison source/upstream/time/provenance is now explicit, and mismatch wording correctly includes weather-only checks. Two fixed calibration cases reproduce all numeric metrics/diagnostics exactly (`calibration-presentation-confirmation.json`).16weather tests and all8finalbrowserworkflows pass, latest build passes. Full115test run session1404, log `pytest-release.log`. Earlier114full pass remains valid engineering history.

**Final-source-freeze.json SHA2563058ca0666caa1c6033d078e0740477e73d59a89205b56a33360acc2ef7f8253.** No further backend/upwind or protocol edits while final runs. Four final stride4shards launched with planning: exec sessions10821(offset0),23075(offset1),94595(offset2),15422(offset3), Python PIDs87630/87640/87642/87634. Folders `evaluations/weather-bias/final-part0..3`, logs `.local/weather-bias/final0..3.log`. Each has8seeds/112condition-worlds plus6plannerworlds, total896old/new outcomes +360followups. Do not terminate or skip the remaining seeds. Need finish every shard, verify frozen source hashes, generate actual reports/figure, inspect, update PROGRESS and final answer. No final result selected a model change.

`scripts/report_weather_bias.py` now also derives detailed `WEATHER_BIAS_ACCEPTANCE.md`, calibration selection context and every paired planner comparator. Formatting scripts during final is reporting-only; scientific source freeze covers backend/protocol/locks. `scripts/reproduce_weather_baseline.py --out NEWPATH` strips new strict-schema fields and reproduces the detailed original40/18; a2-case command preflight passed exactly. Initial original script remains untouched. Add release test/resource details, actual final interpretations and figure to generated results after reading outcomes. Always report conditional coverage/area together and mention point estimates can remain distant.

Final engineering confirmation:115pytest tests pass in55.93s (`pytest-release.log`),8browser tests pass in41.1s (`playwright-final.log`), build passes. Current-source resource-release5children complete, every source hash matches freeze: single12823.76s955MiB; single51244.46s1791MiB; campaign128explicit240-group refusal; unknowncampaign512explicit workload refusal; characterizedcampaign51224.04s1160MiB. All under60s/2GiB. Current source server restarted API session65318/PID88809; Vite5173 remains session84735. Actual HTTP comparison analysis reports16used references in `current-api-comparison.json`.

Additional fair-data control8worlds is complete: `reference-control/results.json` and original executed `script.py.txt` match its metadata hash. Separate protocol WEATHER_BIAS_REFERENCE_CONTROL.md declared after primary freeze before reading planner outcomes. It lets0.4 use actually observed qualified reference weather, with provided uncertainty, then locks a pollution plan and evaluates it under the same0.5 downstream estimator. Do not describe new-vs-old on original primary data as a pure inversion benefit. `scripts/reference_weather_control.py --out NEWPATH` adds only an output-directory CLI after the executed script was preserved. Primary360followups complete by early final; remaining source-inference worlds must finish. `report_weather_bias.py` includes actual resource usage/optional fewer instruments and supplementary comparator results. Cap is at most2, not necessarily exactly2.

Both pre-presentation calibration source files were reconstructed by reversing only the recorded output additions; every byte matches their actually recorded calibration SHA256. All calibration sources preserved in `calibration-source`, manifest. Final source/configuration snapshot84files in `frozen-source`, manifest; includes code/tests/frontend/scripts at freeze. Later reporting/supplement scripts have separate hashes and do not change frozen production/evaluator code. No final-dependent production change is allowed.
# Current handoff — National Explorer v3 release complete

The `/explore` National Explorer is a separate product surface; inverse source-localization findings and artifacts remain preserved and are not used by it. The current local release and authoritative data/model/API/evaluation record are in [NATIONAL_EXPLORER_V3_RELEASE.md](NATIONAL_EXPLORER_V3_RELEASE.md). Release `upwind-national-explorer-0.3.0` deploys model `upwind-nearest-monitor-annual-pm25-0.3.0` under protocol `UW-NATIONAL-SPATIAL-2026-04`, built from official EPA AQS, Census, EPA NEI, and PRISM data. The builder now selects one ambient event-treatment summary per POC; event-excluded alternatives are not used as ambient observations. The correction changed 80 2024 and 57 provisional 2025 site-year means and all corrected evaluation artifacts are retained.

The same selection rule leaves nearest-monitor deployed. Gaussian+PRISM tmean achieved 1.320/1.859 µg/m³ MAE/RMSE on 872 matched 2024 sites and 1.384/1.872 on 882 provisional-2025 sites, winning5/5 and3/5 folds. It fails the unchanged requirement of at least4/5 wins in both years. The deployment's empirical ±4.123 µg/m³ spatial OOF band covered89.9% in matched 2024 and93.2% in provisional2025; it is not a local guarantee. These previously inspected monitor vintages are development evidence, not untouched validation. Coverage:32,333 searchable places,31,523 estimates,810 withheld, population sum213,515,188. The full backend suite (250), production build and all nine National Explorer browser workflows pass. No field accuracy, public deployment or source attribution claim is established.

The v1/v2 National Explorer notes below are historical snapshots; see [v2 methods and limits](NATIONAL_EXPLORER_V2.md) and [v1 baseline](NATIONAL_EXPLORER.md) only for historical details.

# Current handoff — engine 0.9 feasibility repair complete
