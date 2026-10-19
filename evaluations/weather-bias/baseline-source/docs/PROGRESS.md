# Durable progress — research0.4 implementation and evaluation completed

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
