# National Explorer v3 release record

This is the authoritative record for the current local release. The older v1/v2 documents below describe historical snapshots and are not authoritative for current model scores or AQS event-selection semantics.

## Scope and release data

The National Explorer at `/explore` presents historical annual PM2.5 evidence. Census Gazetteer places are point locations, not polygons or area averages. EPA monitor summaries are measured at instrument sites; place values are estimates; NEI values are facility inventory emissions. These evidence types remain separate. The product does not show current conditions, personal exposure, forecasts, health effects, facility contribution, responsibility, or source attribution.

The local release was built on 2026-10-20 from official EPA and Census files:

| Data | Vintage and use |
|---|---|
| EPA AQS annual monitor summaries | 2018–2025; model target uses complete 2024 annual PM2.5 summaries, parameter 88101, annual standard, quarterly means of daily means, µg/m³. The 2025 summary is provisional. One ambient summary is selected per POC (Events Included when present, otherwise No Events); selected colocated POCs are then combined once by physical site. Event-excluded alternatives are not substituted. |
| Census place Gazetteer | 2024; 32,333 searchable place GEOIDs and internal-point coordinates. |
| Census Population Estimates Program | 2020–2024; latest available population estimate is joined by unique place GEOID. The population total counts Census place units only and does not add counties, metros, or tracts. |
| EPA National Emissions Inventory | 2023 facility summary; mapped `PM25-PRI` primary PM2.5 inventory values, in source units (`TON`), with EIS facility IDs. These are annual facility inventory estimates, not ambient concentrations. Links use the official inventory archive and preserve each record ID because no stable facility-specific URL was verified. |

The raw inputs and generated JSON release are local, ignored data artifacts. The release manifest records source URLs, vintages, and build time. Generated national source data are not bundled into the initial browser JavaScript.

## Deployed model and evidence

The deployed release is `upwind-national-explorer-0.3.0`, model `upwind-nearest-monitor-annual-pm25-0.3.0`, protocol `UW-NATIONAL-SPATIAL-2026-04`. It transfers the nearest eligible 2024 monitor value to each supported Census Gazetteer point. The deployed fit uses 894 eligible physical AQS sites and has no learned pollution covariates.

The protocol compares nearest monitor, the fixed 150 km Gaussian-kernel ridge candidate, and a Gaussian model with a linear PRISM annual-mean-temperature term. All candidates use the same spatial folds and matched sites within each year. PRISM tmean was acquired from Oregon State University's PRISM Group annual 4-km grids; monitor coordinates were sampled in the containing raster cell. The candidate fits temperature standardization, an OLS intercept and temperature slope, and the fixed Gaussian residual kernel using training-fold rows only. These are per-fold candidate fits; no persistent temperature model is deployed. The annual grid is retrospective and cannot support a beginning-of-year forecast. Protocol, source provenance, and detailed fold results are in `evaluations/national-v3/`.

| Year | Candidate | Matched sites | MAE | RMSE | Bias | Fold MAE wins vs nearest |
|---|---|---:|---:|---:|---:|
| 2024 | Nearest monitor (deployed) | 872 | 1.832 | 2.662 | −0.547 | — |
| 2024 | Gaussian, 150 km | 872 | 1.495 | 2.082 | +0.011 | 5/5 |
| 2024 | Gaussian + PRISM tmean | 872 | 1.320 | 1.859 | −0.081 | 5/5 |
| 2025 provisional | Nearest monitor (deployed method) | 882 | 1.719 | 2.366 | −0.327 | — |
| 2025 provisional | Gaussian, 150 km | 882 | 1.375 | 1.887 | −0.086 | 3/5 |
| 2025 provisional | Gaussian + PRISM tmean | 882 | 1.384 | 1.872 | −0.202 | 3/5 |

Values are µg/m³ on common rows with finite PRISM values, not the full deployment fit. The existing requirement remains at least four fold wins in both years; neither Gaussian candidate qualifies, so nearest-monitor remains deployed. These vintages and folds were already inspected and are development evidence, not an untouched final evaluation. PRISM improves the 2024 pooled score but does not pass the two-year consistency rule.

The corrected deployment band is ±4.123 µg/m³ (width 8.246), the empirical 90th percentile of corrected spatial out-of-fold nearest-monitor absolute residuals. On the matched comparison rows it covers 89.9% (784/872) in 2024 and 93.2% (822/882) in provisional 2025. The legacy ±4.059 band covered 89.4% and 93.1%. These are observed monitor-site coverages, not local guarantees or Bayesian credible intervals. No untouched final set or independent between-monitor field validation is established.

### AQS event-selection correction

Inspection found that the prior builder could average alternative event treatments when a POC had no “No Events” summary, and could select a site-level “No Events” row while dropping ambient “Events Included” rows from other POCs. EPA defines event treatments as alternative summaries, not independent instruments. The corrected builder selects exactly one ambient summary per POC: “Events Included” where available, otherwise “No Events”; event-excluded rows are never substituted. It then averages selected colocated POCs once per physical site. The 2024 selection changed 80 site-year means (mean absolute shift 0.035 µg/m³; maximum 3.615); 2025 changed 57 (0.014; maximum 1.291). No site-year lacked a selected ambient POC. Raw row provenance and selected POC/treatment/certification/completeness metadata remain in the release. Old and corrected audits are retained separately in the v3 evaluation artifacts.

