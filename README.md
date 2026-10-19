# UPWIND

A local investigation workspace for community **PM2.5 exploration and monitoring design**, with an experimental background/source comparison engine. No accounts, paid APIs, live hardware or GPU required. All bundled data are visibly synthetic. This is a working first local release, not field-validated source attribution.

Current release: **plume-weather-0.5.0**. Read the [weather repair results](docs/WEATHER_BIAS_RESULTS.md), [engineering/scientific limits](docs/WEATHER_BIAS_IMPLEMENTATION.md), and [LLM continuation prompt](docs/UPWIND_LLM_EXPORT_PROMPT.md). Synthetic improvements do not establish operational attribution reliability.

## Run locally

Requires Python 3.12+, Node 22.12+ (tested 24.19), and npm. Linux/macOS commands:

```sh
bash scripts/setup.sh
bash scripts/dev.sh
```

Open `http://127.0.0.1:5173` in your own laptop browser. API: port 8000. No credentials needed. The first screen opens the complete synthetic example. Click **Generate measurement plans**, change budget or permissions, compare baselines, save, and export evidence. See [the operator guide](docs/pilot/OPERATOR_GUIDE.md).

Single-process mode after setup/build:

```sh
.venv/bin/uvicorn upwind.api:app --host 127.0.0.1 --port 8000
```

Then open port 8000 locally. Stop/restart this command after rebuilding the frontend. Development mode uses Vite with an API proxy and hot reload. SQLite and raw CSVs live locally in `.local/upwind.sqlite3`; set `UPWIND_DATA_DIR` to change the directory. Live processes need restarting after a machine snapshot restores. Data are private local files, not encrypted storage; the unauthenticated API is intended for loopback use.

## Verify and reproduce

```sh
.venv/bin/python -m pytest -q
.venv/bin/upwind demo --out .local/demo-result.json
.venv/bin/upwind evaluate --out .local/current-model-evaluation.json
cd frontend
npm run build
npm run test:e2e
```

Browser tests use separate ports 8001/5174 and `.local/browser-test-data`. Install Chromium and set `CHROMIUM_PATH` if it is not `/usr/bin/chromium`, or install Playwright's Chromium and point that variable at its executable. Browser test downloads/screenshots stay local. Exported investigation JSON can be reproduced with `.venv/bin/upwind analyze path/to/investigation.json --out .local/analysis.json` from the repository root. Generated `runtime_ms` is a measured first-run timing retained in cache; it is not an SLA.

## What works

- Define a study area, objective, concerns and source-domain anchors.
- CSV schema mapping, UTC normalization, optional uncertainty/humidity/temperature, quality flags, preserved raw imports and hashes; follow-up files append and invalidate previous analysis.
- Offline spatial grid, optional MapLibre/OpenStreetMap context, synchronized monitor readings/timeline, site constraints and approximate resident observations.
- Cost/equipment-constrained predictive-mixture information and spatial coverage objective; exhaustive tiny cases, fair spread/random/wind baselines, correlated errors, integrated nuisance parameters and a transparent geometric baseline.
- SQLite save/reopen, investigation JSON restore, spreadsheet-safe normalized CSV, self-contained HTML report with print-to-PDF styles and evidence limits.
- Deterministic engine and CLI, recorded synthetic evaluation outputs, operator/pilot kit.

## Evidence and important gaps

Original v 0.1 evaluation (preserved): **24 synthetic runs, 15 analyzed, 9 refused** for unsupported conditions. The nominal identifiable case did **not** reliably localize the hidden source; conditional weights are broad. Median location error across analyzed cases was about 680 m. Do not interpret discrete-grid coverage or a numerically sharp weight as real-world calibration. Read [the actual results](evaluations/synthetic-results.json) and [science limits](docs/SCIENCE.md).

NOAA/Sagebrush, EPA documentation, and the EPA hourly PM2.5 archive were blocked by this environment's HTTP CONNECT policy (403). No independent tracer/PM2.5 benchmark or prospective planning benefit has been established. An EPA AQS acquisition/conversion script is supplied; actual archive compatibility remains unverified until access is available. [External-data instructions](docs/EXTERNAL_DATA.md) record exact destinations and the blocker. Future scheduling is explicitly unsupported. Each observed steady period is limited to one hour; explicit campaigns require a fixed source and constant release across separately steady periods. No outreach, publication, partnerships, adoption, field accuracy or competition eligibility is claimed.

## Research engine and current evidence

Current scientific model: **plume-weather-0.5.0**, protocol **UW-WEATHER-2026-03**. Read [weather-bias results](docs/WEATHER_BIAS_RESULTS.md), [root causes, equations and reproduction](docs/WEATHER_BIAS_IMPLEMENTATION.md), and [science limits](docs/SCIENCE.md). Historical campaign0.4 results remain in [RESEARCH_RESULTS.md](docs/RESEARCH_RESULTS.md). Local engineering tests do not establish reliable source attribution for governments, companies or activist organizations.

