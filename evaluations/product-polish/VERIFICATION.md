# UPWIND product polish verification

Run date: 2026-10-21. Measurements use the built national release and local browser environment. They are not service-level guarantees.

## Map query comparison

Old `/api/national/places?limit=3000` response was row-capped; the endpoint returned 3,000 of 31,523 national place estimates without claiming completeness. New `/api/national/viewport` filters first, aggregates every matching row into stable Web Mercator cells, and coarsens deterministically to a 300-symbol budget. Cluster membership sums to `represented_records`; coincident rows stay inspectable through the paged member API. Layer, year, pollutant, viewport, requested zoom, grid level, dataset identity, and aggregation version travel with the response.

Warm request measurements (three requests per case; median wall latency):

| View/layer | Before | After symbols / represented rows | Response bytes | Median |
|---|---:|---:|---:|---:|
| National estimates | 3,000 / 31,523 (truncated) | 20 / 31,523 | 4,633 | 84.1 ms |
| National monitors | — | 14 / 872 | 3,047 | 2.9 ms |
| National NEI source rows | — | 19 / 75,405 | 3,865 | 129.7 ms |
| Los Angeles estimates | 143 / 143 | 8 / 143 | 3,836 | 1.2 ms |
| Los Angeles monitors | — | 4 / 9 | 1,043 | 0.8 ms |
| Los Angeles source rows | — | 10 / 1,950 | 2,665 | 3.6 ms |

The old limit was in the API response before the map renderer. It silently omitted place rows from the national display. New map queries use indexed geographic buckets, post-filter by the exact viewport bounds, and aggregate the complete filtered result. Requests start after `moveend` plus a debounce; abort signals and request sequence checks prevent stale responses from replacing newer ones. Existing data remains visible during refresh. Only the active data layer is fetched.

There was no live before-change browser server at implementation start, so no comparable before-change interaction latency or recording exists. Browser verification measured correctness and behavior, not frame rate. No synthetic performance figures are reported.

## Repeatable interaction sequence and results

Environment: local release data, local API and Vite server, Playwright Chromium. The automated sequence covers national overview, city search, local zoom and repeated drag-pan, selected-place details, cluster member inspection, layer switching, reset, share/export, and mobile layout. Browser tests assert the full filtered count is represented and viewport symbols stay within 300, clusters page exact members, and stale responses cannot overwrite current results.

- National overview: 20 symbols represented 31,523 estimated locations; 4,633-byte viewport response; 84.1 ms median warm API latency.
- Los Angeles local view: 8 symbols represent all 143 matching estimated locations.
- Dense coincident group: clicked aggregate exposes a count and pageable member rows; 114-member example is captured.
- Movement: five-step zoom, three repeated drag-pans, zoom-out/reset, and rapid-pan stale-response check pass.
- Request behavior: one debounced request per settled movement; previous in-flight request is aborted when a newer settled view starts. No requests are sent each movement frame.
- Observed defects fixed: map aggregation badge used the viewport-relative position against a page without a positioning context; selection/pan timing made evidence screenshots capture an unsettled camera; tablet controls overflowed instead of wrapping. The map instance and native GeoJSON layers are retained while data changes.

## Visual review

Sol opened and inspected the final browser captures at 1440×900, 1280×800, 768×1024, and 390×844. The status badge stays on the map, tablet controls wrap, place details remain readable in a desktop independently scrolling panel, and the mobile selection becomes a bottom sheet. The landing page now presents the mission, real product preview, evidence limits/statistics, workflow, and local-data entry; the previous decorative scene was removed. Screenshots:

- [Explorer overview](screenshots/explorer-overview.png)
- [Dense local map](screenshots/explorer-dense-local.png)
- [Place details](screenshots/explorer-details.png)
- [Cluster member list](screenshots/cluster-members.png)
- [Mobile bottom sheet](screenshots/explorer-mobile-sheet.png)
- [1280×800](screenshots/explorer-1280x800.png)
- [768×1024](screenshots/explorer-768x1024.png)
- [Landing hero](screenshots/landing-hero.png)
- [Landing evidence and workflow](screenshots/landing-evidence.png)

Playwright video recording was not configured in this checkout; the repeatable interaction sequence is retained as a test rather than a video.

## Checks

- `PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests/test_national_api.py backend/tests/test_national_dataset.py`: 17 passed.
- `cd frontend && npm run build`: passed; Vite reports the existing 1,054 kB MapLibre chunk warning.
- `cd frontend && npx playwright test --config playwright.polish.config.ts tests/national-explorer.spec.ts`: 14 passed.
- Full polish browser/capture suite: 15 passed (includes viewport captures and the landing story route).
- `git diff --check`: passed.

Map tiles depend on OpenStreetMap network access. The displayed estimates remain historical Census-place point predictions, monitoring values remain measured site summaries, and NEI source values remain annual inventory estimates; the UI preserves these distinctions and does not imply source attribution.
