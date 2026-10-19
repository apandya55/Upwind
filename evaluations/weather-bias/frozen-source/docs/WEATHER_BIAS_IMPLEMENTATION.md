# Weather-bias repair: implementation and scope

Scientific model `plume-weather-0.5.0`, protocol [UW-WEATHER-2026-03](WEATHER_BIAS_PROTOCOL.md). This is a research implementation. Government, company or activist use does not establish field reliability or responsibility. Prior0.4 source and results remain under `evaluations/weather-bias/baseline-source` and `evaluations/research`.

## Confirmed cause

The previous40 biased-weather cases reproduced exactly, including18 accepted regions that all missed the simulated primary source. Accepted means conditional single-source weight≥.9, conditional90% region occupying<half the supported domain, and no withheld-block predictive warning. All40 generated cases are the denominator;18 accepted and22 abstained. Wrong means the true source's cell was absent from that region, not merely that the MAP point differed. These were synthetic campaign cases, with recorded wind systematically shifted about25° while a3° setting confined coherent integration to±6.75°. All40 raised zero predictive warnings. The detailed18 records preserve full inputs, evaluator-only truth, geometry, conditional nuisance estimates, competing source/weather components, predictive errors, area and passed rule in `reproduced/accepted18-diagnostics.json`.

The direction error was already coherent across periods in0.4. It was **not** independent per-row noise. Source position and strength could compensate for wrong wind. Held-out pollution predictions could consequently look compatible while geographic coverage failed. The rule had no independent weather evidence requirement. The repair does not change angle conventions or add concentration noise to conceal this failure.

## Actual model

`weather_evidence.py` separates a persistent direction correction b~Normal(0,20°²) and log-speed correction l~Normal(0,.2²) from declared short-period direction/speed uncertainty. These numerical priors are explicit research assumptions, not empirical weather calibration. Angular calculations use wrapped differences and periodic plume directions; the finite local Gaussian integration is approximately±3SD with at most2° spacing (or half the narrower SD). It is not a global circular likelihood for arbitrary antipodal comparisons. Antipodal comparison centers beyond90° flag a weather mismatch; no supported-location label follows. This approximation and finite prior tails can still fail under larger or changing biases.

Reference rows must be explicit measured inputs with `role=reference`, their own `source_id`, and nonempty `upstream_id` distinct from the primary's. They must state `comparison_provenance`, `direction_systematic_sd_deg`, `speed_systematic_fraction`, and random direction SD (`direction_random_sd_deg`, default2°). Metadata claims are not externally verified. A string saying “calibrated” alone never narrows the prior.

Pairing uses nearest primary timestamp, then metric distance, with limits120seconds/250metres. Comparisons more than14days from fitted campaign readings are ignored. Shared-upstream products cannot verify their own primary. Source IDs alone do not establish independence. Station bias is assumed constant during the campaign/calibration interval. Comparisons at the station cannot certify wind spatial representativeness at every pollution sensor or fix clock errors elsewhere.

For qualified direction differences d, covariance R contains primary short-period error with exp(-|Δt|/600s) correlation, independent reference random errors, and one shared systematic outer product for each upstream group. Its SD is the maximum declared systematic SD in that group; repeated products do not reduce that floor. The Gaussian update is V=(σ_b^-2+1ᵀR^-1 1)^-1, m=V1ᵀR^-1 d. Speed uses log(reference/primary), the same correlation and grouped systematic errors, plus a2% random reference-speed assumption. Relative speed SDs approximate log-scale SDs; very large fractional errors need a better measurement model. Direction unwrapping occurs about the circular mean difference. Common-bias residual χ² checks use n-1 degrees of freedom and a.005 threshold each for direction/speed; user-declared uncertainties remain conditional assumptions. A common hidden bias in two allegedly independent instruments is unobservable to this check.

The updated persistent distribution is combined in quadrature with declared short-period uncertainty and integrated as one coherent campaign wind perturbation. This conservatively does not turn independent short-period errors into independent identifiability information; it is not a resolved time-dependent wind field. Speed uses three lognormal quadrature nodes with weights1/6,2/3,1/6. Components outside the existing.8–8m/s transport support are explicitly truncated and renormalized; no feasible node refuses inference. Values at retained quadrature nodes are not physical bounds.

The source-location, positive-strength and per-window background/trend model otherwise remains0.4. Every joint source/weather component enters conditional geographic regions, predictive moments and prediction-risk design. Information design retains its documented Gaussian component approximation and finite component reduction. Pollution-conditioned wind offsets are outputs of that joint model; they are never passed back as independently measured weather evidence. Wind baseline plans may use the weather-only comparison correction available at planning time. No oracle weather enters production.

## Product and compatibility contract

Weather CSV supports the above optional canonical columns. Primary/reference readings at one timestamp/location remain distinct. Raw CSV, hash, UTC normalization, original instrument values, row origin and comparison provenance are preserved. No automatic angle/time rewriting or calibration is performed on imports.

UI, API and HTML show weather evidence status, used/ignored comparisons, weather-only correction, persistent uncertainty, separately named pollution-conditioned offset, and distances between conditional location means across the90% wind-mass set. That last span is a sensitivity description, not a confidence interval. Unknown weather remains unknown even when pollution fits are sharp. Comparison inconsistencies block the support label. The existing source-weight/region/predictive rule remains otherwise unchanged; no truth-dependent or reject-everything gate is added.