Open **Scenarios → Open synthetic campaign example** to explore four independently steady wind periods. The new model supports explicit 2–6 periods with a shared fixed source/constant release assumption, independent period backgrounds and persistent instrument bias. Enter documented wind uncertainty and release/receptor heights. Read nuisance-profile ambiguity and whole-sensor/period predictive checks together. Changed release, incorrect weather and transport mismatch can still produce confidently wrong results without a warning.

The optional **Spatial prediction · concentration uncertainty** objective targets concentration prediction at independent instruments. It uses a deterministic covariance objective with all mixture moments; it is separate from source localization. Original information, coverage, spread, wind and random options remain available. Costs/permissions/equipment apply equally. No future weather, travel or scheduling benefit is promised.

Default inference fits up to128 selected readings (configurable40–512), balancing sensor×period groups. Raw imports remain preserved; loaded/excluded/usable/fitted counts are separate. Campaigns with more groups than the limit explicitly refuse rather than silently drop instruments/periods. Source regions remain conditional and uncalibrated; recommendations are **research only**. See the detailed result distributions, coverage/area, accepted errors, missed warnings, actual post-measurement planning comparisons and resource limits before interpreting a plan.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m upwind.validation.weather_bias --split final --planning --out .local/weather-recheck
```

Historical0.3 results remain in [ENGINE_RESULTS.md](docs/ENGINE_RESULTS.md). All800 inference/864follow-up/108perturbation outputs were reproduced exactly excluding timings from `evaluations/research/baseline-source` before redesign. The broader current evaluation preserves old cases and holds out layouts, wind regimes and a separately checked advection/transverse-diffusion challenge. Synthetic success is not measured validation.

The original severe-stress [report](docs/STRESS_REPORT.md) and [protocol](docs/STRESS_PROTOCOL.md) describe archived 0.2.1. Its 640 source/3,680 follow-up numerical outputs were reproduced exactly from the preserved source snapshot before the overhaul. Reproduce that historical experiment explicitly:

```sh
PYTHONPATH=evaluations/overhaul/baseline-source/backend OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m upwind.validation.run --skip-external --out .local/legacy-stress-recheck
```

The normal `upwind evaluate` command is now a small, clearly labeled development-used regression using the current region definitions. It is not an untouched evaluation. The old archived command refuses to apply its obsolete discrete metrics to the new model. Existing output directories are preserved by the broader evaluation runners.

Research plotting/reader packages are optional for normal app use: install `requirements-research.lock` to reproduce figures/data inspection. See [dataset catalogue](docs/DATASET_CATALOG.md) and [research/data-access evidence](docs/ENGINE_RESEARCH.md). No controlled-release files or measured-data source accuracy were obtained; NOAA CONNECT 403 blockers remain explicit.

## Code to understand and change

| Location | Responsibility |
|---|---|
| `backend/upwind/inference.py`, `campaign.py`, `predictive_checks.py`, `identifiability.py`, `prediction_design.py`, `design.py`, `engine.py`, `numerics.py` | Campaign inference, exact predictive checks, nuisance profiles, prediction/information design, constraints and transport kernel |
| `backend/upwind/importers.py`, `models.py` | Schemas, UTC conversion, validation and lossless provenance |
| `backend/upwind/fixtures.py`, `evaluation.py` | Synthetic generation, hidden truth separation and held-out evaluation |
| `backend/upwind/api.py`, `store.py`, `report.py` | HTTP, local SQLite, safe exports |
| `frontend/src/App.tsx`, `Map.tsx`, `style.css` | Investigation workflow, offline/optional geographic map, visual design |
| `docs/PROGRESS.md` | Exact checked commands, risks and next work |

See [product scope](docs/PRODUCT.md), [sources and attribution](docs/SOURCES.md), [AI assistance](docs/AI_ASSISTANCE.md), and [three-minute demo](docs/DEMO.md). Verify current official CAC rules and AI-disclosure requirements before submitting; that verification is outstanding.


## Weather-bias repair0.5

Current weather behavior and reproduction: [WEATHER_BIAS_IMPLEMENTATION.md](docs/WEATHER_BIAS_IMPLEMENTATION.md); [fresh protocol](docs/WEATHER_BIAS_PROTOCOL.md); [measured synthetic outcomes](docs/WEATHER_BIAS_RESULTS.md). Older research reports remain historical0.4 evidence. Declared direction/speed uncertainty now describes short-period uncertainty; unknown persistent station bias is integrated separately. Optional weather CSV columns `role,source_id,upstream_id,direction_systematic_sd_deg,speed_systematic_fraction,direction_random_sd_deg,comparison_provenance` supply explicit independent paired reference readings. Both primary and reference need distinct nonempty upstream lineage; comparisons need uncertainty/provenance and must be simultaneous/co-located. User metadata do not certify calibration. Same-upstream products add no independent precision.

UI/HTML distinguish weather-only comparison corrections from pollution-conditioned wind offsets, explain unknown accuracy and additional evidence needs, and preserve old analyses in private JSON archives on load/import. Rerun old saved studies under the new model. Pollution plans do not include a new wind instrument or forecast; any new weather collection needs its own budget. No measured tracer validation or organizational attribution reliability is established.
