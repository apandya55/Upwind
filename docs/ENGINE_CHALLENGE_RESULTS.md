# Independent engine challenge results

The redesign is a research prototype. This independent synthetic challenge does not establish reliable source localization or a consistent advantage for its measurement recommendations. Broad regions, missed sources and missed model failures are reported alongside prediction and software checks.

## Frozen experiment and provenance

Protocol: **UW-OVERHAUL-2026-01**; model: **plume-mixture-0.3.0**. The final experiment contains **400 condition-worlds across 40 paired seed blocks**, with 40 worlds per condition. Reusing a seed across conditions makes their worlds dependent; the reported Wilson intervals concern each condition separately. It does not create 400 independent campaigns. The placement experiment contains 36 condition-worlds across 12 paired seed blocks, 24 methods per world (864 outcomes). Random seeds and repeated measurements are not extra independent campaigns.

The final asymmetric layout, wind-direction regime and stretched-exponential dispersion family were held out from development and calibration. Sources are continuous and almost surely between the old anchors. The independent generator uses different lateral shape/growth, release height and sub-window wind averaging from inference. It remains an idealized open-terrain transport challenge; it is not field validation. The condition name `strong_signal` denotes the higher release range (18,000–36,000 µg/s), and does not guarantee that its held-out sensor layout intercepts a strong plume.

[Predeclared protocol](ENGINE_EVALUATION_PROTOCOL.md) · [Final metadata and code hashes](../evaluations/overhaul/new-final/metadata.json) · [All source outcomes](../evaluations/overhaul/new-final/science.json) · [All placement outcomes](../evaluations/overhaul/new-final/followup.json) · [All perturbations](../evaluations/overhaul/new-final/stability.json) · [Evaluator-only truth and latent fields](../evaluations/overhaul/new-final/truth.json)

Final before/after source hashes match: **True**. No final outcome informed a model change. Priors and numerical settings were fixed before evaluation. The preserved baseline is loaded as an isolated package from `evaluations/overhaul/baseline-source`; it does not inherit redesigned quality, weather or numerical functions.

## Retention and localization

Errors below are metres, shown as 10th percentile / median / 90th percentile. Both estimators are reported: a MAP point can be unstable in a diffuse distribution, while a posterior mean can lie between modes. Neither is an attribution claim. Background-only cases have no source-localization target.

| Condition | New retained / generated | Legacy MAP error p10 / median / p90 | New cell MAP error p10 / median / p90 | New conditional-mean error p10 / median / p90 |
|---|---:|---:|---:|---:|
| background_only | 40/40 | — | — | — |
| weak_signal | 40/40 | 92 / 210 / 344 | 86 / 216 / 316 | 40 / 91 / 119 |
| strong_signal | 40/40 | 115 / 228 / 368 | 83 / 168 / 279 | 38 / 87 / 112 |
| direction_bias | 40/40 | 159 / 255 / 333 | 110 / 193 / 294 | 36 / 97 / 120 |
| two_sources | 40/40 | 115 / 203 / 298 | 70 / 174 / 275 | 34 / 84 / 116 |
| boundary | 40/40 | 27 / 265 / 490 | 62 / 207 / 423 | 177 / 217 / 256 |
| correlated_errors | 40/40 | 134 / 234 / 369 | 108 / 186 / 284 | 29 / 92 / 118 |
| episodic | 40/40 | 109 / 237 / 368 | 92 / 195 / 279 | 37 / 92 / 116 |
| missingness | 40/40 | 135 / 225 / 368 | 83 / 184 / 290 | 40 / 89 / 109 |
| unsupported_weather | 0/40 | — | — | — |

A post-hoc no-data reference is necessary to interpret the conditional mean: the source-domain centroid alone has median error **89.9 m** in the interior-source families and **218.4 m** at the boundary. The redesigned conditional mean is often close to this prior center. Its sub-100 m median therefore does not demonstrate learned localization. This reference did not change any production calculation, metric threshold, final outcome or selected plan; [the calculation is saved separately](../evaluations/overhaul/new-final/posthoc-prior-reference.json).

The old model has a discrete grid; its scenario set has no geographic area and is not assigned an invented area or continuous-location coverage. New regions are unions of complete midpoint-quadrature cells accumulating at least 90% of the *conditional single-source* mass. Their meaning is conditional on that explanation and the assumed model, not 90% responsibility or a calibrated geographic probability. Coverage in two-source worlds refers only to the primary source under a false one-source model.

