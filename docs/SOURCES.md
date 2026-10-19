# Sources, provenance, licenses and attribution

UPWIND combines established dispersion, Bayesian scenario comparison and experimental-design ideas. It does not claim to invent source inversion or sensor placement.

## Foundations and starting points

- Gaussian plume with ground reflection: standard atmospheric-dispersion formulation, e.g. Turner, *Workbook of Atmospheric Dispersion Estimates*, EPA AP-26 (1970); Pasquill/Gifford and Briggs rural dispersion approximations. The coefficients in this educational engine are explicitly recorded in SCIENCE.md. This is not an audited reproduction of an EPA regulatory model.
- Bayesian finite scenario likelihood, log-sum-exp weighting, covariance-based Gaussian information objectives and greedy/exhaustive design are established numerical methods. The implemented nuisance-aware moment score is explicitly approximate; no novelty or general submodularity guarantee claimed.
- EPA sensor study design: https://www.epa.gov/air-sensor-toolbox/air-sensor-use-and-study-design
- EPA sensor siting: https://www.epa.gov/air-sensor-toolbox/guide-siting-and-installing-air-sensors
- NOAA DATEM: https://www.arl.noaa.gov/research/atmospheric-transport-and-dispersion/atd-programs-datem/
- NOAA Project Sagebrush: https://ready.arl.noaa.gov/documents/Tutorial_2021/html/conc_local.html
- pyELQ (existing methane-focused inversion work): https://sede-open.github.io/pyELQ/
- openair (existing air-quality analysis): https://openair-project.github.io/openair/
- Sensor-placement research supplied in the specification: https://doi.org/10.1609/aaai.v 40i 46.41257 — unreviewed here; no claims about its contents.
- Existing community tools: https://cleanairenc.org/airkeeper-dashboard/help-center/
- PurpleAir access: https://community.purpleair.com/t/about-the-purpleair-api/7145
- OpenAQ terms: https://docs.openaq.org/about/terms
- EPA AirData hourly archive naming and format: https://aqs.epa.gov/aqsweb/airdata/download_files.html
- Current CAC rules: https://www.congressionalappchallenge.us/rules/ — must be verified before submission, including AI disclosure and eligibility.

These links are research/acquisition starting points, not endorsements or claims that primary content was reviewed. NOAA/EPA/FastAPI requests attempted here were denied by the environment proxy before content was available; actual external benchmark inspection remains outstanding. Installed package manifests, type definitions/docstrings, and execution were used to verify the APIs used in this build.

## Data

Bundled files in `examples/` and the original 24-run evaluation derive from `backend/upwind/fixtures.py`, using recorded NumPy seeds. Severe synthetic cases/follow-ups derive from `backend/upwind/validation/cases.py` and its independent scalar generator. `external.json` contains aggregate statistics from the actually inspected openair dataset, not simulated observations. The synthetic geography is near (0°,0°); names describe an imagined setting, not surveyed sites, real facilities or residences. Their labels survive UI, JSON and report exports. Hidden simulated truth is returned separately to the evaluator and omitted from the bundled investigation JSON's inferential inputs. Candidate grid includes truth in these constructed cases; this does not test off-grid accuracy.

No NOAA, EPA, OpenAQ, PurpleAir or community data have been bundled or licensed for redistribution by this project. No wind, event, adoption or partnership claim is based on invented real records. Imported files retain raw content, hashes, timezone choices and column mappings. AQS conversion preserves an original archive and writes a separate transformation manifest.

## Software and geographic context

React (MIT), Vite (MIT), TypeScript (Apache-2.0), MapLibre GL JS (BSD-3-Clause), Recharts (MIT), Lucide (ISC), FastAPI (MIT), Pydantic (MIT), NumPy/SciPy/pandas (BSD-3-Clause), pyproj (MIT), SQLite (public domain), pytest (MIT), Playwright (Apache-2.0). Exact dependency trees are in `requirements.lock` and `frontend/package-lock.json`; distributed packages carry their own notices. Review package notices before redistribution. No source image assets or proprietary basemap tiles are copied into the repository.

The default local grid has no third-party geographic content. Optional OpenStreetMap raster tiles display attribution via MapLibre; © OpenStreetMap contributors, ODbL data, subject to tile.openstreetmap.org usage policy. They are a convenience and may be unavailable; do not bulk download or assume a production tile-service agreement. Geographic context availability never changes measured readings or engine outputs.

The project owner has not yet selected a repository-wide license. Do not infer one from third-party dependency licenses.

## Severe evaluation provenance

The pinned upstream openair repository (`c2970d8c5addf68497bddaae13230167e7387651`) and `man/mydata.Rd` were actually inspected for the subsequent stress task. The documented Marylebone file contains real PM2.5/wind, but no coordinates/source ground truth; it was not fitted as an attribution benchmark. Raw files remain ignored locally pending primary-data terms review. DATASET_CATALOG.md records compatibility and access status. requirements-research.lock pins the optional pyreadr/Matplotlib reader and plotting dependencies; figure manifests record exact input hashes and versions. No numerical conclusion was generated by an LLM.

## Engine overhaul evidence

The 0.3.0 redesign's inspected primary manuscript, pinned official Stan/NOAA source revisions, licensing findings and actual acquisition failures are recorded in [ENGINE_RESEARCH.md](ENGINE_RESEARCH.md) and `evaluations/overhaul/external-access.json`. In particular, Gabry et al.'s *Visualization in Bayesian workflow* supports distinct fitted-data and held-out predictive checks; it does not certify these priors, diagnostic thresholds or field reliability. No new external scientific dependency was added. No NOAA tracer files were obtained, and no existing London data were relabeled as source-location truth.
