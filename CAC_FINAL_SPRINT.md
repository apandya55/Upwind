# CAC Final Sprint Checklist

Audit date: 25 October 2026. The working National Explorer remains the product entry point; no backend science or dataset was changed in this sprint.

## P0 — product and evidence integrity

- [x] Confirm `/` opens the National Explorer and `/explore` remains an alias.
- [x] Verify the current core workflow: search Census places, select a place, inspect its annual estimate and nearby AQS/NEI records with dates and distances, inspect limitations, compare places, and export CSV, GeoJSON, or a print snapshot.
- [x] Confirm estimate, monitor measurement, and facility inventory records are rendered as distinct evidence types.
- [x] Use the actual repository remote (`https://github.com/apandya55/Upwind`) for repository links.
- [x] Replace unsupported About copy, the invented working-group quotation, and the stale/incorrect repository links with release-backed information.
- [x] Add the portfolio, About, methodology, source links, creator credit, and current copyright year to the shared footer.
- [x] Keep the CAC handoff and AI assistance disclosure factual.
- [x] Run the backend suite, frontend production build, and browser workflows after this sprint's changes (259 backend tests; 44 Playwright tests; frontend build passed).
- [x] Check primary search, place selection, comparison, export, responsive layouts, and methodology navigation across desktop/mobile browser coverage.

## P1 — science and data extension

- [x] Inspect existing PRISM environmental-covariate comparison: the 2024 candidate improves matched pooled error but the 2025 provisional spatial-fold rule fails (3/5 wins), so it is not deployed. The existing nearest-monitor release stays unchanged.
- [x] Check the national release sources, vintages, and local data artifacts. The current product data are EPA AQS annual summaries, 2024 Census place Gazetteer and population estimates, 2023 EPA NEI facility summaries, and a PRISM annual temperature candidate used only in evaluation.
- [ ] Do not add OSM, ECHO, OpenAQ, or FIRMS records in this deadline sprint. A new integration needs documented license/provenance, deduplication and time/geography semantics, user-facing limits, and focused tests first.
- [ ] Do not claim a new model improvement: no untouched, newly separated held-out evaluation is available here. Preserve the deployed baseline and existing negative results.

## P2 — submission polish

- [x] Capture and inspect screenshots from the running app for homepage, methodology, and Explorer at desktop/mobile widths; inspect all four homepage story states. Artifacts are retained under `artifacts/` and `frontend/artifacts/qa/`.
- [ ] Verify current CAC rules, eligibility, and AI disclosure requirements against official contest materials before submission.
- [x] Record the live application demo flow in `CAC_SUBMISSION_NOTES.md`.

## Verified release facts

The local 0.3.0 Explorer release is built from 2024 Census Gazetteer points, EPA AQS annual PM2.5 summaries for 2018–2025 (2025 provisional), and 2023 EPA NEI PM2.5-PRI facility records. It contains 32,333 searchable places, 31,523 supported 2024 place-point estimates, 810 withheld places, 894 eligible 2024 AQS sites, and 76,404 mapped NEI records with coordinates. The deployed estimate assigns the nearest eligible 2024 monitor value to supported Census points. Its ±4.123 µg/m³ band is an empirical spatial out-of-fold monitor-site residual band, not a local guarantee. No new measurements, model, source attribution, field accuracy, adoption, or deployment are claimed.

Primary source and evaluation record: `docs/NATIONAL_EXPLORER_V3_RELEASE.md`. Research engine evidence and limits remain in `docs/PROGRESS.md`, `docs/SCIENCE.md`, and the versioned evaluation reports.
