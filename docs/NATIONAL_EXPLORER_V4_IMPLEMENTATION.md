# National Explorer v4 implementation

This document records the local product overhaul built on the v3 national release. It is an implementation record, not a field-accuracy claim.

## Product and architecture

The public product now opens with a lightweight landing page at `/`; `/explore` is the full-screen National Explorer and `/local` is the own-data entry point. The older synthetic investigation workspace is preserved at the explicit `/workspace` route and is not linked from the public Explorer journey. The Explorer keeps one MapLibre instance, uses native GeoJSON layers with monitor clustering, requests bounded viewport pages after settled map movement, and loads the national release from the API instead of shipping it in the browser bundle. On small screens, a selected place, monitor, or facility opens in a scrollable bottom sheet over the map.

The API contracts remain release-aware and bounded:

- `/api/national/places`, `/monitors`, and `/sources` require complete finite viewport bounds for map requests and return stable pages, exact totals, and truncation metadata.
- `/api/national/context` accepts a WGS84 point and a radius capped at 250 km. It returns nearby AQS monitor summaries and NEI inventory rows as separate evidence classes, ranks by great-circle distance, and includes provenance and limitations. Inventory emissions are displayed metadata, not a ranking weight or causal score.
- Snapshot JSON, CSV, GeoJSON, and print use the same selected-place release data. CSV protects spreadsheet formula cells; GeoJSON coordinates are WGS84 `[longitude, latitude]`.

## Data actually integrated

The local release uses EPA AQS annual PM2.5 summaries (2018–2025), Census 2024 place Gazetteer points and 2020–2024 population estimates, EPA 2023 NEI primary-PM2.5 facility summary rows, and PRISM annual temperature grids for the evaluated development candidate. AQS rows now carry `upwind-canonical-observation-1` records with provider/station identity, annual UTC period, pollutant/units/metric, selected POC event treatment, quality fields, archive hash/member, and source CSV row numbers. Event-treatment alternatives remain distinct from independent instruments.

The deployed place estimate is still nearest eligible 2024 monitor. Gaussian and Gaussian+PRISM candidates remain development comparisons because the predeclared two-year fold-win rule was not met. No new low-cost sensor source was silently added: access, units, quality, deduplication, and redistribution requirements must be verified before integrating another provider.

## Coverage and evidence

The checked v3 release contains 32,333 searchable Census places, 31,523 supported 2024 estimates, 810 explicit withholds, 894 eligible physical monitor sites, and 76,404 mapped NEI PM2.5-PRI facility summary rows. These are release counts, not people reached or exposure coverage. Place coordinates are Gazetteer internal points, not legal boundaries or area averages. Monitor observations, modeled point estimates, facility inventory records, and any observational association remain separate.

The context workflow lets a user choose a bounded 25, 50, 100, or 250 km radius around a selected Gazetteer point. It shows nearby measured monitor summaries and documented inventory records with actual distance, year, pollutant, units, source links, and evidence-class interpretations. It does not infer facility contribution, responsibility, health risk, or regulatory status.

## Evaluation and performance evidence

The existing national-v3 comparison remains the supported model evidence: nearest-monitor 2024 matched-site MAE/RMSE 1.832/2.662 µg/m³; Gaussian+PRISM 1.320/1.859 in 2024 and 1.384/1.872 in provisional 2025, but only 3/5 provisional-year fold wins. No untouched final monitor set or independent field validation exists.

The v3 local measurements remain the before/after performance record: six-request medians were 2.67 ms for a central-North-Carolina place viewport, 1.57 ms for monitors, 14.39 ms for facilities, and about 30 ms for one-place snapshot generation on this machine. The national JSON release stays server-side. These are local single-user measurements, not an SLA; the v4 UI changes were verified for behavior and build but were not presented as a new benchmark.

## Run and verify

From the repository root:

```sh
bash scripts/setup.sh
PYTHONPATH=backend .venv/bin/uvicorn upwind.api:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/` for a built release. For Vite development, run the API separately and use:

```sh
cd frontend
UPWIND_API_URL=http://127.0.0.1:8000 npm run dev -- --port 5174
```

Open `http://127.0.0.1:5174/`. Rebuild the ignored local release only when source files or vintages change:

```sh
.venv/bin/python scripts/build_national_dataset.py --start-year 2018 --end-year 2025
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/evaluate_national_v2.py
.venv/bin/python scripts/evaluate_national_v3.py
```

Focused verification used for this overhaul:

```sh
PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests/test_national_api.py backend/tests/test_national_dataset.py backend/tests/test_national_v3_eval.py backend/tests/test_national_v2_eval.py
cd frontend && npm run build
```

The focused backend suite passed 22 tests, the production frontend build passed, and all nine National Explorer Playwright workflows passed against the local release. The build retains Vite's advisory about the deferred MapLibre chunk. No deployment, outreach, purchase, or public publication was performed.

## Remaining limits

The release is historical and local. It does not provide live conditions, forecasts, personal exposure, facility causation, or source responsibility. A radius query is measured from a supplied point; polygon boundaries and area averages require a separately validated boundary source. Weather-aligned directional association is not enabled because a compatible independent timestamped weather/observation dataset is not established. A broad empirical spatial error band is not a local guarantee, and no independent field validation has been completed.

## Evidence and share-state continuation (2026-10-21)

The NEI dot is the source release's facility coordinate; it is not a release point, building entrance, or verified footprint. No exact address/footprint source is present in this release, so this continuation exposes `epa-eis:<EIS ID>` as a canonical key using exact provider identity only. It preserves `[longitude, latitude]`, identifies the coordinate role and original record, and explicitly leaves verified address/footprint empty. No spatial nearest-building or fuzzy matching was added. Aggregated dots now have a separate cluster symbol with a count label and open member records; the chosen map anchor remains an actual member coordinate.

The combined **Air + sources** layer queries the existing estimate, AQS, and NEI releases independently and renders their evidence classes with separate symbols. No provider was added; inventory, measurement, and estimates remain separate, and no source contribution is inferred. The nearest-monitor estimator remains deployed because the existing development candidate did not meet its predeclared two-year rule. No new model training or performance claim is made.

Share URLs use `v=1&camera=lon,lat,zoom,bearing,pitch` with bounded WGS84/map values and rounded precision. Camera writes are debounced and replace the current history entry; filter/selection interactions retain their existing history behavior. Links restore in a fresh browser context, including the combined layer and manually moved camera. Monitor and facility selection identifiers are serialized separately from Census place IDs. Private local uploads are not included in URLs. Invalid camera state falls back to the national view.

The regional context endpoint pages all spatial-index candidates before counts and ranking. A synthetic regression with 10,005 records confirms no earlier 10,000-row page cap hides the largest record. One local Raleigh TestClient request (50 km, 2024) returned 4 monitor summaries and 181 NEI facilities in 28,766 response bytes at 132.96 ms. This single local measurement is diagnostic only, not an SLA. No second public dataset, training set, address crosswalk, facility footprint, or source-apportionment method was added.

Focused checks: `PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests/test_national_api.py`; `cd frontend && npm run build`; `cd frontend && npx playwright test tests/national-explorer.spec.ts --grep 'combined evidence|viewport aggregation|dense aggregate|back and forward'`. The coordinates in the NEI release remain unverified beyond provider records; the UI calls them approximate inventory locations.
