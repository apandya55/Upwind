# External-data acquisition and exact blocker

On 2026-10-18 the environment's egress proxy returned **HTTP 403 on CONNECT**, before any source file could be inspected, for:

- `ready.arl.noaa.gov`: `https://ready.arl.noaa.gov/documents/Tutorial_2021/html/conc_local.html`
- `www.epa.gov`: `https://www.epa.gov/air-sensor-toolbox/air-sensor-use-and-study-design`
- `aqs.epa.gov`: `https://aqs.epa.gov/aqsweb/airdata/hourly_88101_2024.zip`
- `fastapi.tiangolo.com`: tutorial documentation.

This is an environment network-policy response, not evidence that NOAA/EPA require credentials or that a specific dataset is unavailable publicly. No authentication was requested or fabricated. Required custom domain additions are listed in environment settings; they must be applied before retrying those acquisitions. GitHub and public package registries worked. No TLS, signature or checksum verification was disabled.

## NOAA DATEM / Project Sagebrush

Starting sources: https://www.arl.noaa.gov/research/atmospheric-transport-and-dispersion/atd-programs-datem/ and the tutorial URL above. **Actual files, license, release heights/histories, coordinate system, tracer units and usable meteorology have not been inspected.** Therefore no compatible file adapter or tracer validation is claimed. A tracer experiment is not independent urban PM2.5 validation even if later fitted successfully. Next: acquire official files, inventory units and release geometry, reject incompatible unsteady/calm cases, keep true release coordinates exclusively in an evaluator, then predeclare campaign/time splits before inference.

## EPA AQS hourly PM2.5

Adapter: `scripts/acquire_aqs.py`, now `aqs-intake-1.0.0`. It validates UTC dates/times, finite concentrations, coordinates, units, parameter88101, hourly duration and explicitly declared WGS84. It retains instrument IDs, qualifiers, source metadata and hashes. It stages the entire conversion and refuses existing destinations; a late failure cannot overwrite a previous export. Use a new output path for each run. The [intake contract and failure checks](MEASURED_DATA_VALIDATION.md) are tested on constructed fixtures, **not an actual EPA archive**. Real archive compatibility/licensing review and meaningful external evaluation remain unverified.

```sh
# Explicit download can be large; source archive retained in .local.
.venv/bin/python scripts/acquire_aqs.py --download --year 2024 \
  --state 37 --start 2024-06-01 --end 2024-06-01 --out .local/aqs-pm25.csv

# Or use an independently obtained official archive, without network access:
.venv/bin/python scripts/acquire_aqs.py --archive path/to/hourly_88101_2024.zip \
  --state 37 --start 2024-06-01 --end 2024-06-01 --out .local/aqs-pm25.csv
```

Create a **new**, non-synthetic investigation, import the CSV, retain its sidecar provenance and original archive, and record instrument/method/qualifier interpretation in Data quality notes. Use exploration and spatial coverage first. Hourly time-labelled instrument averages are not guaranteed compatible with the steady instantaneous plume approximation. AQS measurements provide neither known source coordinates nor facility responsibility. Do not manufacture source-truth evaluation from nearby facilities.

EPA terms/provenance must be checked from official pages before redistributing real files. No external data are committed. Network errors produce a failed acquisition; there is no simulated substitute.

## Subsequent measured-data audit

The severe stress task acquired the real openair Marylebone example through its upstream GitHub repository, inspected its documentation and 65,533 records, and retained hashes/statistics without redistributing raw files. Missing verified coordinates prevent spatial inference; those rows were rejected rather than assigned guessed sites. This does not remove the official NOAA/EPA access blocker or establish independent source validation. See DATASET_CATALOG.md and STRESS_REPORT.md. Additional UCI/UK/London domain requirements were saved in the environment draft; draft persistence alone does not apply runtime access.
