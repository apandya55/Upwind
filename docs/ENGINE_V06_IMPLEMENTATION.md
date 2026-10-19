# Engine 0.6: what changed and what did not

The candidate is `plume-robust-0.6.0`, evaluated under
[UW-ENGINE-2026-06](ENGINE_V06_PROTOCOL.md). The exact 0.5 baseline and its failures
are retained in `evaluations/engine-v06/baseline-source` and the earlier reports.
This implements the attachment's weather-bias objective on top of the already
completed 0.5 repair; it does not replace the application or invent field data.

## Coherent weather alternatives

The previous repair conditions persistent station bias on qualifying paired
independent weather observations. Agreement between two instruments cannot
establish the absence of a hidden error shared by both. The new estimator uses a
mixture *after* the weather-only comparison update:

- Nominal comparison model: probability 0.75, existing comparison-conditioned
  direction/log-speed distributions and declared short-period uncertainty.
- Common-error model: probability 0.25, the same correction plus an independent
  coherent normal direction error with SD 20 degrees and log-speed error SD 0.2.

When no reference qualifies, the existing unknown-station model remains; there
is no second duplicate uncertainty component. These probabilities/scales are
research assumptions, not measured frequencies or calibrated error bounds.
References still require simultaneous/co-located observations, uncertainty,
explicit provenance and distinct upstream lineage; duplicate products cannot
create independent information. No observations are rewritten.

Direction and speed are conditionally independent *within* a weather model.
After averaging the models they are generally dependent. `joint_weather_grid`
therefore returns a **joint tensor**, not the product of its marginals. Repeated
identical nodes accumulate mass exactly. Tensor entries with exactly zero prior
mass are omitted; no positive-prior component is pruned. Speed nodes outside the
transport support are explicitly truncated and renormalized as before.

The positive-strength source likelihood, source-domain quadrature and nuisance
terms are integrated for every retained weather pair. Regions, predictive means,
log densities, simulation and planning use the resulting joint posterior.
`common_mode_posterior_probability` is conditional on the single-source family;
it is not an observed probability that instruments are wrong. Pollution-conditioned
wind corrections remain inferred explanations, never independent calibration.

## Adaptive geographic integral

The original area-uniform prior on the rectangle spanned by user anchors remains.
Start with the existing grid (20m target, at most24 cells per axis) and its spatial
quadrature (campaigns four Gauss–Legendre nodes per cell; single windows midpoints).
Rank cells by posterior density, collect up to90% of source mass or96 parents,
and divide each selected parent into four equal rectangles once. Every unselected
cell remains. Recalculate the entire source/weather integral with each cell's
actual area prior. This is neither posterior resampling nor a change to the
search domain. A model-workload guard can retain the coarse integral, with an
explicit diagnostic. Cells already at most10m wide are not refined again.

For unequal cells, geographic HPD ordering and the reported mode use **mass per
area**. Ordering raw cell mass would systematically prefer unrefined large cells
and make the reported answer depend on how a cell was split. The evaluator shares
this distinction; original baseline results retain their historical definitions.
The region is a union of whole cells accumulating at least90% conditional source
mass. It remains finite numerical integration, not calibrated geographic coverage.
Coarse cells can miss isolated narrow peaks; one refinement stage cannot guarantee
convergence of an arbitrary continuous posterior.

## Point decisions, ambiguity and domain extent

The conditional posterior mean integrates all source quadrature nodes. It is the
Bayes decision for squared position loss under this model. The density-mode cell
center, east/north covariance and spatial RMS spread are reported separately.
A mean can lie between modes or in excluded geography; inspect the region rather
than treating any point as a measured source. More decimal places do not establish
physical accuracy.

The model reports source mass in the fixed outer10% strip of the declared
rectangle, using integration nodes rather than counting adaptive cell boundaries.
At least50% edge mass withholds the `source_supported` label. This is an explicit
research sensitivity policy. It cannot establish that a domain is complete or
detect every source beyond it. Domain-limited cases and all refusals remain in
evaluation denominators. Existing source weight/region-size/predictive/weather
screens remain. Passing them still does not prove physical adequacy.

## Exact computation reductions

Many observations share the same receptor coordinates and observed wind
speed/direction. Let G be transport signatures at the distinct combinations and
B a one-hot observation-to-signature matrix. The full observation design is BG.
With the **original full** covariance C and residual y, compute

```
H = Bᵀ C⁻¹ B
h = Bᵀ C⁻¹ y
(Bg)ᵀ C⁻¹ (Bg) = gᵀ H g
(Bg)ᵀ C⁻¹ y = gᵀ h.
```

C still contains every reading's uncertainty, temporal/spatial model error,
persistent instrument bias, period background and trend. Its original determinant
and observation normalizer remain in the marginal likelihood. This reduction
does not average observations or count correlated repeats as new instruments.
Direct full-matrix comparisons cover up to512 observations.

Effective source strength is Q divided by speed scale. For each unique
source/direction signature b, aggregate the joint posterior across speed nodes:

```
p_b = Σ_k w_k
m_b = Σ_k w_k E[q_k] / p_b
v_b = Σ_k w_k (Var[q_k] + (E[q_k] - m_b)²).
```

For residual future signature vector g_b and shared conditional background mean
mu0/covariance C0, the total predictive mean is
`mu0 + Σ_b p_b m_b g_b`. Covariance uses centered between-component deviations,
`Σ_b v_b g_b g_bᵀ`, and the background-only component. Centering avoids subtracting
two huge second moments. This is exact mixture first/second-moment algebra, not
component selection or Gaussianizing strength. Sobol draws select the original
joint component and draw its truncated-normal strength; marginal log densities
sum the same original components in bounded chunks.

The existing28-million-entry transport limit now bounds the actual compressed
design; a separate2-million-nonzero-component limit bounds mixture arrays.
Predictive designs and full per-component covariance tensors also have explicit
bounds. The exact moment/draw paths avoid that tensor. Intermediate coarse arrays
are released before adaptive refinement. These are numerical support contracts,
not guarantees of response time or accuracy at arbitrary deployment scale.

## Product compatibility and verification

API, Scenarios UI and HTML reports distinguish reference-only correction,
pollution-conditioned inference, common-error alternatives, point spread and
search-boundary dependence. Exact point coordinates remain excluded from HTML
exports; they remain in the private JSON. Pollution plans retain equal budget,
access, power and equipment constraints; they do not purchase weather hardware.

Saved0.5 and earlier analyses are archived losslessly and must be rerun. Version
and complete configuration participate in cache identity. Raw imports, timezone
normalization, origin flags, observations and instrument/provenance metadata are
preserved. New tests compare the joint source likelihood to independent scalar
strength quadrature, predictive moments to explicit component moments, grouped
GLS to full covariance, area partitions, density ordering, point-loss identities,
domain strips and saved-result migration. Earlier tests remain enabled.

The neutral Gaussian one-steady-source physical approximation, source-strength
prior, background/error assumptions, kernel support and weather-station matching
limits remain. Arbitrary spatial wind fields, clock errors, intermittent releases,
multiple sources, street canyons and chemical attribution are not solved. Primary
measured tracer validation remains unperformed; external access and provenance/
units blockers from the prior audit remain. Organizational attribution readiness
cannot be inferred from synthetic or software-test counts.
