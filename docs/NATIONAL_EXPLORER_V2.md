# National Explorer v2

The current release and verification handoff is [NATIONAL_EXPLORER_V3_RELEASE.md](NATIONAL_EXPLORER_V3_RELEASE.md). Everything below is a historical v2 snapshot; its scores and release counts are superseded by v3. In particular, v3 corrected AQS exceptional-event selection and recalculated the evaluation and uncertainty band.

At the v2 snapshot, evidence labels, spatial holdout design, uncertainty provenance, and request size were improved. The v3 release retains nearest-monitor deployment because the fixed spatial candidates did not meet the existing consistency rule across both available years. The inverse source-localization engine remains separate from this Explorer.

## Data and estimand

The target is annual PM2.5 in µg/m³ from EPA AQS parameter 88101, the annual standard, “Quarterly Means of Daily Means,” with sample-completeness flag `Y`. This historical v2 release retained colocated POC provenance but predates the corrected ambient event-selection rule. The v3 release selects one summary per POC (Events Included when present, otherwise No Events) and never substitutes event-excluded alternatives. 2024 supplies the deployed estimate; 2025 annual summaries are provisional and are used only as supplementary candidate-development evidence. These are monitor-site summaries, not daily values, personal exposure, or a temporal forecast.

Place predictions are at the Census Gazetteer internal point. No place polygons are in this release, so values are point estimates and cannot be called citywide, neighborhood, or area averages. Each estimate shows its distance to the nearest eligible 2024 AQS site and the site ID/value used for comparison. A monitor within 5 km of a Gazetteer point is a proximity measure, not proof that it lies within the place boundary.

EPA NEI 2023 data contain 77,976 `PM25-PRI` (filterable plus condensable) facility-summary rows; 76,404 have usable coordinates and valid emissions values. The 76,404 mapped EIS IDs are unique in this release, so these are not 76,404 duplicate display points. The inventory labels them facility-level annual values in `TON`; they do not include PM10 or precursor pollutants in this layer. The UI reports EIS ID, `PM25-PRI`, vintage, source category, amount, units, and distance. Facility links point to EPA's official inventory download, not a facility-specific record page; the source archive has no verified stable per-row URL in this release. Nearby records are ranked by reported PM2.5-PRI emissions within the loaded viewport. Proximity is not evidence of contribution or responsibility.

Dataset vintages, source URLs, retrieval metadata, and hashes are in `data/national/release/manifest.json`. Raw source files and derived releases remain ignored local artifacts. Refreshes are resumable through the existing acquisition script; model processing stays offline and outside request handlers.

## Candidate protocol and results

Protocol `UW-NATIONAL-SPATIAL-2026-02` was written before its candidate run in `scripts/evaluate_national_v2.py`. It assigns each AQS site ID once to a deterministic fold based on its first recorded coordinate's 10° latitude/longitude cell, so all 6,763 rows for the 1,161 physical site IDs retain the same fold. There are no IDs with changing reported coordinates in this release. Five folds are fit and scored separately within each year; no site-year from a held fold enters that fold's fit. Distances use haversine geometry. The fixed candidates are nearest monitor, 4-neighbor inverse-distance weighting with power 2, and 150 km Gaussian-kernel ridge with ridge 1.0. No hyperparameter sweep or population/emissions proxy is used. Coordinates are the only features. The Gaussian model uses training rows only; there is no learned preprocessing.

The 2024 data and v1 test summaries had already been inspected, so all v2 folds are development evidence. No untouched final set is claimed. Fold IDs are spatial cells but neighboring cells can land in different folds; this design does not provide a geographic buffer, and nearby-border leakage can make errors optimistic. The 2025 archive is provisional, not independent field validation. No compatible, provenance-verified elevation, land-cover, road, meteorology, or satellite predictor was available locally; a nonlinear environmental model was therefore not fit. Census population and facility proximity are not pollution substitutes.

| Year | Method | Held-fold sites | MAE | RMSE | Bias | R² vs training-fold mean |
|---|---|---:|---:|---:|---:|---:|
| 2024 | Nearest monitor | 894 | 1.773 | 2.524 | −0.514 | −0.479 |
| 2024 | IDW, k=4, p=2 | 894 | 1.583 | 2.200 | −0.130 | −0.123 |
| 2024 | Gaussian kernel, 150 km | 894 | 1.492 | 2.077 | −0.000 | −0.001 |
| 2025 provisional | Nearest monitor | 907 | 1.721 | 2.357 | −0.288 | −0.539 |
| 2025 provisional | IDW, k=4, p=2 | 907 | 1.573 | 2.102 | +0.060 | −0.223 |
| 2025 provisional | Gaussian kernel, 150 km | 907 | 1.405 | 1.921 | −0.086 | −0.022 |

