# Dataset compatibility catalogue

Many air-quality datasets exist. They answer different questions: **known controlled releases** can test transport/localization if their physics and units match; **monitoring networks** can test imports and prediction/placement if outcomes are withheld; a concentration record near a facility is not source ground truth.

| Dataset / campaign | What it could test | Gate before using this engine | Inspected here |
|---|---|---|---|
| NOAA DATEM / Project Sagebrush | Controlled outdoor tracer transport and release-location reconstruction | Inspect actual release histories/heights, receptor heights, mass/mixing-ratio units, local weather and stability; fixed H=5m/z=2m may be incompatible | Official tutorial and DATEM requests blocked by proxy CONNECT 403; no files inspected |
| Project Prairie Grass (DATEM) | Established short-range controlled-release dispersion benchmark | Actual geometry, source height, stability and tracer units must be verified; never assume a PM2.5 equivalence | Candidate only; catalogue/files unverified due access |
| Kincaid (DATEM) | Challenge a model with elevated-source dispersion | Elevated-release/longer-range conditions are outside this fixed-height short-range baseline; use as a rejection/mismatch case unless a separate model is implemented | Candidate only; files not acquired |
| MUST / Joint Urban tracer experiments | Expose effects of obstacles, street canyons and complex transport | Current open-terrain plume must not be presented as a valid urban reconstruction model; verify campaign access/licensing and actual files first | Research candidates, not acquired or validated |
| EPA AQS / AirData hourly PM2.5 | Real measurement quality, held-out site/time prediction and retrospective placement | Preserve coordinates, instrument/POC, units and qualifiers; needs an honest availability-time split. Source attribution has no supplied independent truth | Official archive/index CONNECT 403; existing adapter contract-tested only |
| UCI Beijing Multi-Site Air Quality | Multiyear network quality, missingness, and temporal/site holdouts | Verify original files, station coordinates and local timestamps; compass wind categories require documented uncertainty, not invented precise angles | Official UCI page CONNECT 403; no official data acquired |
| UK AURN / London monitoring networks | Multi-station retrospective exploration/prediction/placement | Acquire station metadata and verify meteorology representativeness, averaging periods, terms and campaign splits | Station metadata destinations CONNECT 403 |
| openair `mydata` / London Marylebone | Real PM2.5/wind distributions, missingness, UTC conversion and import refusal with absent metadata | One urban station; no coordinates in the file, no known release, no valid localization benchmark | **Acquired and inspected at a pinned upstream revision** |
| OpenAQ aggregated observations | Broader import/metadata/held-out-network robustness | Source-specific licenses, coordinates, averaging units, API access/terms and possible duplication require verification | Not acquired; no access/credential or source-accuracy claim |

Primary starting sources: [NOAA DATEM](https://www.arl.noaa.gov/research/atmospheric-transport-and-dispersion/atd-programs-datem/), [Sagebrush tutorial](https://ready.arl.noaa.gov/documents/Tutorial_2021/html/conc_local.html), [EPA AirData](https://aqs.epa.gov/aqsweb/airdata/download_files.html), [UCI multi-site dataset](https://archive.ics.uci.edu/dataset/501/beijing+multi+site+air+quality+data), [openair source](https://github.com/openair-project/openair), [UK AURN metadata source used by openair](https://uk-air.defra.gov.uk/openair/R_data/AURN_metadata.RData), [OpenAQ terms](https://docs.openaq.org/about/terms). Uninspected candidates are not evidence of model performance or confirmed current licensing/access.

## Actual measured data inspected

Repository `openair-project/openair`, revision `c2970d8c5addf68497bddaae13230167e7387651`, `data/mydata.rda`. Upstream `man/mydata.Rd` explicitly documents hourly Marylebone observations, PM2.5 in µg/m³, wind in m/s and direction from north. R POSIXct dates were read with `pyreadr timezone=UTC`; no naive local timestamps were guessed.

- 65,533 hourly rows, 1998-01-01 through 2005-06-23; 56,758 nonmissing PM2.5 readings and 8,775 missing values. PM2.5 median 20, 99th percentile 58, maximum 398 µg/m³.
- 808 records lack one or both wind fields; 583 recorded speeds are below 0.8 m/s and 5,557 above 8 m/s. 1,377 directions use 360°, physically equivalent to 0°. The importer now records that normalization explicitly.
- All 65,533 rows were exercised in seven bounded import batches **with missing coordinates left blank**. All were rejected for incomplete spatial input, raw originals were preserved, and no sites were invented. This is a tested failure-closed data contract and descriptive data audit, **not a passed real-data source-model evaluation**.
- One site cannot independently localize a source under this application's minimum sensor contract; urban roadside observations do not meet an open-neutral-terrain assertion automatically. Multiple years also cannot be passed as one ≤1-hour steady window.
- Data SHA256: `f40da24c7855076874d04dfc13e612d53313d029fe3c24692bff73d19d92fc38`. Exact metadata/statistics and documentation hash are in the stress results' `external.json`.

No upstream R code was executed. The package carries an MIT license, but the primary London data redistribution terms were not independently verified, so raw data remain in ignored local storage. The reproducible evaluator acquires the pinned Git repository, checks its revision and records content hashes; the report commits metadata and aggregate results, not raw observations.

## Precise acquisition blocker and next action

The platform Git proxy could read public GitHub checkouts, while official NOAA/EPA/UCI/UK/London metadata destinations returned CONNECT 403. This does not establish that a token or paid service is necessary. Current runtime egress must allow `ready.arl.noaa.gov`, `www.arl.noaa.gov`, `aqs.epa.gov`, `archive.ics.uci.edu`, `uk-air.defra.gov.uk`, and `londonair.org.uk` before compatible primary-file acquisition can be retried. Draft domain entries do not establish live access. No tracer/field localization error can be reported until actual compatible files and independent truth are inspected.
