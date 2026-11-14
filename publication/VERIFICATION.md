# Local release verification — 2026-11-14

- Full backend suite: **233 passed**, 274.38 seconds. One dependency deprecation warning from Starlette's httpx test client; no failed tests.
- Publication gate: **7 passed** (deduplication, invalid records, weather joins, spatial holdout separation, Parquet ZSTD, three-page PDF, public artifact parity, report checksums, evaluation identity).
- Public browser suite: **3 passed, 1 skipped**. The skipped case requires an externally configured API origin; it is not evidence of deployed API availability. Local preview logged connection refusals for the absent API, while static downloads and report navigation passed.
- Production build: passed with VITE_SITE_URL=https://upwind-explorer.vercel.app; public-surface verification passed. Existing bundle-size advisory remains.
- Extracted publication archive: checksums verified and publication command completed from a separate directory. Evaluation prediction tables matched the original exactly. Same installed locked Python environment was used; no claim of independent operating-system reproduction is made.
- Archive member hashes verified. Exact deposited bytes are identified by SHA256SUMS.json, with base Git revision and uncommitted status in BUILD_PROVENANCE.json.
- The dependency lock is included; the publication job is configured in CI. Remote CI execution is not claimed by these local results.

## Remaining external release actions

Commit and tag the reviewed working tree, deploy the website changes, then upload the Zenodo archive and Hugging Face folder. Verify deployed download URLs after deployment. Add the assigned DOI and dataset URL to citation metadata and the evidence page after publication. No remote publication, deployment, DOI assignment or Git tag was performed by the packaging command.

The scientific scope is annual EPA PM2.5 observations and regional spatial validation. Hourly AQI, school exposure, commute-window and highway-buffer validation remain outside the supported claims.
