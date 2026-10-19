# Current handoff — measured-data intake repair complete

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
