# UPWIND continuation prompt

Copy the text below into the next coding LLM, with access to the repository.

---

You are continuing **UPWIND**, https://github.com/apandya55/Upwind. Start by checking `git status`, `git log -1` and the actual checkout; preserve user changes. Read `AGENTS.md`, `docs/PROGRESS.md`, `docs/SCIENCE.md`, `docs/WEATHER_BIAS_RESULTS.md`, `docs/WEATHER_BIAS_ACCEPTANCE.md` and `docs/WEATHER_BIAS_IMPLEMENTATION.md`. Those files and retained raw evidence take precedence over this summary if they disagree. Do not assume processes or ignored local files survived. The repository contains the complete application and historical evaluation evidence, not just a patch.

## User's goal and completed release

The user wants a working, rigorously tested pollution investigation and measurement planning application, eventually useful to governments, companies and activist organizations. The latest repair addresses coherent weather bias that previously produced accepted wrong source regions. The user authorized publishing this completed project to GitHub and requested this continuation prompt. Publishing a future deployment, releasing investigation data, contacting organizations or claiming certification requires its own applicable authorization. No outreach or deployment has happened.

Current scientific model is **plume-weather-0.5.0**, protocol **UW-WEATHER-2026-03**. The application package remains0.1.0. It is a **research prototype with synthetic tests, not field-validated source attribution**. Source localization, concentration prediction, recordkeeping, monitoring placement and secure organizational deployment are separate capabilities. Do not promise responsibility findings, regulatory accuracy, calibrated geography or general planner superiority.

The weather repair is implemented across backend, CSV schema, API, React UI, HTML exports and saved-result migration. It:

- Separates unknown persistent station direction/log-speed bias (research priors SD20°/.2) from user-declared short-period uncertainty; propagates joint source/weather/strength uncertainty into regions and predictions.
- Conditions weather bias only on qualified explicitly independent primary/reference readings, paired within120s/250m and14days of the campaign. Shared upstream systematic covariance floors do not shrink as1/√N. Duplicate products cannot manufacture independent calibration. Metadata remain user claims.
- Separately reports weather-only correction and pollution-conditioned offset, evidence/provenance and mismatch; unknown stays unknown. Incompatible comparison evidence blocks support. It does not solve arbitrary clock errors or spatial wind fields.
- Preserves raw imports/UTC/origins, includes full configuration in cache identity, archives old scientific results and requires rerunning them. No silent reinterpretation of old results.
- Bounds exact numerical temporary arrays; explicitly refuses excessive workloads or comparison counts instead of crashing or manufacturing measurements.

The unchanged core is a restricted neutral Gaussian transport approximation, background-only versus one fixed source with constant positive strength, up to six declared steady campaign periods, integrated backgrounds/trends/instrument biases and correlated error. It is not a multi-source, puff, chemistry or city-flow model. The experimental support rule requires source weight≥.9, conditional90% region<half the supported area, no predictive mismatch and no weather-comparison mismatch. Passing that rule is not proof of accuracy.

## Evidence you must retain and understand

All paths below are relative to repository root:

- `evaluations/weather-bias/baseline-source` and its manifest preserve exact0.4; `reproduced/all40.json` and `accepted18-diagnostics.json` reproduce all40 biased cases including18 accepted wrong regions. The original short wind prior excluded coherent ~25° error; source/strength/background compensated and shared-weather pollutant holdouts passed. No wind-convention/unit/time-sign bug was found.
- On those **development-used original18** cases the repair covers18/18, accepts16 with zero accepted wrong; two abstain. This is regression evidence, not untouched validation. Across all original40 biased cases it covers38/40, accepts17 with zero accepted wrong. Original compatible40 coverage40/40 but median MAP49.7m/mean area47.4%, versus old22.9m/26.9%; broader uncertainty has a usefulness cost.
- Fresh development seeds1010000–7, calibration1110000–15, final1210000–31. Fourteen conditions with new layouts, weather bands, lag ranges and spatial mismatch; all raw inputs, explicit refusals and outputs are retained. Final has896 old/new source outcomes across448 condition-worlds, and360 actual follow-up fits across24 paired worlds. These are **now inspected**, not future holdouts. Report per-condition denominators and intervals; repeated methods are not independent worlds.
- `final-source-freeze.json` hashes every frozen scientific file/protocol/lockfile. Four `final-part*` directories retain before/after source hashes. `verification.json` verifies counts, source snapshots, report and figure hashes. Frozen scientific files were unchanged during final evaluation. `calibration-source` reconstructs the exact calibration source; only output/provenance presentation changed afterward and repeated numerical results match exactly.
- `final-summary.json`, `planner-paired-comparisons.json`, `original40-before-after.json`, `reference-control`, `sensitivity`, `resources-release`, and `figures` accompany the Markdown reports. Do not discard failures, failed resource preflights, explicit refusals or older version evidence.
- All six primary new-versus-mean-random planner RMSE confidence intervals cross zero (eight paired worlds per condition). No demonstrated general superiority. Choices were locked before reveal, each with cost≤250/equipment≤2; actual spending can be smaller. All downstream estimators use0.5. These are retrospective simultaneous measurements at observed times, not prospective field experiments.
- The primary0.4 adapter cannot condition reference-weather fields. A supplementary eight-world control supplies actual noisy observed reference readings to0.4; it prevents attributing all gains to new inversion logic. It never supplies true weather. The protocol and original executed script are retained.
- Sensitivity/oracle work uses development worlds only. Priors15/20/30° expose prior dependence; same-wind or poor-layout cases often retain≥75% domain even with correct-weather oracle. Requested10m cells are capped at24per-axis; actual cells in that probe are about15.4×18.3m. Do not mislabel achieved resolution.
- Clock lag, spatial mismatch, correlated error, independent transport and multiple sources still produce accepted geographic errors. Final accepted geographic errors include spatial mismatch4/10 accepted, correlated error1/5, two sources4/13 and independent transport3/13. Direction-bias final coverage improves10/32→30/32 (unknown) or31/32 (comparison), with0/9 and0/10 accepted wrong. Calibration still has direction/clock failures. Read the full tables and intervals before quoting rates. Warning-free fits can be wrong. The repair does not establish government/company/activist attribution readiness.
- NOAA measured-tracer requests failed proxy CONNECT403 (`external-retry.json`); no compatible measured controlled-release validation was performed. Historical London records without source truth/compatible geometry establish import/audit behavior only. No external dataset, partner or endorsement should be invented.

