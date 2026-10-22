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