Old saved results are moved to `archived_results` on read/import, with a compatibility note and no current result. Reading does not overwrite the SQLite original. Saving persists the explicit archive and original observations. Historical `plan_history` retains its model identifiers. Reanalysis is necessary because the semantics of narrow settings changed. Cache keys include model version and a canonical configuration hash; mutable numerical configuration cannot reuse stale cached regions/plans.

There is a bounded numerical workload and an explicit128-qualified-comparison ceiling before covariance allocation. Raw rows remain retained when inference refuses. Larger imports do not imply all rows were inverted. The resource report records actual accepted shapes, memory, time and refusals.

## Planning meaning

A pollution plan adds simultaneous retrospective readings at the last observed timestamp, using `followup-{site ID}` instruments. Source information and concentration prediction remain different objectives. Existing independent weather readings are available inputs equally to applicable methods;0.4 cannot interpret the new comparison schema and retains primary values. The baseline comparison therefore includes a capability difference when paired readings exist, explicitly reported as a data-enabled improvement. A new wind instrument is not included in pollution plan costs. The product identifies the potential need for independent weather evidence but implements no free weather acquisition or forecast. The optional protocol weather-first intervention is not claimed as an implemented planner.

## Independent checks and reproduction

`backend/tests/test_weather_bias.py` checks the correlated Gaussian reference update against independent numerical integration, correction signs/speed ratios,359/1 wrapping, non-averaging shared-systematic error, missing/shared lineage, remote/asynchronous/stale references, comparison limits, CSV/raw/UTC preservation, cache invalidation, saved archives, API and escaped HTML. Existing scalar plume/positive-strength quadrature tests check the weather mixture with an independent likelihood calculation; known-weather oracles remain diagnostic only.

Commands (new output paths required):

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m pytest -q
cd frontend && npm run build && npm run test:e2e
# From repository root:
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m upwind.validation.weather_bias --split development --out .local/weather-dev
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m upwind.validation.weather_bias --split calibration --out .local/weather-cal
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m upwind.validation.weather_bias --split final --planning --out .local/weather-final
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m upwind.validation.weather_aux sensitivity --out .local/weather-sensitivity
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m upwind.validation.weather_aux resources --out .local/weather-resources
```

For reproducibility on this unborn checkout, source SHA256 manifests replace a nonexistent Git commit identifier. Split runs support `--offset`/`--limit` for disjoint sequential seed shards; aggregate all declared seeds and retain every refusal/crash. Do not pool reused condition seeds as independent campaigns.

Official NOAA DATEM/Sagebrush routes were retried and both failed proxy CONNECT403 (`evaluations/weather-bias/external-retry.json`). No compatible measured tracer data were acquired. No field validation, measured geographic accuracy or universal weather-error detection is claimed. Existing actually inspected primary-method sources remain documented in `ENGINE_RESEARCH.md`; this repair's algebra has an independent numerical reference check, not a fabricated literature validation.

## Cause classification and evidence

| Candidate cause | Finding in reproduced18 | Remaining scope |
|---|---|---|
| Wind-from/to, degrees/radians, axes, metric units | No convention defect found. West wind flows east; scalar independent kernel and90° coordinate/wind rotation checks agree, including the new chunk boundary.359°/1° difference is+2°. | These checks establish conventions, not real station accuracy. |
| UTC/timing/averaging | Reproduced inputs have aligned normalized timestamps and steady weather within each15min period; no averaging/timestamp bug explains these18. | Fresh clock-shift tests deliberately challenge observed-time matching; no automatic clock repair is inferred. |
| Station/receptor spatial mismatch | Original truth uses one spatially uniform wind and a station within support. | Fresh station-distance refusals and spatially different winds expose representativeness limits. A valid proximity check cannot certify a uniform field. |
| Shared bias treated as row noise | Not the cause:0.4 already integrates a campaign-coherent offset. | The narrow caller-supplied3° distribution excluded true weather.0.5 adds a separate persistent-bias prior, still conditional and finite. |
| Source/strength/background compensation | Confirmed. Detailed18 component/background records and independent GLS profiles show alternative source/weather explanations. | Some layouts are unidentifiable even with correct weather; adding more parameters is not information. |
| Validation/acceptance ignores weather accuracy | Confirmed. Withheld pollution sensors/periods share the same biased weather record; good predictions cannot independently verify it. | Explicit paired weather data can help. No disagreement detected is never a calibration certificate. |

Development-only free-nuisance profiles find source-center separations about412m among near-optimal wind-offset modes with all six monitors/four wind regimes; same-wind or far-four layouts admit about548m separation. These are descriptive finite-grid results with unrestricted effective strength and per-window background/trend, not confidence intervals. The original source rectangle remains full size. Correct-weather oracle regions shrink for the useful near layouts, but same-wind/far layouts can remain broad; data geometry and wind diversity matter.

In the48 development sensitivity fits, prior SD15° causes one near-four/four-wind region to miss the source where20°/30° retain it; mean location and area change with prior. This supports reporting prior dependence, not claiming20° is calibrated.1° vs2° integration and finer geographic cells agree closely on these few cases;±5° shifts and different monitor subsets can still move MAP locations. No final result selected the prior or the support rule.

To reproduce the original40/18 failure diagnoses under the preserved0.4 namespace after the schema migration, run `.venv/bin/python scripts/reproduce_weather_baseline.py --out .local/weather-baseline-recheck` with one BLAS thread. The initial actually executed script is preserved verbatim in `reproduced/script.py.txt`; the runnable command additionally strips new weather/archive fields before validating the old strict schema. It asserts every original metric within1e-10 and checks18accepted/allwrong at the full40-case default. `--limit2` is only a command preflight, never a replacement denominator.