| Condition | New nominal 90% region coverage | Median region area (m²) | Median fraction of domain | Median source-model weight |
|---|---:|---:|---:|---:|
| background_only | — | 140272 | 86.2% | 0.435 |
| weak_signal | 34/40 (85%; 95% CI 71–93%) | 140085 | 86.0% | 0.437 |
| strong_signal | 39/40 (98%; 95% CI 87–100%) | 139713 | 85.8% | 0.456 |
| direction_bias | 35/40 (88%; 95% CI 74–95%) | 140458 | 86.3% | 0.441 |
| two_sources | 39/40 (98%; 95% CI 87–100%) | 138036 | 84.8% | 0.502 |
| boundary | 37/40 (92%; 95% CI 80–97%) | 140458 | 86.3% | 0.450 |
| correlated_errors | 36/40 (90%; 95% CI 77–96%) | 136360 | 83.8% | 0.539 |
| episodic | 36/40 (90%; 95% CI 77–96%) | 140085 | 86.0% | 0.445 |
| missingness | 39/40 (98%; 95% CI 87–100%) | 141948 | 87.2% | 0.465 |
| unsupported_weather | — | — | — | — |

Large regions are loss of usefulness, not successful precision. Coverage must be read together with area, source-model weight and source misses. Unsupported-condition refusals stay in the retention denominator. The high-confidence-error definition was fixed before outcomes: source-model weight >0.9, region covering <25% of the domain, and truth outside the region. An absence of that event is not evidence that broad regions or source probabilities are calibrated.

## Source detection and adequacy diagnostics

| Condition | False source alarms (background only) | Source misses (weight <0.5) | Sharp wrong region | Predictive mismatch warnings |
|---|---:|---:|---:|---:|
| background_only | 0/40 (0%; 95% CI 0–9%) | — | — | 0/40 (0%; 95% CI 0–9%) |
| weak_signal | — | 39/40 (98%; 95% CI 87–100%) | 0/40 (0%; 95% CI 0–9%) | 0/40 (0%; 95% CI 0–9%) |
| strong_signal | — | 29/40 (72%; 95% CI 57–84%) | 0/40 (0%; 95% CI 0–9%) | 0/40 (0%; 95% CI 0–9%) |
| direction_bias | — | 36/40 (90%; 95% CI 77–96%) | 0/40 (0%; 95% CI 0–9%) | 0/40 (0%; 95% CI 0–9%) |
| two_sources | — | 20/40 (50%; 95% CI 35–65%) | 0/40 (0%; 95% CI 0–9%) | 0/40 (0%; 95% CI 0–9%) |
| boundary | — | 32/40 (80%; 95% CI 65–90%) | 0/40 (0%; 95% CI 0–9%) | 0/40 (0%; 95% CI 0–9%) |
| correlated_errors | — | 16/40 (40%; 95% CI 26–55%) | 0/40 (0%; 95% CI 0–9%) | 10/40 (25%; 95% CI 14–40%) |
| episodic | — | 36/40 (90%; 95% CI 77–96%) | 0/40 (0%; 95% CI 0–9%) | 0/40 (0%; 95% CI 0–9%) |
| missingness | — | 34/40 (85%; 95% CI 71–93%) | 0/40 (0%; 95% CI 0–9%) | 0/40 (0%; 95% CI 0–9%) |
| unsupported_weather | — | — | — | — |

The warning is a leave-one-sensor-out predictive screen, not an adequacy certificate. A missing warning in direction-bias, two-source or episodic worlds is a missed failure of the assumed physical explanation, even when the readings are observationally compatible with the simpler model. A warning on a no-source/single-source world is a possible false alarm. The preserved baseline has no background-only family, so source-presence false-alarm/miss rates are undefined for it.

## Held-out sensor prediction

An entire sensor is withheld and its index cycles across worlds. Adjacent readings from that sensor never enter the fitted input. Table values are means across world-level scores. Predictive intervals include component observation variance and the declared Gaussian moment approximation to integrated strength; they are not just posterior-mean spread.

