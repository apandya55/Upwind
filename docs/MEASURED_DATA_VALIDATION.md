# Measured-data validation status and intake

2026-10-18 (America/New_York). Scientific model remains **plume-weather-0.5.0**. This continuation repairs the EPA archive intake tool; it changes no inference, weather prior, support rule, planner or held-out evaluation. The [published synthetic results](WEATHER_BIAS_RESULTS.md) and their failures still apply.

## What was established

The prior adapter deleted an existing destination before validating the archive, appended selected chunks directly to the final CSV, and could delete a good export in its CLI exception handler. A later incompatible row could therefore destroy earlier work or leave a partial conversion. Existing sidecar provenance could also describe different output bytes.

`scripts/acquire_aqs.py`, identifier `aqs-intake-1.0.0`, now validates in a private staging directory beside the destination. It refuses existing CSV, sidecar and download destinations, including broken symlinks. It publishes using exclusive same-filesystem hard links, preventing a competing conversion from replacing an existing file. The sidecar reserves the basename before the complete CSV appears; publication failure removes only that conversion's own sidecar. Raw archives are never modified. Both archive and CSV SHA256, adapter source hash and version, selected dates/state, archive member and quality counts are recorded.

This is not a filesystem transaction across two files. A process or machine failure between publication steps can leave an orphan sidecar. Treat an export as complete only when **both files exist and the CSV hash matches the sidecar**; do not delete an unexplained sidecar automatically. Hard links require filesystem support. Power-loss durability and network-filesystem guarantees were not established. Concurrent writers to one basename are refused; separate processes should use separate output names.

## Declared input contract

The following is tested on **constructed fixtures**, not an acquired EPA archive. A future real file must still be inspected against official documentation, terms and actual columns; the tool refuses deviations rather than inferring replacements.

| Field | Required meaning / handling |
|---|---|
| State/County/Site/POC | Decimal instrument identifiers; county/site/POC are nonzero. State/county/site padding is explicit. POC remains part of the instrument ID. |
| Date GMT / Time GMT | Valid YYYY-MM-DD and24-hour HH:MM; combined as UTC with no inferred timezone or shifted dates. Selection is inclusive by UTC date. |
| Parameter Code | Exactly88101; another parameter cannot be relabelled PM2.5. |
| Sample Duration | Exactly`1 HOUR`; no daily-to-hourly conversion or interpretation as instantaneous concentration. |
| Units of Measure | Exactly`Micrograms/cubic meter (LC)`; no mixing-ratio or standard-condition conversion. |
| Datum | Exactly`WGS84`; NAD83 or unspecified coordinates require separate verified transformation. |
| Latitude / Longitude | Finite, within the application's supported±85°/±180° coordinate range. |
| Sample Measurement | Finite numeric value. Negative and>500µg/m³ values are retained and counted for review, not erased or rescaled by this adapter. |
| Qualifier / method / uncertainty | Preserved when present. Source uncertainty is retained as declared text, not silently assigned a statistical interpretation. |

CSV headers must be unique and nonempty; record widths must match exactly. No inferred index, filled short row, duplicate-header renaming, fabricated coordinate, imputation or synthetic fallback is permitted. Archive selection requires one CSV member. Downloads/archives are bounded to1.5GB and uncompressed input to8GB. Streaming conversion uses100,000-row chunks; this is an intake bound, not the app's10,000-row-per-import or512-row inference capability. Malformed selected metadata abort the whole conversion. Qualifier counts and preserved raw metadata require operator review; conversion does not establish that every record is scientifically usable.

## Use with an independently obtained archive

```sh
.venv/bin/python scripts/acquire_aqs.py \
  --archive /path/to/hourly_88101_2024.zip --year 2024 \
  --state 37 --start 2024-06-01 --end 2024-06-01 \
  --out .local/aqs-review-NEW.csv
```

Choose a new output path every time. Explicit downloading remains available with`--download`; an existing archive is retained, so omit`--download` when reusing it. Start/end years must match`--year`. No credentials are required by this offline conversion. A caller-provided provenance URL and a hash establish neither official authenticity nor licensing.

Verify a completed pair before importing:

```python
import hashlib, json
from pathlib import Path
csv_path = Path(".local/aqs-review-NEW.csv")
metadata = json.loads(csv_path.with_suffix(".provenance.json").read_text())
assert hashlib.sha256(csv_path.read_bytes()).hexdigest() == metadata["output_csv_sha256"]
```

Keep the original archive and sidecar. In the app create a non-synthetic investigation, retain source/method/qualifier notes and review quality exclusions. Hourly ambient measurements provide no known source location or independent weather. Do not derive source truth from nearby facilities or feed this archive directly into a claimed localization benchmark.

## Verification and current blocker

The focused37checks include the existing importer round trip plus36new contract/fault cases: later-chunk failure, malformed dates/units/datum/parameter/duration, nonfinite values, mismatched record widths, duplicate headers, empty selection, existing files/symlinks, concurrent converters, publication rollback, changed archives, interrupted/oversized/invalid downloads and retained qualifiers. All fixtures are explicitly constructed. Full backend results are in [pytest.log](../evaluations/aqs-intake/pytest.log); no frontend code changed. `scripts/verify_weather_release.py` still verifies the exact frozen0.5 scientific source and all original evaluation counts/artifacts.

[Current access audit](../evaluations/aqs-intake/external-access.json): NOAA programme/tutorial, Zenodo catalog, GitHub search API and EPA archive HEAD requests all returned proxy CONNECT403. Native GitHub Git publication remains available; that does not imply GitHub search API or third-party data access. No new observations or official archive body were acquired, and no measured accuracy result exists. These are environment access errors, not evidence that the sources require a paid service or personal token.

The next external prerequisite is access to an official dataset or an independently obtained archive plus its documentation/terms. For a localization benchmark, additionally verify release schedule/strength, source and receptor geometry/heights, local meteorology/conventions, units, averaging intervals, stability and clock alignment. Keep release truth exclusively in the evaluator. Before scientific selection, declare campaign-level development/calibration/final splits and a fresh protocol; previously inspected synthetic seeds cannot become fresh validation. Any controlled-tracer result remains distinct from urban PM2.5 responsibility or prospective planner benefit.
