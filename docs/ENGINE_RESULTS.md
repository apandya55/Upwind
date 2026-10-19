# Scientific engine overhaul: implementation and evidence

The overhaul is implemented as **plume-mixture-0.3.0**. Its numerical calculations and product workflows pass the recorded checks, but source localization and measurement recommendations remain **research-prototype capabilities**. The tests do not support unsupervised attribution, a calibrated geographic confidence claim, or a general placement-benefit claim. A working investigation workspace is useful for recording measurements and comparing explicit hypotheses; it cannot create source information absent from the data.

## What was found and changed

The original 640 source runs and 3,680 follow-up outcomes reproduced exactly, excluding timings. [The audit](ENGINE_AUDIT.md) includes equations, transformations and ranked causes. Wind-from convention, projection, units and numerical normalization passed inspection. The old likelihood already modeled persistent sensor/spatial dependence, so treating every reading as independent was not the confirmed cause.

Separate problems required separate changes:

| Finding | Implemented change | What it does not establish |
|---|---|---|
| Old weak-signal plume increments were often far below instrument error | Background-only competes with one release; ambiguity is reported | A background result does not prove no pollution or identify its chemistry |
| Restricted strength/background grids and wind support can force a wrong location | Analytic positive-strength/intercept/trend integration; wider coherent wind scenarios | Priors and discrepancy covariance are not field calibrated |
| Exact candidate-point truth gave misleading grid coverage | Area-weighted cells between domain anchors, explicit domain/support/resolution, continuous hidden-truth evaluation | A nominal 90% conditional region is not measured 90% geographic coverage |
| Fitted residuals could miss deceptive fits | Withhold complete sensors and score their predictions | The replacement still misses many physical mismatches |
| Old planning score ignored distribution differences with equal means and could exceed target entropy | Numerical predictive-mixture group information with independent quadrature checks | Finite mixture/draw budgets can change rankings; an internal score is not realized learning |
| Future discrepancy was not conditioned on existing residuals | Conditional cross covariance and explicit endpoint-timestamp/instrument update contract | Historical weather is not a forecast; routes/travel are not inferred |
| Quantile selection could discard a diagnostic episode | Configurable 40–512 rows, balanced sensor quotas, rare/extreme/end-time anchors and seeded time strata | Not all rare observations survive; bounded fits are not full-data inversions |
| UI point percentages encouraged incorrect geographic meaning | Domain anchors, conditional cell region, separate support/adequacy/identifiability/validation text, counts and research-only plans | A product label is not a scientific adequacy certificate |

No neural network or new runtime dependency was introduced. A multi-source inverse model was not added without evidence that its extra parameters would be identifiable or improve independent prediction. Multiple sources remain an explicit unsupported explanation, and missed cases remain in the results. [Science](SCIENCE.md) documents every equation/prior, truncation and covariance assumption; [the implementation review map](ENGINE_IMPLEMENTATION.md) identifies the code to inspect.

## Original cases are development data

[The complete old-case before/after table](ENGINE_DEVELOPMENT_COMPARISON.md) covers 640 worlds:480 fits,160 unsupported refusals, zero crashes. All have been inspected and are development-used. The baseline selects discrete MAP points; the new conditional mean/MAP uses a continuous-cell prior, so its point errors are different estimands.

Important regressions remain: in old strong-signal cases, the new geographic region contains truth 26/40 times, despite the old exact-grid MAP error being zero. In old two-source cases it covers the designated primary source 7/40 times, with 33 narrow wrong sharp regions and zero predictive warnings. Direction-bias coverage 36/40 uses regions around 85% of the domain. Weak-signal conditional mean error improves, but regions occupy about 89% and source-model weight stays near 0.5. These are not evidence of useful precise attribution.

## Independent final challenge

The experiment was evaluated only after the model was frozen; all before/after source hashes match. The final set contains 400 condition-worlds across 40 paired seed blocks, with whole sensor layouts, wind regimes and stretched-exponential transport held out from development/calibration. Candidate outcomes are generated only after every method has locked its choices; hidden truth is evaluator-only. Per-condition confidence intervals use 40 repetitions, not pooled 400 independence. Planner conditions reuse 12 seed blocks; 20 random methods are repeated comparisons, not 20 independent campaigns per world.

The independent transport differs in lateral shape, width growth, source height and sub-window wind averaging. It is still simplified synthetic open-terrain transport, not an independent measured campaign. The evaluation cannot establish neighborhood PM2.5 attribution, chemistry or all weather/layout generalization.

The final run completed **800 paired old/new inference outcomes** (400 condition-worlds) and **864 realized follow-up outcomes**, with **zero crashes** and matching before/after source hashes. Both models fit 360/400 and refuse 40 unsupported-weather worlds. This is 90% computational retention, not 90% successful localization.