| Condition | RMSE legacy → new (µg/m³) | NLPD legacy → new | 90% interval coverage legacy → new | Mean interval width legacy → new (µg/m³) |
|---|---:|---:|---:|---:|
| background_only | 2.63 → 1.48 | 2.72 → 1.93 | 75.0% → 96.9% | 7.20 → 6.95 |
| weak_signal | 2.25 → 1.51 | 2.55 → 1.96 | 80.0% → 97.5% | 7.05 → 6.96 |
| strong_signal | 2.78 → 1.43 | 2.82 → 1.92 | 68.8% → 97.5% | 6.90 → 6.98 |
| direction_bias | 2.78 → 1.58 | 2.78 → 1.98 | 68.8% → 95.0% | 6.64 → 6.97 |
| two_sources | 3.17 → 1.84 | 3.21 → 2.12 | 59.4% → 91.9% | 6.49 → 6.99 |
| boundary | 2.71 → 1.57 | 2.77 → 1.99 | 71.2% → 95.6% | 6.82 → 6.94 |
| correlated_errors | 3.78 → 2.66 | 3.61 → 2.62 | 56.2% → 82.5% | 6.91 → 7.49 |
| episodic | 2.73 → 1.44 | 2.77 → 1.91 | 71.2% → 96.9% | 6.96 → 6.95 |
| missingness | 2.32 → 1.74 | 2.52 → 2.10 | 81.2% → 93.3% | 7.17 → 7.22 |
| unsupported_weather | — → — | — → — | — → — | — → — |

The source-family Brier scores and reliability bins are saved in `summary.json`; their prevalence is artificial (eight of the nine supported condition families contain a source). They are descriptive simulation scores, not a field probability calibration, and pooled bins do not remove dependence between seed blocks.

## Actual placement outcomes

Every method locks its choices before candidate observations are realized. The methods share the same sites, costs, budget, equipment count and available contemporaneous weather. All selected measurements are appended and refitted using the redesigned engine, isolating acquisition quality; the legacy row means its preserved *planner*, not its entire old inference pipeline. Future observed weather and hidden truth never reach either planner.

Positive RMSE advantage means lower posterior target RMSE than the per-world average of 20 random plans. Positive localization advantage means lower cell-MAP error. The source/noise/transport assumptions remain imperfect. Each row has at most 12 paired worlds, so its uncertainty is large; no general superiority claim follows from a small mean difference.

| Condition | Method | Paired worlds | Mean target RMSE advantage vs random20 (µg/m³) | Mean localization advantage vs random20 (m) | Worse RMSE than random20 | Mean cost |
|---|---|---:|---:|---:|---:|---:|
| direction_bias | new | 12 | -0.046 | -9.1 | 5/12 (42%; 95% CI 19–68%) | 216 |
| direction_bias | legacy | 12 | 0.060 | -7.8 | 4/12 (33%; 95% CI 14–61%) | 213 |
| direction_bias | spread | 12 | 0.031 | -11.8 | 6/12 (50%; 95% CI 25–75%) | 220 |
| direction_bias | wind | 12 | -0.047 | 1.4 | 8/12 (67%; 95% CI 39–86%) | 212 |
| strong_signal | new | 12 | 0.140 | 35.7 | 6/12 (50%; 95% CI 25–75%) | 212 |
| strong_signal | legacy | 12 | -0.025 | 0.1 | 8/12 (67%; 95% CI 39–86%) | 218 |
| strong_signal | spread | 12 | 0.016 | 3.3 | 5/12 (42%; 95% CI 19–68%) | 220 |
| strong_signal | wind | 12 | -0.105 | 18.3 | 9/12 (75%; 95% CI 47–91%) | 212 |
| weak_signal | new | 12 | -0.000 | 4.9 | 7/12 (58%; 95% CI 32–81%) | 211 |
| weak_signal | legacy | 12 | 0.034 | -18.1 | 4/12 (33%; 95% CI 14–61%) | 213 |
| weak_signal | spread | 12 | 0.032 | 29.7 | 6/12 (50%; 95% CI 25–75%) | 218 |
| weak_signal | wind | 12 | -0.062 | -1.3 | 10/12 (83%; 95% CI 55–95%) | 222 |

The redesigned planner integrates background-versus-source and coarse nearest-anchor spatial groups using reduced Gaussian-component mixtures and Sobol integration. It does not optimize the full fine-cell entropy exactly. Finite component budgets and moment approximations can change rankings; the separate numerical-budget study is necessary context. There is no travel route, future-window forecast, field exposure benefit, or expected percentage improvement claim.

## Supplementary checks of usefulness

After the primary experiment, a separate analysis applied the product rule that was already frozen in production: source-model weight ≥0.9, region occupying <50% of the domain, and no predictive warning. Only **2/400 generated condition-worlds** (2/360 fitted) met that rule. Both were correlated-error worlds, and **one of the two regions missed the source**. Thus successful numerical fitting is much more common than a useful source interpretation. The primary table's zero sharp-wrong events uses its predeclared stricter <25% area definition; it does not erase this operational failure under the actual product rule.

