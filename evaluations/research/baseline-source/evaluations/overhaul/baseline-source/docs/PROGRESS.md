# Durable progress — severe stress evaluation completed

Current scientific model: **plume-ensemble-0.2.1**; application package remains 0.1.0. Work is local and uncommitted; no GitHub push, deployment, outreach, or raw-data publication was performed. Preserve `.local` investigations and user changes. Use the existing checkout, not a new worktree.

## Read first

- `docs/STRESS_REPORT.md`: complete results, failures, capacity, commands and figures.
- `docs/STRESS_PROTOCOL.md`: frozen seeds, predeclared metrics and documented evaluator/diagnostic corrections.
- `docs/DATASET_CATALOG.md`: what each external dataset can actually validate and exact access/metadata blockers.
- `docs/SCIENCE.md`: equations, units, likelihood/covariance, planning objectives and scientific limits.

## Verified outcomes

Final data: `evaluations/stress/v0.2.1-final/`. **72,167 engineering/property checks**, zero failed groups; **640** synthetic case/seed runs and **3,680** paired follow-up evaluations, zero crashes. These are 40 held-out seeds across repeated conditions/methods, not thousands of independent campaigns. 160 unsupported-condition source analyses were refused as designed. Separate verification: **34 pytest tests passed**, **four Chromium workflows passed**, TypeScript/production build passed and Ruff F401/F821 checks passed.

Maximum resource fixture: 10,000 measurements +10,000 meteorology records, 100 sites, 25 source hypotheses, 1,350 scenarios. About **1.42 seconds**, **227 MiB peak RSS** on the recorded AMD EPYC machine, one Python process/BLAS thread. At most **40 balanced rows are fitted**, after validating all-window conditions; this is not a 10,000-row full inversion. All resource cases ran with 30s subprocess timeout and 2GiB address-space ceiling. Exact timings/hardware are in JSON; not a universal laptop guarantee.

The 64-write/32-client concurrency test used isolated SQLite storage; all acknowledged writes survived exactly once, overload received deliberate 429, invalid writes did not partially persist, oversized bodies returned 413, and recovery succeeded. API now admits at most four POST/PUT requests concurrently. A 500-combination CSV edge battery found no unexpected exceptions.

## Defects repaired

Shape-safe empty site handling; explicit uncertainty/UTF-8 byte bounds; strict scientific JSON numeric types; Cholesky likelihood/information calculations; full-window weather/geometry before balanced sampling; contradictory duplicate quarantine; duplicate source refusal; unsupported source-distance filtering; order-independent geographic origins and ID ordering; fixed spatial target universe across budgets; best available baseline envelope for large-case heuristics; separate uninformative versus infeasible status; MAP-tie-aware evaluation; covariance-standardized residual warning; visible UI model-mismatch alert. No raw imports or historical failures were erased.

Preserved history: original `evaluations/synthetic-results.json` and initial protocol; `evaluations/stress/baseline-*`; development permutation failures; first complete v0.2.0 and pre-final v0.2.1 runs. The v0.2.0 evaluator spuriously reported zero error for a uniform tied source posterior and used the wrong residual-noise scale. Both are documented and corrected without changing the held-out transport, likelihood or planner to obtain a preferred outcome. Report-renderer source hashes are recorded separately from the tested numerical source snapshot.

## Important retained scientific failures

- High-signal matched-family synthetic case: 40/40 unique MAP locations within 100m. Weak signal: 6/40. This is a same-family scalar-generator check, not independent field validation.
- Wind-direction bias: only 10/40 true sources in the nominal conditional 90% grid set. A separate speed-bias case assigned about 97.7% weight to a wrong location 100m away without a mismatch alarm.
- The constructed two-source case escaped the residual alarm in all 40 runs. A correct dominant-grid location does not establish a single source. The diagnostic is a heuristic with false negatives, not an adequacy certificate.
- Follow-up optimizer helps on average under favorable matched high-signal assumptions; weak-signal localization/prediction can be worse than random. Under noise mismatch it made 3/40 confidently wrong optimized selections. Entropy reduction does not certify accuracy or health benefits.
- Future scheduling, urban-canyon chemistry/transport, field attribution and calibrated geographic uncertainty remain unsupported. Do not hide these failures or tune existing held-out seeds.

## Actual external data and limits

Acquired and inspected upstream openair `mydata`, revision `c2970d8c5addf68497bddaae13230167e7387651`: 65,533 hourly London records, 56,758 nonmissing PM2.5 values, 8,775 missing. Units/dates documented upstream; R POSIXct read explicitly UTC. No coordinates occur in the file; verified station metadata is blocked, one urban site has no known release truth. All 65,533 incomplete-coordinate rows were exercised in seven bounded batches and rejected rather than inventing sites. This is a measured-data audit, **not a real-data source-model accuracy test**. Raw data are ignored locally pending primary-data redistribution review; hashes and statistics are saved.

Official NOAA/EPA/UCI/UK/London metadata requests returned CONNECT 403. The environment draft preserves previous settings and adds `archive.ics.uci.edu`, `uk-air.defra.gov.uk`, `londonair.org.uk`; prior NOAA/EPA domains were already saved. Draft save confirmed persistence only. Runtime access/publication have not been established; user must review/save environment settings and publish before retrying affected acquisitions. No token was requested and no verification disabled.

## Commands and artifacts

```sh
bash scripts/dev.sh
# Ordinary regressions:
.venv/bin/python -m pytest -q
cd frontend && npm run build && npm run test:e2e
# From repository root, optional research reader/plot dependencies:
uv pip install --python .venv/bin/python -r requirements-research.lock
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m upwind.validation.run --out .local/new-stress-run
MPLCONFIGDIR=/workspace/Upwind/.local/mplconfig .venv/bin/python scripts/plot_stress.py --input .local/new-stress-run
.venv/bin/python -m upwind.validation.reporting --input .local/new-stress-run --out .local/new-stress-report.md
```

Runner refuses nonempty output directories. `--skip-external` records an explicit unrun inspection. Reports handle blocked data and failed resource children without inventing validation. Figure inputs/version/source hashes, dependency versions/lock hashes, exact numerical/evaluation source hashes, report artifact hashes, raw outcomes and pytest XML are retained. Browser tests use separate ports 8001/5174 and `.local/browser-test-data`. Original startup scripts/configuration remain usable; research packages are optional for app use. New CLI evaluations default to `.local/current-model-evaluation.json` to preserve the original v0.1 results.

Code: `engine.py` orchestration/ensemble/plans; `numerics.py` kernel and stable information; `weather.py` full-window matching; `quality.py` deterministic selection; `validation/` independent oracle, fixtures, science, resources, API/data batteries and reporting. New figures are under the final evaluation directory. Existing operator guide/pilot kit and AI disclosure remain in `docs/`.

## First incomplete work

1. Obtain actual compatible controlled-release files and independent station metadata once runtime access works; inspect release histories/heights, units, averaging periods, meteorology, licenses and truth separation before fitting anything. Fixed H=5m/z=2m may require a separate documented model; do not silently relabel tracer gases as PM2.5.
2. Predeclare new development and untouched evaluation seeds/campaign splits before changing physics or model families. Investigate multi-source/background/weather misspecification and posterior predictive adequacy rather than adjusting a threshold until this frozen test passes.
3. Validate realized placement decisions on an independent real network/campaign with candidate outcomes and future weather withheld. Do not equate the existing Gaussian-moment score with demonstrated field benefit.
4. Obtain genuine operator feedback/consent; verify current CAC and AI-disclosure rules independently before submission. No adoption or award outcome is claimed.
