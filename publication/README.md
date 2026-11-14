# UPWIND annual evidence release — 2026-11-14

## Reproduce

Use Python 3.12. From the extracted archive or repository:

```sh
python -m venv .venv
.venv/bin/python -m pip install -r requirements-publication.lock
.venv/bin/python scripts/publication_release.py
```

This command uses the bundled national cleaned EPA snapshot, selects NC, exports Parquet, evaluates spatial holdouts, generates the three-page report, runs release integrity tests and packages an archive under artifacts/. It does not download new observations or publish remotely. The input and split are fixed; measured latencies and generated PDF metadata can vary. The archive's SHA256SUMS.json validates the exact deposited bytes.

Full national acquisition remains `scripts/build_national_dataset.py`; raw archive URLs and ingestion rules are in that script. The bundled input is a cleaned derivative, not raw EPA observations. The annual release covers 2018–2025; 2025 is provisional. A physical monitor may contain multiple colocated instruments.

## Scope and evidence

Software version 0.1.0; evidence snapshot 2026-11-14. National production estimates use the nearest eligible monitor. NC evaluation uses spatially held-out one-degree cells, with station identity held constant across years. Candidate methods are evaluated without tuning. `release/evaluation.json` adds a training-mean baseline, errors by county, year and distance, and station-cluster bootstrap intervals. These results apply to the NC experiment. They do not replace the national evaluation. Spatial dependence between neighboring stations is not eliminated by station-cluster resampling.

The school-corridor report is an annual evidence-gap study: no hourly commute, AQI spike, road-buffer, school exposure or causal claim is supported. Weather columns are null unless explicitly supplied.

## Zenodo deposit

Upload artifacts/upwind-annual-evidence-2026.zip. Suggested title: **UPWIND: reproducible annual PM2.5 exploration and North Carolina spatial evaluation**. Creator: Arnav Pandya. Resource: software. Use CITATION.cff for citation metadata. Describe the software Apache-2.0 license separately from source-data notices below. Record the actual Git commit and release tag when depositing; the current working tree may include unpublished edits. Do not invent a DOI. After publication, add the issued DOI to CITATION.cff and the public methodology page.

## Hugging Face dataset repository

Copy `publication/DATASET_CARD.md` as README.md and upload `release/upwind_nc_air_quality.parquet`, DATA_DICTIONARY.md, BENCHMARKS.md, `release/evaluation.json`, and the report. This is a dataset, not a trained model. Use a separate software repository link. Do not describe absent weather fields as measured meteorology.

## Source and rights notices

EPA AQS observations are attributed to the U.S. Environmental Protection Agency; original source: https://aqs.epa.gov/aqsweb/airdata/download_files.html . EPA data are not authored by UPWIND, and the software license does not relicense upstream material. No endorsement is implied. This NC package contains no OSM geometry, Census population or NEI facility data; their separate terms apply to other UPWIND products. Consult upstream notices when redistributing those products.

## Engineering case study

UPWIND separates monitor readings from place estimates and emissions records. Input checks catch bad records, and the downloads include source details and evaluation results.

Pipeline: EPA annual archives → eligibility/event/POC normalization → physical site-year release → held-out spatial evaluation → Parquet + report → static public downloads.

Resume wording: “Built UPWIND, an open-source PM2.5 explorer with validated EPA ingestion, spatial holdout evaluation, reproducible Parquet exports, and a checksummed publication pipeline; released a 160-observation, 23-station North Carolina evidence dataset.” Only say “released” after publishing. The results do not establish a health benefit or a better model.

## Deployment boundary

The publication command prepares local assets. Deploy the frontend using the existing documented production workflow with VITE_SITE_URL set to the real origin. Verify `/research/`, report links, and dataset downloads on the deployed origin before announcing the release. This archive does not include the full national deployment data or raw archives; follow DEPLOYMENT.md in the source repository for the explorer deployment.

The workflow also creates `artifacts/huggingface/` with a ready-to-upload dataset card, Parquet, documentation, evaluation and PDF. Upload that folder's contents as the root of the dataset repository. `publication/zenodo-metadata.json` provides a suggested software-deposit metadata payload; it contains no placeholder DOI or release identifier.