A supplementary paired bootstrap (5,000 resamples within each condition, seed 90210) gives 95% percentile intervals for the redesigned planner's mean RMSE advantage over random20: strong_signal **−0.097 to +0.492 µg/m³**, weak_signal **−0.071 to +0.064**, and direction_bias **−0.130 to +0.024**. All include zero. With 12 paired worlds per condition these intervals are exploratory; they do not establish superiority or equivalence.

[Saved supplementary analysis and definitions](../evaluations/overhaul/final-supplementary-analysis.json) preserve these calculations. This was post-evaluation reporting, not a replacement for the predeclared metrics or a reason to tune the model. No production or evaluator source changed.

## Perturbations and sampling

Perturbations are +3° measured wind, +0.5 µg/m³ concentrations, and reversed input order, on the first four worlds per supported condition; plans are checked on the first world only. These are stability checks, not truth validation.

| Perturbation | Results | Median / maximum source-mean displacement (m) | Median / maximum absolute source-weight change | Mean plan Jaccard overlap (when checked) |
|---|---:|---:|---:|---:|
| wind+3deg | 36 | 1.2884 / 123.15 | 0.0040595 / 0.14139 | 0.593 |
| concentration+0.5 | 36 | 0.0076922 / 0.029598 | 3.6048e-05 / 0.00019104 | 1.000 |
| input-order | 36 | 8.4179e-10 / 1.6268e-09 | 0 / 0 | 1.000 |

Stability statuses: `{'retained': 108}`.

[Development ablations and full-data comparison](../evaluations/overhaul/new-development-supplementary-frozen/supplementary.json) contain 18 explicit full/background-only/no-wind-uncertainty fits and 19 sampling fits. This is a small mechanism study, not an independent calibration. Broad wind integration often expands the region and loses precision; a better coverage number alone is not improvement.

For the single 192-row rare-episode fixture, limits 40, 64, 128 and full 192 retained respectively 2, 3, 3 and 6 of the six true episode readings (seed 0). The default 128-row approximation differed from the full source weight by 0.00028 (selection seed 0) or 0.00622 (seed 11), with conditional-mean displacements 0.08 m and 0.50 m. That fixture was diffuse; it does not establish small errors on all campaigns. The concentration-based selection is an explicit bounded approximation and does not guarantee retention of every informative episode or unbiased full-data inference.

## Execution, history and limits

The final source and placement experiment recorded **0 inference/placement crashes**, **394.9 seconds** wall time and **214.0 MiB** process-reported peak RSS on `AMD EPYC 9V45 96-Core Processor` with one BLAS thread. This is a challenge-run measurement, not the maximum supported 10,000-row workload or a universal laptop guarantee. Initial challenge fits use every usable 24-row final input (fewer after missingness); full loaded/excluded/fitted counts are in each record. Separate capacity tests measure the maximum workload and 128/512-row approximation.

The complete development experiment used 12 seed blocks (120 condition-worlds, 240 old/new inference outcomes and 864 follow-ups); calibration used 24 blocks (240 condition-worlds, 480 inference outcomes and 864 follow-ups). Development source-byte checks recorded concurrent formatting of engine/inference; calibration recorded only formatting of unrelated, unimported `validation/overhaul_regression.py`. Both are explicitly development/calibration, preserved with their exact hashes. The first calibration attempt was interrupted for a clean source freeze and retained with an `INTERRUPTED.json` record. The frozen supplementary rerun matched every original numerical result excluding runtime. The untouched final run, which determines this report, has matching before/after hashes.

Commands from the repository root:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m upwind.validation.overhaul --split development --out .local/overhaul-development
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m upwind.validation.overhaul --split development --supplementary-only --out .local/overhaul-supplementary
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m upwind.validation.overhaul --split calibration --out .local/overhaul-calibration
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m upwind.validation.overhaul --split final --out .local/overhaul-final
```

Use new output directories; the runner refuses to overwrite evidence. All earlier stress cases are development-used, and their original failures remain preserved. Re-running these final seeds reproduces a final experiment; it does not create a fresh holdout for subsequent tuning.

No measured-data source-localization validation was obtained. London single-station PM2.5 records support their documented import/data-quality audit, not source accuracy. The official NOAA/DATEM/Sagebrush acquisition status and exact external blockers are documented separately. This challenge cannot establish urban PM2.5 transport, chemical composition, source multiplicity, facility responsibility, health impact, field calibration, or benefit to an operational campaign.

Important review points are the half-normal source marginalization and correlated background conditioning in `inference.py`, the midpoint geographic integration and its excluded area, the moment-matched predictive tails, the coarse/reduced-mixture target in `design.py`, and value-dependent bounded selection in `quality.py`. Read the reported missed failures and loss of region precision before treating any recommendation as useful.