| Condition | Old MAP median / p90 m | New cell MAP median / p90 m | New conditional-region coverage | Median domain covered | Held-sensor RMSE old → new µg/m³ |
|---|---:|---:|---:|---:|---:|
| background_only | — | — | — | 86.2% | 2.63 → 1.48 |
| weak_signal | 210 / 344 | 216 / 316 | 34/40 | 86.0% | 2.25 → 1.51 |
| strong_signal | 228 / 368 | 168 / 279 | 39/40 | 85.8% | 2.78 → 1.43 |
| direction_bias | 255 / 333 | 193 / 294 | 35/40 | 86.3% | 2.78 → 1.58 |
| two_sources | 203 / 298 | 174 / 275 | 39/40 | 84.8% | 3.17 → 1.84 |
| boundary | 265 / 490 | 207 / 423 | 37/40 | 86.3% | 2.71 → 1.57 |
| correlated_errors | 234 / 369 | 186 / 284 | 36/40 | 83.8% | 3.78 → 2.66 |
| episodic | 237 / 368 | 195 / 279 | 36/40 | 86.0% | 2.73 → 1.44 |
| missingness | 225 / 368 | 184 / 290 | 39/40 | 87.2% | 2.32 → 1.74 |
| unsupported_weather | — | — | — | — | — → — |

**Coverage is mostly obtained with broad regions.** Strong-release cases cover 39/40 true locations, while occupying a median 85.8% of the domain and missing source presence (weight<0.5) in 29/40. Weak cases miss source presence 39/40; biased wind 36/40. Background-only false alarms at weight>0.9 are 0/40 (95% Wilson upper bound 8.8%). No-source and source worlds are therefore not reliably distinguished.

The conditional source mean has median errors around 87–97 m in several interior families, but a **no-data domain-centroid estimate already has median 89.92 m** on those same sources. These small mean errors largely reflect prior centering. They must not be called learned localization accuracy. The MAP distributions above and the boundary failures expose that limitation. The frozen product evidence rule labels just **2/400 generated worlds** source-supported (2/360 fitted), and one of those two regions misses truth. That rule provides very little useful resolved output; broad coverage and near-abstention do not meet reliable-localization goals.

The held-out predictive screen warns on 10/40 correlated-error worlds and 0/40 each two-source, episodic and direction-bias worlds. Those are important missed physical failures. It also produces 0/40 warnings in background-only and single-source strong-release cases. Improved prediction is a narrower measured benefit: for example, mean held-sensor RMSE falls 2.78→1.43 µg/m³ under higher release, while interval coverage rises 68.8%→97.5% rather than establishing nominal 90% calibration. Per-condition quantiles, NLPD, width, Brier scores, warnings/refusals and Wilson intervals are in [the complete final report](ENGINE_CHALLENGE_RESULTS.md).

| Planner condition | New target-RMSE advantage vs mean 20 random plans µg/m³ | Supplementary paired 95% bootstrap interval | Worse than random mean | Mean cost |
|---|---:|---:|---:|---:|
| direction_bias | -0.046 | -0.130 to +0.024 | 5/12 | 216 |
| strong_signal | +0.140 | -0.097 to +0.492 | 6/12 | 212 |
| weak_signal | -0.000 | -0.071 to +0.064 | 7/12 | 211 |

Positive advantage favors the new planner. All three supplementary intervals cross zero. They resample paired seed blocks within each condition (5,000 replicates, fixed seed 90210); n=12 remains imprecise. These post-evaluation intervals and the frozen-rule counts are explicitly supplementary descriptions, not replacements for the protocol metrics. [Exact script/results](../evaluations/overhaul/final-supplementary-analysis.json) retain input hashes. The complete report compares every proposed method with the preserved old planner, spread, wind and all 20 random seeds, including cost/localization outcomes. There is **no demonstrated general placement advantage**. The UI keeps the spread baseline available and labels the information plans experimental.

All 108 perturbations retain computable outputs. Input reversal changes source means by at most 1.7×10⁻⁹ m and preserves plan choices; +3° measured wind can move a mean 123 m and changes some plans. Stable code ordering is verified; robustness to plausible wind error is limited.

[Source-region and error figure](../evaluations/overhaul/new-final/source-overhaul.png) · [Planner/reliability figure](../evaluations/overhaul/new-final/planner-overhaul.png) · [Exportable SVG/figure provenance](../evaluations/overhaul/new-final/FIGURES.md)


## Sensitivity, ablations and workload limits

