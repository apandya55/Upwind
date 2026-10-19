# First local release

UPWIND helps a community campaign decide what to measure next, preserving uncertainty and practical limits. The usable release is **PM2.5 exploration + constrained monitoring design**. Atmospheric source reconstruction is a separate **experimental synthetic demonstration**.

## Supported workflow

1. Open a credential-free synthetic study or create an investigation with bounds, concern and objective.
2. Import canonical or mapped measurement/weather CSV, choose an IANA timezone for naive timestamps, and inspect invalid rows/flags without losing raw originals.
3. Explore observed monitors on a synchronized local map and UTC timeline. Optional geographic tiles have no effect on the engine.
4. Mark existing monitors, permissible candidate sites, and separate plausible source hypotheses. Record costs, power/battery, permission, safe access and availability.
5. Choose geometric spatial coverage or an experimental source-location information approximation. All methods share feasible sites, budget and equipment. Future scheduling is unavailable; the experimental window is an observed steady period of at most one hour.
6. Compare optimized, spatially spread, seeded random (20-seed statistics), and wind-corridor plans where applicable. Small candidate sets use exhaustive search; >12 use cost-normalized greedy selection, with no optimality guarantee.
7. Append follow-up readings, inspect them, rerun, and retain past comparison hashes/plans. Select a single steady window via a separate investigation for reconstruction if the campaign spans longer than one hour; the timeline filter only changes exploration, not inference inputs.
8. Save/reopen SQLite investigations. Export/restore a private full-fidelity JSON archive, normalized CSV, and a self-contained HTML evidence report suitable for browser print-to-PDF.
9. Record original resident accounts at approximate locations. Reports round those coordinates to ~1 km, but free-text notes still require privacy review.

Local report generation does not send a complaint, make a certification, or establish responsibility. Import archives include original measurements and exact private coordinates. Multiple users/accounts, encryption at rest and hosted public deployments are outside this local release.

## Explicit non-goals and gaps

- No field-validated PM2.5 source attribution, chemistry/odor identification, causal facility responsibility, real-time city coverage or health-benefit score.
- No future sampling-time optimization, weather forecast integration, live APIs, mandatory hardware, paid AI, GPU or cloud database.
- No atmospheric stability estimation, terrain/street-canyon modelling, deposition or chemical transport. Unsupported conditions refuse reconstruction; spatial planning remains available.
- No automatic calibration, arbitrary smoothing or synthetic filling of missing data.
- Leakage-controlled synthetic follow-up comparisons are now recorded in STRESS_REPORT.md; real independent-campaign/prospective placement benefit remains unproven. Weak-signal and mismatch failures are retained.
- External NOAA/EPA acquisition is blocked; the EPA adapter is contract-tested on constructed schema samples but unverified on an official downloaded archive. No external validation claimed.
- No external-user validation, outreach, adoption or competition eligibility has been established.

The area selector is explicit geographic bounds. The offline grid is a spatial canvas, not satellite imagery, surveyed boundaries or interpolated pollution. Map labels may overlap in very dense user studies; the accessible site selector provides a separate selection route.