The Gaussian kernel wins MAE in 5/5 2024 folds but only 3/5 2025 folds, below the declared requirement of at least 4/5 in both years. Nearest-monitor therefore remains deployed. The 2024 nearest-monitor R² is negative against the training-fold mean: its squared error is greater than predicting the training mean on these geographic folds. It is not calculated against the held-out test mean. The old v1 166-site result (MAE 1.122, RMSE 1.539, R² −0.039 against the old test-set mean) is retained only in the local historical artifact `model_report_v1_historical.json`; it was previously inspected and is not fresh validation.

The selected model is refit on all 894 eligible 2024 sites. Its symmetric ±4.059 µg/m³ band is the 90th percentile of absolute geographic out-of-fold nearest-monitor residuals. This is a broad monitor-site error summary, not a Bayesian interval or locally guaranteed coverage. The model withholds a place if it is outside the declared continental-U.S. rectangle or farther than the out-of-fold 90th-percentile nearest-monitor distance (1,303.8 km). Places beyond the out-of-fold 75th-percentile distance (719.6 km) remain visible as low-evidence estimates. These cutoffs describe observed monitor geometry; they do not guarantee local performance. Per-fold values, input hash, and deployment details are in `data/national/release/model_report_v2_development.json`.

## Coverage and interpretation

The local release has 32,333 searchable Census places. It publishes 31,523 estimates and withholds 810 under the current domain/distance rule. Available 2024 population estimates for those unique place GEOIDs sum to 213,515,188. This is geographic population coverage, not users, adoption, exposure, or impact. The count differs from v1 because support is recalculated from spatial out-of-fold distances under the v2 fold design. Alaska, Hawaii, DC, and territories remain searchable; the model domain is the contiguous-U.S. rectangle.

Every mapped monitor is labeled measured. Place values are labeled estimated or low-evidence estimate; unsupported places have no colored prediction. The UI reports the estimate point, year, units, model, 90th-percentile OOF error band, nearest monitor and distance, and explains what the model uses. Historical monitor values remain measured monitor summaries and are not replaced with predictions. Comparisons use a common year/method and state when places share the same nearest monitor; overlapping broad bands make their ordering uncertain. The quick comparison includes Charlotte, Durham, Raleigh, and Denver.

CSV and GeoJSON include GEOID, state/type, estimate coordinates, year, source vintages, estimate, interval, evidence status, model ID, nearest-monitor details, population if present, up to four nearby inventory records, generation time, and limitations. The browser print report is the shareable community snapshot; its values come from the displayed selected place/comparison. NEI data source links and facility metadata remain explicit.

## Runtime and reproduction

The initial Explorer requests only the manifest and any URL-selected place/comparison. Map movement sends viewport bounds. Place queries return at most 3,000 map points, monitor queries at most 10,000 rows, and facility queries at most 3,000 rows ordered by reported primary-PM2.5 emissions; responses report totals and truncation. A cached one-degree in-memory index avoids rescanning all 76,404 facility rows after first use. The Explorer is a lazy route chunk, separating MapLibre and Recharts from the investigation workspace's initial JavaScript.

From the repository root:

```sh
.venv/bin/python scripts/build_national_dataset.py --start-year 2018 --end-year 2025
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/evaluate_national_v2.py
PYTHONPATH=backend .venv/bin/uvicorn upwind.api:app --host 127.0.0.1 --port 8000
```

For the historical v2 snapshot, the model report command wrote deployment `model.json`, place estimates and release counts, preserving the older report as `model_report_v1_historical.json`. `scripts/train_national_model.py` reproduces v1. Use the v3 release record and its commands for the current local release.

Focused checks:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests/test_national_api.py backend/tests/test_national_v2_eval.py
cd frontend && npm run build && npm run test:e2e -- --grep "National Explorer"
```

The previous 2018–2025 monitor archives, Census places/population, and NEI facility summaries were acquired from official EPA/Census sources. No data acquisition or independent field validation is pending for this local implementation. A clean final evaluation on newly collected/untouched monitor geography and a facility-specific EPA record URL remain unresolved. No measured between-monitor accuracy, temporal forecast skill, population impact, emissions contribution, causal attribution, or operational reliability is established.