- [Covariance/quadrature study](ENGINE_SENSITIVITY.md): 288 fits across paired development conditions. Persistent model error alone does not repair old strong or two-source coverage. Finer cells help some strong cases and worsen the two-source example. Independent strong regions are already broad; no universal setting was selected from these outcomes.
- `new-development-supplementary-frozen`: 18 inference ablations and 19 selected/full-data comparisons. A single 192-reading rare-episode challenge retains 2/6 episode readings at limit 40, 3/6 at 64/128, and 6/6 under full 192. The 128-row fit's conditional source mean differs from full by 0.08–0.50 m across two selection seeds in this one broad case; this is not a general equivalence guarantee.
- `ablations-planner-dev-frozen-v2`: 36 plans across six development condition-worlds. Raising 128 components/128 draws to 512/512 changes four choices; realized target RMSE improves twice and worsens twice. Replicate agreement does not bound component-reduction bias.
- Six schema-limit resource children finish within 30 seconds and 2 GiB address space. At 10,000 measurements + 10,000 met records + 100 sites + 25 anchors, 4,621 mixture components: 128 fitted rows take 12.67 s/357.51 MiB peak RSS; 512 take 14.72 s/660.62 MiB. The reproduced old 40-row model took 1.38 s/226.72 MiB on its maximum fixture. This is a substantial computation/memory regression for additional inference/diagnostics, not a speed improvement.

The maximum-component probe separately tests 576 cells/12,097 components; its result is reported below. All timings use the recorded AMD EPYC 9V45 CPU, one BLAS thread and fresh child processes; not laptop guarantees. 30 s/2 GiB are test limits, not an API service-level promise. Loaded, excluded and fitted counts remain separate.

The separate maximum-component test used all 576 cells and **12,097 components**, with no excluded source area and the same 10,000/10,000/100/25 input limits. It passed both fresh-process limits:

| Fitted / loaded measurements | Runtime | Peak RSS |
|---|---:|---:|
| 128 / 10,000 | 15.58 s | 550.72 MiB |
| 512 / 10,000 | 19.94 s | 1,290.16 MiB |

The exact script, geometry, hashes, time/address-space limits and all results are saved in `evaluations/overhaul/resources-max-components/`. This is the largest tested numerical shape, with configured equipment limit eight; it remains bounded selected-row inference.

## Software and data verification

**81 backend tests** pass, including independent positive-strength integration and predictive-moment oracles, tail stability, uniform area prior, QMC permutation invariance, feasibility and exhaustive tiny optimization. **Six Chromium workflows**, typecheck and production build pass. Ruff F401/F821 passes. The original immutable baseline separately passes 34 tests and 72,167 engineering/property checks; those counts are not relabeled as 81+72,167 tests of every new model feature.

API concurrency: 64 writes / 32 clients produce 13 accepted and 51 explicit 429 responses; every acknowledged write survives exactly once. Four malformed requests return 422, oversized body 413, no partial writes, and post-overload recovery 200. A 500-combination CSV battery has zero unexpected errors. Response counts/timings are scheduler-dependent, not fixed expectations. Normal local services were restarted; health reports the new scientific identifier.

**Measured-data localization validation: not performed.** Official NOAA DATEM/Project Sagebrush retrieval still fails at proxy CONNECT 403 before source files are obtained. [Research/access evidence](ENGINE_RESEARCH.md) records exact permitted routes, commands, pinned source documents and licensing findings. No proxy bypass, invented coordinates or relabeled simulation was used. The previously inspected 65,533 London records have no verified coordinates or independent release truth for this task; they remain a data/import audit. Even future tracer success would not automatically validate neighborhood PM2.5.

## Reproduce and review

```sh
# Current product checks:
OPENBLAS_NUM_THREADS=1 .venv/bin/python -m pytest -q
cd frontend && npm run build && npm run test:e2e
# Back at repository root, use new output folders:
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m upwind.validation.overhaul --split final --out .local/final-recheck
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m upwind.validation.overhaul_regression --out .local/oldcase-recheck --report .local/oldcase-report.md
# Exact archived baseline implementation:
PYTHONPATH=evaluations/overhaul/baseline-source/backend OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m upwind.validation.run --skip-external --out .local/baseline-recheck
```

The metadata records exact code/configuration hashes, commands, seeds, dependency versions, CPU and every refusal/failure. Baseline/file manifests substitute for a commit identifier because this checkout has no committed project history. No GitHub push or publication was performed. Interrupted probes and pre-final software/format changes remain documented; the final primary run has unchanged relevant source hashes. Previous evaluation outputs were preserved.

The final set remains untouched by model tuning: outcomes can inform the next scientific investigation, but changing priors, thresholds or physics using them would make them development data and require a fresh evaluation. Start review with `inference.CONFIG`, analytic likelihood/truncation, source-support exclusions, sensor-block prediction, `design.py` component approximation and the actual-versus-random planner outcomes. The unresolved scientific failures are reasons to keep the current recommendations in research use.

Handover: [implementation/configuration manifest](../evaluations/overhaul/implementation-manifest.json) and [verification records](../evaluations/overhaul/verification.json).
