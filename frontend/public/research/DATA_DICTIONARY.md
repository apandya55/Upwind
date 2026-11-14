# UPWIND NC data dictionary

One row per physical EPA station and calendar year; sorted by year then ID. Parquet uses ZSTD and stores no dataframe index. Dates label annual periods, not instantaneous samples. Identifiers preserve leading zeros. Missing optional data are Arrow null, never zero or a sentinel. No rows are dropped for missing weather. See BENCHMARKS.md for ingestion filters and exact counts.

| Column | Arrow type | Definition | Unit | Null handling |
|---|---|---|---|---|
| id | string | Physical EPA AQS site identifier; colocated POCs are combined | identifier | Required; invalid source row rejected |
| state_fips | string | State FIPS, 37 for North Carolina | code | Required; invalid source row rejected |
| county_fips | string | Five-digit state + county FIPS | code | Required; invalid source row rejected |
| site_number | string | Four-digit AQS site number | code | Required; invalid source row rejected |
| year | int64 | Annual observation year | year | Required; invalid source row rejected |
| period_start | date32[day] | Inclusive January 1; annual period label | date | Required; invalid source row rejected |
| period_end_exclusive | date32[day] | Exclusive January 1 of following year | date | Required; invalid source row rejected |
| latitude | double | Station latitude, WGS84 | degrees north | Required; invalid source row rejected |
| longitude | double | Station longitude, WGS84 | degrees east | Required; invalid source row rejected |
| pm25_ug_m3 | double | Mean of eligible colocated POC annual PM2.5 summaries | µg/m³, local conditions | Required; invalid source row rejected |
| poc_count | int64 | Number of selected colocated instruments, not independent sites | count | Absent source value remains null |
| sample_completeness | string | EPA completeness indicator; required Y | flag | Required; invalid source row rejected |
| event_treatment | string | Selected ambient event treatment(s), preserved from ingestion | text | Absent source value remains null |
| pollutant_standard | string | EPA annual PM2.5 standard selected during ingestion | text | Absent source value remains null |
| metric | string | EPA aggregation metric: Quarterly Means of Daily Means | text | Required; invalid source row rejected |
| evidence_type | string | Source observation classification | text | Required; invalid source row rejected |
| temperature_c | double | Annual mean air temperature | °C | Null without matching annual weather or when source value missing; never imputed |
| relative_humidity_pct | double | Annual mean relative humidity | % | Null without matching annual weather or when source value missing; never imputed |
| wind_speed_m_s | double | Annual mean scalar wind speed | m/s | Null without matching annual weather or when source value missing; never imputed |

Optional weather CSV must contain `id`, integer `year`, and all three weather columns. Values must be numeric or empty; infinities, humidity outside 0–100%, negative wind speed, missing keys, and conflicting site-years abort. Exact duplicate rows are collapsed. The caller is responsible for annual aggregation and weather provenance. Weather is exported but is not used in the coordinate-only benchmark.
