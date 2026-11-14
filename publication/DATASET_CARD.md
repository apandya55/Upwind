---
language:
- en
tags:
- air-quality
- environmental-science
- tabular
- pm25
size_categories:
- n<1K
configs:
- config_name: default
  data_files:
  - split: train
    path: upwind_nc_air_quality.parquet
---
# UPWIND North Carolina annual PM2.5

160 physical station-year observations at 23 EPA AQS stations, 2018–2025. This is an observational dataset, not a machine-learning training split; `train` is the Hub loading convention only. Use station-grouped spatial holdouts for evaluation.

PM2.5 is in µg/m³ at local conditions. Colocated POCs are combined upstream; one row represents one physical site-year. Annual periods must not be interpreted as hourly measurements or AQI. All three weather columns are null in this snapshot. The 2025 observations are provisional.

See DATA_DICTIONARY.md for column definitions and null rules, BENCHMARKS.md for the fixed regional evaluation, and evaluation.json for subgroup results and station-cluster uncertainty. Retain upstream attribution to U.S. EPA AQS. Apache-2.0 applies to UPWIND software, not a blanket relicensing of source observations. No endorsement, causal traffic attribution, school exposure estimate or health guidance is implied.

Source code: https://github.com/apandya55/Upwind . Regenerate with `scripts/publication_release.py` and the publication dependency lock. The archive includes input and output checksums.
