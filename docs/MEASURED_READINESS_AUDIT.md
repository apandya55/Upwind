# Measured-data readiness audit

2026-10-18 (America/New_York). The user selected measured-data validation as the next priority. **No measured localization or prediction accuracy result is established by this audit.** It found and inspected a secondary Prairie Grass workbook, but primary provenance, missing metadata and model compatibility prevent treating it as a benchmark. The scientific model and all frozen0.5 results remain unchanged.

## Access and source findings

The saved environment configuration already listed NOAA/EPA, yet a live NOAA request still failed at proxy CONNECT403. Configuration and runtime reachability are different evidence. Public GitHub web pages and native Git worked. An initial batch of GitHub searches hit429; search stopped and a later single README search succeeded. No authentication, TLS or rate-limit bypass was used.

Four repositories were inspected at pinned revisions without running their code:

| Source | Revision | Finding |
|---|---|---|
| [NOAA HYSPLITDATA](https://github.com/noaa-oar-arl/hysplitdata) | `757f7ced24a446ba5de92040b915fdc7acf5ae03` | File-reading library and HYSPLIT output fixtures, not a measured controlled-release archive. |
| [pyELQ](https://github.com/sede-open/pyELQ) | `c845e37a7410e5fcf3b2f7d77876c00007290e6f` | The inspected basic notebook explicitly generates synthetic concentrations/weather. Its Apache2.0 code license and references do not turn those examples into measurements or establish rights to external datasets. |
| [Gas dispersion catalog](https://github.com/DreamCatcher096/Gas_dispersion_datasets) | `6f2a1d35e6696ece2fe1f98fcda1b097b4f797de` | Secondary links to primary documentation; no data files. Led to Aarhus University and HARMO. |
| [Prairie Grass modelling assignment](https://github.com/Reinenornormey/Gaussian-plume-model) | `6fd4a0892481e25171f3c4c6efe3114448bd4674` | README plus one Excel workbook. Contains purported observations, modelled outputs and calculation sheets; no standalone dataset license. |

[Exact request/source/hash record](../evaluations/measured-readiness/access-and-sources.json). Raw files and web responses stay in ignored local storage. Only our own audit code, aggregate metadata and hashes are committed. No upstream code, workbook formula, macro or external connection was executed.

## Prairie Grass candidate: concrete compatibility findings

The workbook SHA256 is `96a6cb7812d9a618fd50c1266ce7943acfe91c3ae339f60d9d130653f9b61887`. Its layout concerns experiment21 and five sampling arcs. A column labelled as observed is still an **unverified purported observation** until its measurement lineage is checked. Modelled columns are never included as observations, even when their cells contain constants rather than formulas.

| Arc sheet | Purported observation constants | Modelled constants, excluded | Explicit observation unit | Values above500µg/m³ if the unit label is correct |
|---|---|---|---|---|
|50m|21|21|Not stated (`Co`)|Not calculated|
|100m|16|16|g/m³|12|
|200m|12|12|g/m³|10|
|400m|10|10|g/m³|7|
|800m|15|15|g/m³|11|

There are74 purported observation constants in total. Unit labels on four arcs cover53values;40of those would exceed the current app's500µg/m³ review/exclusion threshold after the explicit g→µg conversion. The50m unit is not inherited from another sheet. This is a compatibility count, not an accuracy result or a claim that these are verified valid observations.

The workbook labels its release constant50.9g/s, equivalent to50,900,000µg/s. That is about1,697times the frozen model's HalfNormal strength-prior scale30,000µg/s. This is a scale comparison to a workbook assertion, not independently verified release truth. Blindly fitting these data with that prior would not provide a fair physical test. Dividing the measurements to obtain a convenient answer would invalidate the experiment.

The workbook also supplies source-height wind≈4.447m/s, release height0.46m and receptor height1.5m as constants. The wind is part of a modelling assignment and cannot be assumed an independent instrument observation; uncertainty and derivation must be checked. The stability sheet describes “Weakly stable (neutral),” which does not establish compatibility with a neutral kernel. Verified time basis, complete source/receptor coordinate frame, wind direction, observation units on every arc and primary measurement documentation remain unresolved.

This SO2 tracer experiment would test a separately documented tracer transport application. It cannot directly establish PM2.5 source responsibility in urban terrain. One inspected experiment is also not a campaign-level calibration/final split. Treat experiment21 and this workbook as development-used; do not relabel them an untouched final set later.

Disposition: **not ready for measured validation**. No model fit, localization score, calibrated coverage rate, planner benefit or field certification is reported. The machine-readable [candidate audit](../evaluations/measured-readiness/prairie-candidate.json) retains the counts and blockers.

## Reproduce the audit

The auditor uses only the Python standard library and reads pinned Git objects. It never imports upstream code, evaluates formulas or writes observation exports. It refuses overwriting an audit. Use a new destination:

```sh
git clone --no-checkout https://github.com/Reinenornormey/Gaussian-plume-model.git .local/prairie-audit-NEW
.venv/bin/python scripts/audit_prairie_candidate.py \
  --checkout .local/prairie-audit-NEW --out .local/prairie-audit-NEW.json
.venv/bin/python -m pytest -q backend/tests/test_prairie_audit.py
```

The fixed revision is embedded in the script; later branch updates cannot silently change the audit. Eleven tests use constructed OOXML fixtures to check observation/model separation, non-inherited units, cached formulas, nonnumeric/nonfinite cells, external/escaping relationships and size refusal. No actual measurements are bundled as fixtures. [Focused log](../evaluations/measured-readiness/pytest-audit.log) and [full backend log](../evaluations/measured-readiness/pytest-full.log) retain actual outcomes:11focused checks and162full-suite tests passed. Original scientific-source/artifact verification remains available through `scripts/verify_weather_release.py`.

## External prerequisite and next experiment

The actual catalog links identify:

- [Aarhus University Prairie Grass page](https://envs.au.dk/en/research-areas/air-pollution-emissions-and-effects/the-monitoring-program/air-pollution-models/background-info/omlprairie).
- [HARMO Prairie Grass discussion](https://www.harmo.org/jsirwin/PrairieGrassDiscussion.html) and [referenced original report](https://www.harmo.org/jsirwin/PGrassVolumeI.pdf).

Live requests to the first two returned CONNECT403. A network draft adding only`envs.au.dk` and`www.harmo.org` was saved while retaining all eight existing custom domains and the platform presets. The configuration tool reported`requires_publish: true`. **Review and save the changes in environment settings, then publish the environment.** Saving a draft does not update the current proxy; no post-publication connectivity is claimed. Existing NOAA/EPA runtime denials may need separate environment troubleshooting even though those domains are already listed. Do not disable TLS or extract proxy credentials.

Once access is applied, inspect the actual documentation links and terms before downloading primary files; do not invent archive URLs. Preserve source archives/hashes and measured versus modelled distinctions. Establish units, release history, geometry/heights, sampling/averaging intervals, meteorology/stability and clock basis before building a benchmark. Keep source truth in an evaluator only. Define a new protocol and model identifier for any tracer-specific prior, quality policy or transport change; retain0.5 as the baseline. Declare untouched campaign-level splits before using further observed outcomes for selection. If files remain incompatible, report the refusal and its denominator rather than generating replacement observations.