## Verified engineering and how to reproduce

Python3.12.14, Node24.19, npm, Linux, Chromium `/usr/bin/chromium` were used. Normal setup: `bash scripts/setup.sh`; dev: `bash scripts/dev.sh`. See README for alternative production-build/loopback startup. Dependency locks are committed. Research reporting dependencies are in `requirements-research.lock`. No GPU or paid API is required. `.venv`, `node_modules`, `.local` and real SQLite investigations are ignored. Never publish their contents or credentials.

Verified release checks:115 pytest tests, eight Chromium workflows, frontend build/typecheck. Existing Starlette/httpx deprecation is not a test failure. Commands from repo root:

```sh
.venv/bin/python -m pytest -q
(cd frontend && npm run build && npm run test:e2e)
.venv/bin/python scripts/verify_weather_release.py
```

Browser tests own ports8001/5174 and isolated data; do not run `npm ci` during live Vite/browser workflows. Single-process local service: `.venv/bin/uvicorn upwind.api:app --host 127.0.0.1 --port 8000`. Verify health/representative API behavior after restarting; live PIDs are not portable. The unauthenticated loopback app and local unencrypted storage are not an organizational deployment architecture.

Frozen resource probes: each child60s/2GiB;10,000 readings +10,000 weather rows loaded, at most512 inverted. Single-window128fit23.76s/954.8MiB;512fit44.46s/1790.5MiB. Characterized512 campaign24.04s/1159.6MiB. Unknown-weather512campaign explicitly refuses workload;128campaign refuses240sensor/window groups. These are bounds and observed measurements, not a universal SLA. API stress retained36 acknowledged writes among64 requests with28 explicit429s; malformed422/oversize413/recovery200 and500CSV fuzz cases passed.

Rebuild reports from retained raw evidence without rerunning scientific evaluation:

```sh
.venv/bin/python scripts/report_weather_bias.py
# Figure generator refuses existing figures: preserve them before choosing a NEW destination/run.
MPLCONFIGDIR=.local/mplconfig .venv/bin/python scripts/plot_weather_bias.py
.venv/bin/python scripts/verify_weather_release.py
```

Do not blindly run the figure command against the retained figure directory. Regenerating scripts/manifests can change documentation; review diffs. Baseline reproduction (new output directory):

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/reproduce_weather_baseline.py --out .local/new-baseline-reproduction
```

Fresh evaluation runner syntax (expensive; preserve existing destinations):

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m upwind.validation.weather_bias --split final --offset 0 --stride 4 --planning --out .local/reproduction-final-part0
```

Run offsets0,1,2,3 to reproduce all retained final cases; reusing these seeds is reproduction, not a fresh test. Main run source is `backend/upwind/validation/weather_bias.py`; auxiliary sensitivity/resources are `weather_aux.py`. `scripts/regress_weather_original.py` reproduces development-used old cases with `--offset`, `--count`, `--out`; `scripts/reference_weather_control.py --out NEWPATH` reproduces the supplementary control. Historical module names/versions are retained intentionally.

## Recommended next work

First report the actual final limitations plainly to the user and agree on the next target. High-value next targets are obtaining accessible licensed controlled-release observations with known source/weather, evaluating spatial/temporal weather mismatch independently, and designing a prospective placement experiment. Secure organizational use would separately require access control, tenancy, audit logs, encryption/backup/retention and deployment review. Do not add that scope silently.

For any scientific change, write a falsifiable hypothesis and a new version/protocol, preserve this release and its errors, choose fresh development/calibration/final conditions before selection, and hold the new final untouched until source freeze. Do not tune to these final seeds or convert a failed adequacy claim into a passing one by excluding difficult cases or raising rejection thresholds. Distinguish useful inference from abstention and count every generated case. Match information, weather observations, budgets/equipment and downstream estimators across comparisons; report actual outcomes and uncertainty.

Preserve user investigations and explicit truth separation. Synthetic evaluator truth/oracles must never enter production inference or planner inputs. Finish authorized implementation and appropriate checks; explain real blockers without inventing results. The current branch/commit in Git identifies the published source; run `git rev-parse HEAD` rather than assuming a SHA from a conversation.