## Coverage and counts

The checked local release contains 32,333 unique searchable place GEOIDs; 31,523 have a 2024 estimate and 810 are withheld under the current contiguous-U.S. domain and monitor-distance support rule. The 31,523 estimates are nearest eligible monitor values assigned to Census Gazetteer points, with their supporting monitor and distance retained. Population coverage sums the latest available 2024 Census estimate for each unique modeled place GEOID with a population value: 213,515,188. This is geographic population coverage, not people reached, exposure, usage, adoption, or impact. There are 894 eligible 2024 physical monitor sites. The 2023 NEI release contains 76,404 mapped PM2.5-PRI facility records with coordinates; facility records and process/release-point rows are counted and described according to the source audit, not interpreted as ambient causes.

Coverage measures searchable places, places with supported model estimates, monitor proximity, and population sum separately. A monitor within 5 km of a Gazetteer point is only a proximity proxy, not proof the monitor is within a legal boundary. The geography uses distinct Census place units and does not add overlapping county, metro, or tract populations.

## API, snapshot, and performance

The API reads generated release files from `data/national/release/`; model fitting happens offline. Existing manifest/place/monitor/source routes remain. Viewport queries use a one-degree index, exact totals, bounded pages and offsets; facility counts are distinct EIS facilities. Snapshot JSON, CSV and GeoJSON are release-aware and draw from a consistent file set. They include selected places or an explicit missing estimate and reason, WGS84 coordinates and point meaning, model and empirical interval interpretation, supporting monitor, population vintage, nearby inventory records, source vintages, limitations and release identity. CSV protects spreadsheet formula cells. GeoJSON uses WGS84 `[longitude, latitude]`. Print output uses the same JSON snapshot data as the visible selected place and comparisons.

On 2026-10-20, six sequential requests per endpoint were measured against a fresh local API process on this machine; medians and response bytes were: manifest 1.10 ms/14,534 B; Raleigh, NC search 3.74 ms/992 B; a 1.5° × 1.2° central-NC place viewport 2.67 ms/78,717 B; monitor viewport 1.57 ms/2,769 B; facility viewport 14.39 ms/164,656 B; and a one-place Raleigh snapshot JSON/CSV/GeoJSON 29.67/29.51/29.57 ms at 6,124/4,963/6,467 B. Snapshot generation includes nearby-facility lookup. These local single-user timings are not an SLA.

The generated release totals 74,172,726 JSON bytes (70.7 MiB; 71 MiB on disk): places 26,588,659 B, monitors 4,953,624 B, facilities 42,345,729 B, and supporting manifests/models/reports 284,714 B. The production `frontend/dist` totals 1,894,140 B. The initial entry is 222.35 kB minified/69.79 kB gzip; the Explorer route is lazy-loaded at 57.81 kB/17.56 kB gzip, with MapLibre split into deferred 344.43 kB and 1,054.12 kB chunks (100.78 kB and 285.42 kB gzip). The national JSON remains server-side and is not shipped in the browser bundle. Vite warns that the 1.05 MB minified MapLibre chunk exceeds its default 500 kB advisory threshold.

## Run and reproduce

From the repository root, with Python/Node dependencies installed:

```sh
.venv/bin/python scripts/build_national_dataset.py --start-year 2018 --end-year 2025
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/evaluate_national_v2.py
.venv/bin/python scripts/evaluate_national_v3.py
PYTHONPATH=backend .venv/bin/uvicorn upwind.api:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/explore`. The acquisition pipeline caches official source archives under ignored `data/national/raw/`, records hashes/retrieval metadata, validates inputs, and writes the local release. `evaluate_national_v2.py` rebuilds the selected nearest-monitor deployment. `evaluate_national_v3.py` reproduces the bounded environmental candidate comparison and audits the AQS event-selection correction; it does not switch the deployed model. For Vite development, run the API separately, then:

```sh
cd frontend
UPWIND_API_URL=http://127.0.0.1:8000 npm run dev -- --port 5174
```

## Verification

The focused national API/data/evaluation checks passed (19 tests); the integrated backend suite passed **250 tests** in 296 seconds. The production TypeScript/Vite build passed. All nine Playwright National Explorer workflows passed: place search/comparison, keyboard and URL state, back/forward restoration, JSON-backed CSV/GeoJSON/print snapshot, explicit withheld values and snapshot failures, per-layer truncation notices, mobile viewport behavior, corrected event-policy and matched-PRISM methodology, failed map-data requests, and failed basemap tiles. Snapshot JSON, CSV and GeoJSON were separately requested from the live local release and returned matching selected-place content and release identity. The measured release manifest identifies the 0.3.0 release/model and 32,333 searchable places; 31,523 estimates, 810 withholds, 213,515,188 covered population and 894 eligible 2024 physical monitors. The test run emitted one existing Starlette/httpx deprecation warning; the build retains Vite's advisory about the deferred 1.05 MB MapLibre chunk.

## Known limitations

No untouched final monitor set, independent between-monitor measurements, or field validation is available. Available monitor-site spatial folds show weak transfer skill for the deployed nearest-monitor method, and the broad empirical residual band does not provide a local guarantee. PRISM is a tested candidate but is not deployed under the existing selection rule. Census point estimates are not place averages. Source inventory proximity is not ambient contribution or responsibility. The local source data and API are not a public deployment, and no deployment or outreach is claimed.
