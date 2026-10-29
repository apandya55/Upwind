# Congressional App Challenge — Submission Notes

## One-sentence description

UPWIND is a public atlas for exploring historical annual PM2.5 estimates, EPA monitor measurements, and emissions inventory records across U.S. Census places while keeping their provenance and limitations distinct.

## Intended audience

Residents, students, researchers, and community groups who want to inspect public air-quality records and understand where estimates are supported or withheld. The release is an exploration tool; it does not provide personal exposure, health-risk, regulatory, or source-attribution conclusions.

## Architecture

- React 19, TypeScript, Vite, and MapLibre GL provide the browser interface and map.
- FastAPI serves local, prebuilt release data and bounded national viewport/search/snapshot endpoints.
- The offline Python data pipeline uses official EPA and U.S. Census source files; it records source URLs, vintages, build details, and input hashes in the release manifest.
- The deployed place method assigns the nearest eligible annual AQS summary to supported Census Gazetteer internal points. The separate experimental source-localization engine is not the National Explorer's place-estimation method.

## Three technical challenges

1. **Keeping unlike evidence separate.** Annual monitor measurements, place-point estimates, and annual facility inventory emissions have different units and meanings. The interface and snapshots label them separately; nearby inventory records do not imply contribution to ambient concentration.
2. **Handling monitor and event-selection provenance.** AQS summaries can have multiple parameter occurrence codes and event treatments. The build selects one ambient summary per POC and combines selected colocated POCs once per physical site, retaining the selected provenance.
3. **Withholding unsupported estimates.** The release keeps places searchable while withholding predictions outside its domain or monitor-distance support rule. It reports the reference monitor and distance and describes the empirical residual band as evidence from monitor sites, not a local guarantee.

## Original technical work represented in the repository

The project includes a reproducible EPA/Census release pipeline, an audited AQS event-selection policy, spatial-fold comparisons between a nearest-monitor baseline and Gaussian/PRISM candidates, release-aware search and viewport endpoints, bounded layer rendering, and JSON/CSV/GeoJSON/print snapshots that preserve provenance and limitations. The PRISM candidate is not deployed: although its matched 2024 scores improved, the provisional 2025 result did not meet the release's four-of-five fold-win rule. Results are development evidence, not a fresh untouched final validation.

## Suggested 1–3 minute demonstration

1. Open UPWIND at `/` and search for Durham, North Carolina.
2. Select the Census place result. Point out the 2024 estimate, empirical band, supporting AQS monitor, and distance. Explain that this value is assigned to an internal point and is not a citywide measurement.
3. Open nearby documented evidence. Compare the dated AQS annual summaries with EPA NEI inventory records, including their distances and different units. State explicitly that proximity does not show source contribution.
4. Toggle the monitor and inventory layers, then open methodology to show the model choice, spatial-fold comparison, data vintages, and limits.
5. Export the selected-place snapshot as CSV or GeoJSON (or open the print brief) and point to its source and release metadata.

This workflow uses current release data; do not present hypothetical results as live measurements.

## AI assistance disclosure

Development was AI-assisted. `docs/AI_ASSISTANCE.md` records the scope of assistance and cautions about scientific and authorship claims. The submitter should review and accurately describe their own work, verify contest rules, and disclose AI assistance in the format required by the current official challenge rules. Do not describe generated code or results as exclusively hand-written or independently reviewed.

## Known limits and future work

- No independent between-monitor field validation, personal exposure estimate, current-condition feed, health interpretation, source responsibility, or regulatory attribution is established.
- The nearest-monitor estimate is geographically simple; evaluated Gaussian and PRISM candidates did not satisfy the existing deployment rule.
- The ±4.123 µg/m³ band is a spatial out-of-fold monitor-site residual quantile and does not guarantee local coverage.
- Census Gazetteer internal points are not place boundaries or population-weighted averages. 810 places have no supported 2024 estimate.
- The local dataset release is not a hosted public deployment. Additional transportation/regulatory/fire datasets require a separate provenance, licensing, temporal-alignment, and validation review.
- CAC eligibility, submission requirements, and current AI-disclosure rules need confirmation from official contest materials before submission.

## Run locally

Install the repository's pinned dependencies and follow `README.md` (`bash scripts/setup.sh`, then `bash scripts/dev.sh`). The app opens at `http://127.0.0.1:5173`; national data generation and evaluation commands are documented in `docs/NATIONAL_EXPLORER_V3_RELEASE.md`.
