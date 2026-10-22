# UPWIND National Explorer

The National Explorer is a historical PM2.5 atlas at `/explore`, separate from the archived experimental inverse source-localization workflow. It does not estimate source responsibility, personal exposure, current air quality, or future conditions.

This page retains the historical v1 baseline and data-acquisition notes. The current local release, corrected AQS processing, candidate evaluation, API behavior and verification are documented in [NATIONAL_EXPLORER_V3_RELEASE.md](NATIONAL_EXPLORER_V3_RELEASE.md); use that page for present release claims. All model metrics and counts below describe the superseded v1 snapshot.

## Run locally

From the repository root, acquire/build the local release and run the app:

```sh
.venv/bin/python scripts/build_national_dataset.py --start-year 2018 --end-year 2025
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/evaluate_national_v2.py
.venv/bin/uvicorn upwind.api:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/explore`. For frontend development, run Vite with `UPWIND_API_URL=http://127.0.0.1:8000 npm run dev -- --port 5174` from `frontend`. Downloads are cached under ignored `data/national/raw/`; derived release files under ignored `data/national/release/`. The scripts validate archives before replacing cached files, resume partial downloads, record SHA-256 hashes and retrieval metadata, and atomically publish derived JSON files. Re-running the same commands uses cached downloads. There is no visitor-side model training or account requirement.

## Data included in the current local release

- EPA AirData annual monitor summaries for 2018–2025. There are 6,763 deduplicated site-years; 2024 was selected for modeling with 894 eligible sites. The target is parameter 88101, PM2.5 annual standard, “Quarterly Means of Daily Means,” completeness indicator `Y`, in µg/m³. Colocated POCs are combined to one site-year and their identifiers retained. EPA’s 2025 archive is included for monitor context and is treated as provisional in this release.
- 2024 Census Gazetteer: 32,333 searchable place records with stable GEOIDs, Census place types, and internal-point coordinates.
- Census 2020–2024 place population estimates, joined by state/place GEOID. The join succeeds for 19,479 places (60.2%); most unmatched records are geographies for which this PEP table has no place estimate. Population coverage sums 2024 estimates for the 30,610 supported, unique modeled place GEOIDs that have a published value: 211,733,693. This is geographic coverage, not users or impact. The sum uses Census place units only; county, metro, and tract populations are not added. Census balance-place GEOIDs are retained as their own residual units.
- EPA 2023 NEI facility emissions summary. The pipeline retains 76,404 records with usable coordinates from 77,976 primary-PM2.5 rows (`PM25-PRI`, filterable plus condensable) and reports emissions in the source unit, tons. It excludes component species, filterable-only rows, PM10 and precursor pollutants. 1,572 rows have missing or invalid coordinates/emissions and are not mapped. EIS facility IDs are unique in the retained data. Inventory values are facility-level annual inventory estimates, not ambient measurements; nearby distance does not establish contribution or responsibility.

The Gazetteer supplies point locations, not place polygons. A “monitor nearby” count is a site within 5 km of a Gazetteer internal point, not a claim that a monitor is inside a legal boundary. There is no county-AQI layer in this release. The map currently displays modeled place estimates, measured monitor summaries, or documented facility inventory points as separate layers.

## Model, evaluation, and limits

The target is 2024 annual PM2.5 concentration in µg/m³. The candidate Gaussian radial-basis ridge model uses only latitude and longitude. Bandwidth is selected among 50, 100 and 200 km on development folds. Evaluation holds out fixed 2-degree geographic cells as groups: 565 development sites, 163 calibration sites, and 166 final-test sites, with one site-year per physical AQS site and no site leakage across folds. The calibration block sets the 90th-percentile absolute residual band and 90th-percentile supported monitor distance before final-test results are used.

On final test, RBF MAE/RMSE were 1.095/1.529 µg/m³. Nearest-monitor MAE/RMSE were 1.122/1.539; regional-mean MAE/RMSE were 1.286/1.597. RBF-minus-nearest paired differences were −0.027 µg/m³ MAE (state-cluster 95% bootstrap interval −0.204 to 0.171) and −0.010 RMSE (−0.275 to 0.224). Both intervals include zero, so the atlas deploys the nearest eligible monitor baseline. R² is −0.039 for that selected method. The weak R² means the simple transfer does not explain held-out geographic concentration variation well; the small numerical RBF improvement is inconclusive.

The selected method’s separate calibration block gives a symmetric empirical 90% residual band of ±3.91 µg/m³ (full width 7.82). Its observed coverage on final test was 95.8% (159/166). This is a broad empirical error band, not a Bayesian interval or individual exposure uncertainty. Selected-method final-test MAE/RMSE, bias, and R² by region, concentration bin, and distance to training monitor are in `data/national/release/model_report.json`.

The deployment refit uses all 894 eligible 2024 sites after evaluation. It publishes 30,610 place estimates and withholds 1,723 places outside the calibration-derived monitor-distance support or the contiguous-U.S. geographic rule. Search also includes Alaska, Hawaii, DC, and territories; those remain searchable and their monitor observations are available, but the first place-estimate release does not cover them. The model is trained only for 2024. Earlier/later years in the selector are monitor observation years; a place estimate is not presented for those years.

This is spatial interpolation evaluated on one held-out year, not temporal forecasting or independent measured validation between monitors. The RBF and baseline have negative final R², the geographic fold has sparse subregions, and the reported interval is wide. Coordinate-only modeling has no weather, elevation, land cover, population-density, chemical-composition, or emissions predictors. No result establishes current conditions, personal exposure, health risk, causation, source attribution, or field accuracy. The source-localization engine remains archived experimental research and is not used by the atlas.

## UI and API

The map is MapLibre GL with OpenStreetMap raster tiles. If tiles are unavailable, the map shows an explicit fallback; search, evidence details, and exports continue to work. The client requests place, monitor, and source features for the current viewport. Place search uses name and state; selecting a Census place point, monitor point, or facility point opens its distinct evidence record. Place comparisons persist in local browser storage. The URL retains the selected place, year, and layer.

Exports include spreadsheet-safe CSV with reference-monitor details, GeoJSON with evidence metadata, and a print-ready browser report. The API is under `/api/national/manifest`, `/places`, `/monitors`, and `/sources`. Full release data remain local and are generated from the documented official sources; raw archives and derived JSON are intentionally excluded from version control.

## Verification

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONPATH=backend .venv/bin/python -m pytest -q
cd frontend && npm run build && npm run test:e2e
```

Browser tests use ports 8001/5174 and isolated local storage/data as configured in `frontend/playwright.config.ts`. The National Explorer route is loaded as a separate chunk; see v2 documentation for current bundle measurements.

This page records the v1 baseline and acquisition contract. The current candidate protocol, model, coverage counts, uncertainty labels, and implementation details are in [National Explorer v3](NATIONAL_EXPLORER_V3_RELEASE.md). `scripts/train_national_model.py` reproduces the historical v1 release; use the v3 release record for the current local build and evaluation commands.
