# Engine 0.8 implementation

`plume-robust-0.8.0` implements protocol `UW-ENGINE-2026-08`. It keeps the
0.7.1 Bayesian background/one-source mixture, analytic Gaussian nuisance
marginalization, positive HalfNormal release integration, coherent shared
weather alternatives, and existing adequacy diagnostics. The new computation
compares nested deterministic source-cell and weather quadrature levels before
the engine can label a conditional source explanation supported.

At each level, the existing source/weather log masses are normalized with
log-sum-exp. The controller compares log evidence, source-existence mass,
source mass aggregated back to the original supported cells, posterior mean and
covariance, 90% highest-density region mass and area, and the weather marginal.
The source grid subdivides posterior-dense cells while preserving all remaining
area mass. Weather refinements retain every configured coherent direction,
speed, and common-mode alternative. The original design and component limits
remain active. If a finer level exceeds those limits or a numerical tolerance
fails, the best completed finite posterior remains available and
`numerical_converged=false` blocks `source_supported`.

The tolerance policy is predeclared in
[`ENGINE_V08_PROTOCOL.md`](ENGINE_V08_PROTOCOL.md) and serialized with every
result. Convergence is purely a numerical statement; it does not establish
physical model adequacy or accuracy. Inference output also reports connected
components in the conditional 90% region and their centroid separation. These
are geometric summaries, not a source-count posterior.

The public analysis retains the prior fields and adds `numerical_converged`,
`numerical_refusal_reason`, detailed `quadrature_diagnostics`, and
`source_region90.connected_region_structure`. JSON result serialization stays
finite-only. Reports distinguish failed numerical convergence from predictive
or weather model-mismatch flags. Imported observations, UTC timestamps,
synthetic row origins, instrument metadata, and weather provenance are not
modified by the inference path.

## Evaluation

The runner is `scripts/evaluate_v08.py`; the full fresh development,
calibration and final splits are retained append-only under
`evaluations/engine-v08/`. A source snapshot of the workspace 0.7.1 package is
under `evaluations/engine-v08/v07-baseline/`, with file-level hashes. Each
paired result records the same serialized input hash. Evaluator truth is stored
separately and is never passed to either analysis function.

The eight synthetic families match the prior 0.7.1 evaluator. All their
outcomes remain conditional and synthetic. Separate concentration holdout
scores, point errors, conditional region coverage/area, support/refusal,
externality flags, weather posterior spread, mode geometry, and every numerical
level delta are recorded. See the generated split summaries and protocol for
the exact denominator and reproduction commands. No synthetic result validates
the assumed neutral plume or supports field attribution.

## Completed evaluation

The source freeze is `evaluations/engine-v08/source-freeze.json` (base commit
`356beac35434b1dbed3ed75705cc96c384aa402c`; candidate package SHA-256
`1397c0625e317891cf162a62745a307850f1ced79b68cfa08be16ef8f820ff04`). The
same 0.7.1 workspace snapshot was used as the paired baseline. Development,
calibration, and final contain 128, 128, and 256 paired worlds respectively:
512 candidate and 512 baseline analyses total. All 512 input hashes match.
Each split completed with zero crashes, refusals, or non-finite results.

| Split | Candidate evidence: supported / ambiguous / mismatch | Converged | Median mean error | Correct source-count region coverage | Median region area |
|---|---:|---:|---:|---:|---:|
| Development, 128 | 1 / 87 / 40 | 128/128 | 91.0 m | 112/128 | 89.1% of domain |
| Calibration, 128 | 0 / 86 / 42 | 128/128 | 91.0 m | 112/128 | 89.1% of domain |
| Final, 256 | 1 / 177 / 78 | 256/256 | 91.0 m | 224/256 | 89.1% of domain |

On the untouched final split, the candidate's posterior-mean error distribution
had median 91.0 m, p90 184.4 m, p95 203.2 m, and maximum 257.2 m. Density-mode
error had median 484.4 m, p90 614.3 m, p95 667.8 m, and maximum 667.8 m. Only
one of 256 worlds was `source_supported`; its mean/mode errors were 165.2 m and
395.3 m, its region covered the simulated source, and it was 0/1 within 50 m.
The candidate's source-probability median was 0.491. These model weights are
not calibrated probabilities of real-world responsibility. There were no
source-free worlds in these eight families, so background false-alarm rate was
not measured.

| Final family, 32 worlds each | Supported / ambiguous / mismatch | Mean / mode error medians (m) | Correct source-count coverage | Median region area | Held-out RMSE median |
|---|---:|---:|---:|---:|---:|
| Nominal | 0 / 32 / 0 | 89.2 / 614.3 | 32/32 | 89.1% | 1.65 µg/m³ |
| Humidity response | 0 / 32 / 0 | 91.0 / 262.5 | 32/32 | 89.2% | 2.55 µg/m³ |
| Sensor drift | 0 / 8 / 24 | 199.6 / 401.8 | 32/32 | 61.2% | 4.19 µg/m³ |
| Changing release | 0 / 32 / 0 | 89.2 / 614.3 | 32/32 | 89.1% | 1.67 µg/m³ |
| Two sources | 0 / 32 / 0 | 89.6 / 614.3 | 0/32 for both sources | 89.1% | 1.62 µg/m³ |
| Spatial background | 1 / 9 / 22 | 150.3 / 395.3 | 32/32 | 50.8% | 8.46 µg/m³ |
| Heavy tail | 0 / 0 / 32 | 91.3 / 510.9 | 32/32 | 88.9% | 5.38 µg/m³ |
| Weather error | 0 / 32 / 0 | 92.5 / 614.3 | 32/32 | 89.1% | 1.64 µg/m³ |

The nominal median region contains the simulated location in all 32 cases but
covers 89.1% of the supported domain; that is broad conditional coverage, not
50 m precision. All 32 two-source worlds remained unresolved under the
one-source model, and none of their conditional regions contained both
sources. Final regions had one connected component in 245/256 fits and two in
11/256; component geometry is not a posterior over source count. Sensor-drift
worlds had a median 531.6 m source-location span across weather alternatives;
the candidate raised externality flags in 26/32. Heavy-tail worlds were all
classified as model mismatch. These refusals of support are useful diagnostics,
but do not establish the remaining worlds' physical adequacy.

All 256 final candidate fits stopped after two nested levels and passed every
predeclared tolerance. Across adjacent-level comparisons the maximum observed
changes were: log evidence 0.00448 (limit 0.01), source probability 0.000601
(0.01), parent-cell mass TV 0.00845 (0.05), mean location 1.03 m (10 m),
relative covariance 0.00345 (0.05), region mass 0.000914 (0.02), region area
fraction 0.00174 (0.05), and weather-marginal TV 0.0256 (0.05). This establishes
stability under this finite refinement policy, not accuracy of the model.

The final run recorded 768 held-out sensor/window predictive checks, with no
unavailable scores. Their median RMSE was 2.31 µg/m³, median 90% interval
coverage was 1.00, and median mean negative log predictive density was 2.37.
These correlated checks score concentration prediction and do not measure
source-location accuracy. The paired 0.7.1 baseline had 2/256 supported worlds
versus 1/256 for 0.8; median mean error differed by +0.0002 m and median mode
error by 0 m. Median analysis runtime was 3.49 s for 0.8 and 1.66 s for 0.7.1.
Thus this candidate adds a numerical convergence guarantee but does not improve
localization in this comparison.

Exact rows, including all warnings, mode/weather summaries, source-count and
externality diagnostics, input hashes, and quadrature deltas, are retained in
`evaluations/engine-v08/{development,calibration,final}/`. The full final
paired comparison uses `final/paired.json`; `final/private_truth.json` is
evaluator-only. Reproduction commands are in the protocol above. The split
contains only source-present worlds (including two-source worlds), so it does
not estimate a false-alarm rate. No measured validation, field calibration,
organizational attribution reliability, regulatory attribution, or operational
readiness is established. The 50 m median-precision target is not met.

For a later GIS/frontend phase, stable outputs to expose with their meanings
intact are the conditional source-region polygons/cells, posterior mean and
density mode, source-existence weight, `status`/`evidence_status`, explicit
numerical-convergence state and refusal reason, and weather/provenance and
adequacy warnings. Keep the posterior mean distinct from the mode, and keep
numerical convergence distinct from physical support. Connected-component
counts, source-count profiles, and all synthetic accuracy metrics are
experimental diagnostics, not a probability of multiple sources or a field
confidence display.
